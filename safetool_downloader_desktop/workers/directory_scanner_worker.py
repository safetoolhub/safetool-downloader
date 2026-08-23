# This file is part of SafeTool Downloader, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Directory index scanner worker — BFS crawl of Apache/nginx autoindex pages."""

from __future__ import annotations

import logging
import re
import time
from collections import deque
from urllib.parse import urljoin, urlparse, urlunparse, unquote

import requests
from bs4 import BeautifulSoup
from PySide6.QtCore import QThread, Signal

from safetool_downloader_desktop.i18n import tr

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"
)

_DIRECTORY_INDEX_SORT_RE = re.compile(r"^C=[NMSD];O=[AD]$")

_SIZE_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*([KMGTP])",
    re.IGNORECASE,
)


def _normalise_url(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path.rstrip("/") if parsed.path != "/" else "/"
    query = parsed.query
    if query and _DIRECTORY_INDEX_SORT_RE.match(query):
        query = ""
    return urlunparse((
        parsed.scheme.lower(),
        parsed.netloc.lower(),
        path,
        parsed.params,
        query,
        "",
    ))


def _get_file_extension(url: str) -> str:
    path = unquote(urlparse(url).path)
    lower = path.lower()
    for compound in (".tar.gz", ".tar.bz2", ".tar.xz"):
        if lower.endswith(compound):
            return compound
    dot = path.rfind(".")
    if dot != -1:
        ext = path[dot:].lower()
        ext = ext.split("?")[0].split("#")[0]
        if ext and len(ext) <= 10:
            return ext
    return ""


def _get_filename(url: str) -> str:
    path = unquote(urlparse(url).path)
    name = path.rstrip("/").rsplit("/", 1)[-1]
    return name if name else "unknown"


def _is_same_domain(url: str, base_url: str) -> bool:
    return urlparse(url).netloc.lower() == urlparse(base_url).netloc.lower()


def _is_under_base_path(url: str, base_url: str) -> bool:
    base_path = urlparse(base_url).path
    if not base_path.endswith("/"):
        base_path = base_path + "/"
    return urlparse(url).path.startswith(base_path)


def _sanitize_filename(name: str) -> str:
    name = name.replace("/", "_").replace("\\", "_")
    name = re.sub(r"[\x00-\x1f]", "", name)
    if len(name) > 200:
        name = name[:200]
    return name or "unknown"


def _parse_size_text(text: str) -> int:
    m = _SIZE_RE.search(text)
    if not m:
        return -1
    value = float(m.group(1))
    unit = m.group(2).upper()
    multipliers = {"K": 1024, "M": 1024**2, "G": 1024**3, "T": 1024**4, "P": 1024**5}
    return int(value * multipliers.get(unit, 1))


class FileInfo:
    __slots__ = ("url", "filename", "extension", "size_hint", "size_hint_approx", "source_page", "depth", "meta")

    def __init__(
        self,
        url: str,
        filename: str,
        extension: str,
        size_hint: int,
        source_page: str,
        depth: int = 0,
        meta: dict | None = None,
        size_hint_approx: bool = False,
    ) -> None:
        self.url = url
        self.filename = _sanitize_filename(filename)
        self.extension = extension
        self.size_hint = size_hint
        self.size_hint_approx = size_hint_approx
        self.source_page = source_page
        self.depth = depth
        self.meta = meta

    def to_dict(self) -> dict:
        d = {
            "url": self.url,
            "filename": self.filename,
            "extension": self.extension,
            "size_hint": self.size_hint,
            "size_hint_approx": self.size_hint_approx,
            "source_page": self.source_page,
            "depth": self.depth,
        }
        if self.meta:
            d["meta"] = self.meta
        return d


class DirectoryScannerWorker(QThread):
    """Background worker that crawls Apache/nginx directory index pages.

    Recursively visits all subdirectories under the given URL and collects
    every file found, preserving the directory structure.  No page limit,
    no file limit, no extension filter — it downloads everything.

    Signals:
        files_found(list): List of FileInfo dicts.
        scan_progress(str): Human-readable progress message.
        scan_detail(str): Current URL path being scanned.
        scan_error(str): Error message.
        scan_finished(): Always emitted when scan ends.
    """

    files_found = Signal(list)
    scan_progress = Signal(str)
    scan_detail = Signal(str)
    scan_error = Signal(str)
    scan_finished = Signal()

    def __init__(
        self,
        url: str,
        delay: float = 0.3,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._base_url = url if url.endswith("/") else url + "/"
        self._delay = delay
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        try:
            session = requests.Session()
            session.headers.update({"User-Agent": USER_AGENT})

            logger.info("Directory scan starting: %s", self._base_url)

            all_files: list[dict] = []
            visited: set[str] = set()
            queue: deque[tuple[str, int]] = deque()
            queue.append((self._base_url, 0))
            visited.add(_normalise_url(self._base_url))
            dirs_scanned = 0

            while queue and not self._cancelled:
                url, depth = queue.popleft()
                dirs_scanned += 1

                parsed = urlparse(url)
                url_path = unquote(parsed.path) or "/"
                self.scan_detail.emit(f"{parsed.netloc}{url_path}")
                self.scan_progress.emit(
                    tr("direct_scan.scanning_progress",
                       dirs=dirs_scanned, files=len(all_files))
                )

                try:
                    dir_files, subdirs = self._scan_directory_page(session, url)
                except Exception as exc:
                    logger.warning("Error scanning directory %s: %s", url, exc)
                    continue

                for fi in dir_files:
                    fi.depth = depth
                    all_files.append(fi.to_dict())

                for subdir_url in subdirs:
                    norm = _normalise_url(subdir_url)
                    if norm in visited:
                        continue
                    if not _is_same_domain(subdir_url, self._base_url):
                        continue
                    if not _is_under_base_path(subdir_url, self._base_url):
                        continue
                    visited.add(norm)
                    queue.append((subdir_url, depth + 1))

                if queue and self._delay > 0:
                    time.sleep(self._delay)

            if self._cancelled:
                logger.info("Directory scan cancelled.")
                self.scan_progress.emit(tr("direct_scan.cancelled"))
                self.scan_detail.emit("")
            else:
                seen_urls: set[str] = set()
                unique_files: list[dict] = []
                for f in all_files:
                    if f["url"] not in seen_urls:
                        seen_urls.add(f["url"])
                        unique_files.append(f)

                logger.info(
                    "Directory scan complete: %d directories, %d unique files",
                    dirs_scanned, len(unique_files),
                )

                self.scan_detail.emit("")
                self.scan_progress.emit(
                    tr("direct_scan.complete",
                       dirs=dirs_scanned, files=len(unique_files))
                )
                self.files_found.emit(unique_files)

            session.close()

        except Exception as exc:
            logger.exception("Directory scanner error")
            self.scan_error.emit(str(exc))
        finally:
            self.scan_finished.emit()

    def _scan_directory_page(
        self, session: requests.Session, url: str,
    ) -> tuple[list[FileInfo], list[str]]:
        """Parse an Apache/nginx directory index page.

        Returns (files, subdirectory_urls).
        """
        resp = session.get(url, timeout=30, allow_redirects=True)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "lxml")

        files: list[FileInfo] = []
        subdirs: list[str] = []

        pre = soup.find("pre")
        if not pre:
            logger.debug("No <pre> found at %s — not a directory index?", url)
            return files, subdirs

        for a_tag in pre.find_all("a", href=True):
            href = a_tag["href"].strip()
            if not href:
                continue

            if href.startswith(("#", "javascript:", "mailto:")):
                continue

            if _DIRECTORY_INDEX_SORT_RE.match(urlparse(href).query or ""):
                continue

            absolute = urljoin(url, href)

            img = a_tag.find_previous_sibling("img")
            alt = (img.get("alt", "") if img else "").lower()

            if "volver" in alt or "back" in alt or "parent" in alt:
                continue

            if href.endswith("/"):
                if _is_same_domain(absolute, self._base_url):
                    subdirs.append(absolute)
                continue

            ext = _get_file_extension(absolute)
            if not ext:
                continue

            filename = _get_filename(absolute)

            size_hint = -1
            row_text = ""
            next_sib = a_tag.next_sibling
            if next_sib and isinstance(next_sib, str):
                row_text = next_sib
            if not row_text:
                parent_text = a_tag.parent.get_text() if a_tag.parent else ""
                link_text = a_tag.get_text()
                idx = parent_text.find(link_text)
                if idx >= 0:
                    row_text = parent_text[idx + len(link_text):]
            if row_text:
                size_hint = _parse_size_text(row_text)

            files.append(FileInfo(
                url=absolute,
                filename=filename,
                extension=ext,
                size_hint=size_hint,
                source_page=url,
            ))

        logger.debug(
            "  %s: %d files, %d subdirs", url, len(files), len(subdirs),
        )
        return files, subdirs
