# This file is part of SafeTool Downloader, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Download worker — downloads files with progress reporting."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests
from PySide6.QtCore import QThread, Signal

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (compatible; SafeToolDownloader/0.1; +https://safetoolhub.org)"
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


class DownloadWorker(QThread):
    """Background worker to download files with per-file progress.

    Signals:
        file_progress(int, int, int): (file_index, percent, bytes_downloaded).
        file_complete(int, str): (file_index, saved_path).
        file_error(int, str): (file_index, error_message).
        overall_progress(int, int): (completed_count, total_count).
        all_complete(int, int): (success_count, error_count).
    """

    file_progress = Signal(int, int, int)
    file_complete = Signal(int, str)
    file_error = Signal(int, str)
    overall_progress = Signal(int, int)
    all_complete = Signal(int, int)

    def __init__(
        self,
        files: list[dict],
        output_dir: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._files = files
        self._output_dir = Path(output_dir)
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

        session = requests.Session()
        session.headers.update({"User-Agent": USER_AGENT})

        try:
            for idx, file_info in enumerate(self._files):
                if self._cancelled:
                    break

                url = file_info["url"]
                filename = _sanitize_filename(file_info.get("filename", "download"))

                try:
                    self._download_file(session, idx, url, filename)
                    success_count += 1
                except Exception as exc:
                    logger.warning("Download error for %s: %s", url, exc)
                    self.file_error.emit(idx, str(exc))
                    error_count += 1

                self.overall_progress.emit(success_count + error_count, total)
        finally:
            session.close()

        self.all_complete.emit(success_count, error_count)

    def _download_file(
        self, session: requests.Session, idx: int, url: str, filename: str
    ) -> None:
        """Download a single file with progress updates."""
        resp = session.get(url, stream=True, timeout=60, allow_redirects=True)
        resp.raise_for_status()

        # Get total size from headers
        total_size = int(resp.headers.get("Content-Length", 0))

        dest_path = _unique_path(self._output_dir / filename)

        downloaded = 0
        with open(dest_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=CHUNK_SIZE):
                if self._cancelled:
                    # Clean up partial file
                    f.close()
                    dest_path.unlink(missing_ok=True)
                    return

                f.write(chunk)
                downloaded += len(chunk)

                if total_size > 0:
                    percent = min(100, int(downloaded * 100 / total_size))
                else:
                    percent = -1  # Indeterminate
                self.file_progress.emit(idx, percent, downloaded)

        self.file_complete.emit(idx, str(dest_path))
