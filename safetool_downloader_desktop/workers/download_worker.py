# This file is part of SafeTool Downloader, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Download worker — downloads files with progress reporting."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from urllib.parse import unquote, urlparse, urljoin

import requests
from PySide6.QtCore import QThread, Signal

from safetool_downloader_desktop.settings import (
    get_duplicate_action,
    DUPLICATE_SKIP,
    DUPLICATE_OVERWRITE,
    DUPLICATE_RENAME,
)

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"
)

CHUNK_SIZE = 8192


def _sanitize_filename(name: str) -> str:
    """Remove path traversal and dangerous characters."""
    name = name.replace("/", "_").replace("\\", "_")
    name = re.sub(r'[<>:"|?*\x00-\x1f]', "_", name)
    name = name.strip(". ")
    if len(name) > 200:
        name = name[:200]
    return name or "download"


def _sanitize_dirname(name: str) -> str:
    """Sanitize a single directory name component, preventing path traversal."""
    name = unquote(name)
    name = re.sub(r'[<>:"\|?*\x00-\x1f/\\]', "_", name)
    name = name.strip(". ")
    if len(name) > 100:
        name = name[:100]
    return name or "dir"


def _resolve_output_path(
    url: str,
    base_url: str,
    output_dir: Path,
    preserve_structure: bool,
    filename_override: str | None = None,
) -> Path:
    """Compute the destination Path for a file.

    When *preserve_structure* is True the URL path relative to *base_url* is
    mirrored inside *output_dir*.  Falls back to a flat layout if the file URL
    is not under the base path.

    *filename_override* replaces the leaf filename derived from the URL.  Used
    for RSS episodes where the scanner already built a human-readable name from
    the episode title.
    """
    parsed_url = urlparse(url)
    url_filename = _sanitize_filename(
        unquote(parsed_url.path).rstrip("/").rsplit("/", 1)[-1] or "download"
    )
    leaf = filename_override or url_filename

    if not preserve_structure or not base_url:
        return output_dir / leaf

    parsed_base = urlparse(base_url)
    file_path = unquote(parsed_url.path)
    base_path = unquote(parsed_base.path)

    # Normalise base_path to always end with "/"
    if not base_path.endswith("/"):
        base_path = base_path + "/"

    if not file_path.startswith(base_path):
        # File is outside the base path — fall back to flat layout
        return output_dir / leaf

    rel_path = file_path[len(base_path):]
    parts = [p for p in rel_path.split("/") if p]
    if not parts:
        return output_dir / leaf

    # Last part is the filename; everything before it is subdirectory components
    *dir_parts, _fname = parts
    dest_dir = output_dir
    for part in dir_parts:
        dest_dir = dest_dir / _sanitize_dirname(part)
    return dest_dir / leaf


def _unique_path(path: Path) -> Path:
    """Return a unique file path, appending _1, _2, etc. if needed."""
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    counter = 1
    while True:
        candidate = parent / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1
        if counter > 9999:
            raise RuntimeError(f"Too many duplicates for {path.name}")


def _write_id3_tags(dest_path: Path, file_info: dict, session: requests.Session) -> None:
    """Write ID3v2 tags to an MP3 file from RSS metadata stored in *file_info*.

    Requires ``mutagen``.  Degrades silently if mutagen is not installed or the
    file is not a valid MP3.  Any error during tagging is logged and ignored so
    it never interrupts the download flow.

    Tags written (when metadata is present):
    - TIT2 — episode title
    - TPE1 — podcast author
    - TALB — podcast name (album)
    - TRCK — track / episode number
    - TDRC — publication date
    - COMM — episode description (English)
    - APIC — cover art (fetched via HTTP from ``rss_image_url``)
    """
    meta = file_info.get("meta")
    if not meta:
        return

    try:
        from mutagen.id3 import APIC, COMM, ID3, ID3NoHeaderError, TALB, TDRC, TIT2, TPE1, TRCK
    except ImportError:
        logger.debug("mutagen not available — skipping ID3 tagging for %s", dest_path.name)
        return

    try:
        try:
            tags = ID3(str(dest_path))
        except ID3NoHeaderError:
            tags = ID3()

        if title := meta.get("rss_title"):
            tags["TIT2"] = TIT2(encoding=3, text=title)
        if artist := meta.get("rss_artist"):
            tags["TPE1"] = TPE1(encoding=3, text=artist)
        if album := meta.get("rss_album"):
            tags["TALB"] = TALB(encoding=3, text=album)
        if track := meta.get("rss_track"):
            tags["TRCK"] = TRCK(encoding=3, text=str(track))
        if date := meta.get("rss_date"):
            tags["TDRC"] = TDRC(encoding=3, text=date)
        if desc := meta.get("rss_description"):
            tags["COMM"] = COMM(encoding=3, lang="eng", desc="", text=desc)

        image_url = meta.get("rss_image_url")
        if image_url:
            try:
                img_resp = session.get(image_url, timeout=10, allow_redirects=True)
                img_resp.raise_for_status()
                mime = img_resp.headers.get("Content-Type", "image/jpeg").split(";")[0].strip()
                tags["APIC"] = APIC(
                    encoding=3,
                    mime=mime,
                    type=3,   # Cover (front)
                    desc="Cover",
                    data=img_resp.content,
                )
            except Exception as exc:
                logger.debug("Could not fetch cover art from %s: %s", image_url, exc)

        tags.save(str(dest_path))
        logger.info("ID3 tags written for %s", dest_path.name)
    except Exception as exc:
        logger.warning("Failed to write ID3 tags for %s: %s", dest_path.name, exc)


class DownloadWorker(QThread):
    """Background worker to download files with per-file progress.

    Signals:
        file_progress(int, int, int): (file_index, percent, bytes_downloaded).
        file_complete(int, str): (file_index, saved_path).
        file_error(int, str): (file_index, error_message).
        overall_progress(int, int): (completed_count, total_count).
        all_complete(int, int, int): (success_count, error_count, skip_count).
    """

    file_progress = Signal(int, int, object)
    file_complete = Signal(int, str)
    file_skipped = Signal(int, str)   # (file_index, dest_path) — file already exists, same size
    file_error = Signal(int, str)
    overall_progress = Signal(int, int)
    all_complete = Signal(int, int, int)

    def __init__(
        self,
        files: list[dict],
        output_dir: str,
        base_url: str = "",
        preserve_structure: bool = True,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._files = files
        self._output_dir = Path(output_dir)
        self._base_url = base_url
        self._preserve_structure = preserve_structure
        self._duplicate_action = get_duplicate_action()
        self._cancelled = False

    def cancel(self) -> None:
        """Request cancellation of downloads."""
        self._cancelled = True

    def run(self) -> None:
        """Download all files sequentially."""
        self._output_dir.mkdir(parents=True, exist_ok=True)

        total = len(self._files)
        success_count = 0
        error_count = 0
        skip_count = 0

        session = requests.Session()
        session.headers.update({"User-Agent": USER_AGENT})

        try:
            for idx, file_info in enumerate(self._files):
                if self._cancelled:
                    break

                url = file_info["url"]
                filename = _sanitize_filename(file_info.get("filename", "download"))

                try:
                    skipped = self._download_file(session, idx, url, filename, file_info)
                    if skipped:
                        skip_count += 1
                    else:
                        success_count += 1
                except requests.HTTPError as exc:
                    code = exc.response.status_code if exc.response is not None else 0
                    logger.warning("Download HTTP %s error for %s: %s", code, url, exc)
                    self.file_error.emit(idx, f"HTTP_{code}:{exc}")
                    error_count += 1
                except Exception as exc:
                    logger.warning("Download error for %s: %s", url, exc)
                    self.file_error.emit(idx, str(exc))
                    error_count += 1

                self.overall_progress.emit(success_count + error_count + skip_count, total)
        finally:
            session.close()

        self.all_complete.emit(success_count, error_count, skip_count)

    def _download_file(
        self, session: requests.Session, idx: int, url: str, filename: str,
        file_info: dict,
    ) -> bool:
        """Download a single file with progress updates.

        Returns True if the file was skipped (already exists, same size).
        """
        # Use the human-readable filename from the scanner when available
        # (e.g. RSS episode title), otherwise derive from the URL.
        filename_override = _sanitize_filename(file_info.get("filename") or "") or None
        dest_path = _resolve_output_path(
            url, self._base_url, self._output_dir, self._preserve_structure,
            filename_override=filename_override,
        )
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        # ── Duplicate check ───────────────────────────────────────────
        known_size = file_info.get("size_hint", -1)
        if dest_path.exists():
            existing_size = dest_path.stat().st_size
            same_size = (known_size >= 0 and existing_size == known_size)

            if same_size:
                # Always skip when name+size match, regardless of duplicate setting
                logger.info(
                    "Skipped (already exists, same size %d B): %s",
                    existing_size, dest_path,
                )
                self.file_skipped.emit(idx, str(dest_path))
                return True
            else:
                # Different size — apply duplicate action setting
                if self._duplicate_action == DUPLICATE_OVERWRITE:
                    logger.info(
                        "Overwriting existing file (different size): %s", dest_path
                    )
                    # dest_path stays as-is; will be overwritten below
                else:
                    # DUPLICATE_SKIP or DUPLICATE_RENAME: rename to avoid data loss
                    dest_path = _unique_path(dest_path)
                    logger.info(
                        "Renaming to avoid overwrite (different size): %s", dest_path
                    )

        resp = session.get(url, stream=True, timeout=60, allow_redirects=True)
        resp.raise_for_status()

        # Get total size from headers (use HEAD-fetched hint if available)
        total_size = int(resp.headers.get("Content-Length", 0)) or known_size

        downloaded = 0
        with open(dest_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=CHUNK_SIZE):
                if self._cancelled:
                    # Clean up partial file
                    f.close()
                    dest_path.unlink(missing_ok=True)
                    return False

                f.write(chunk)
                downloaded += len(chunk)

                if total_size > 0:
                    percent = min(100, int(downloaded * 100 / total_size))
                else:
                    percent = -1  # Indeterminate
                self.file_progress.emit(idx, percent, downloaded)

        self.file_complete.emit(idx, str(dest_path))

        # Write ID3 tags for MP3 files that carry RSS metadata
        if dest_path.suffix.lower() == ".mp3" and file_info.get("meta"):
            _write_id3_tags(dest_path, file_info, session)

        return False
