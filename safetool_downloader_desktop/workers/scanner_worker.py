# This file is part of SafeTool Downloader, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Scanner worker — scans web pages for downloadable files with optional recursion."""

from __future__ import annotations

import logging
import re
import time
from collections import deque
from typing import Optional
from urllib.parse import urljoin, urlparse, urlunparse, unquote

import requests
from bs4 import BeautifulSoup
from PySide6.QtCore import QThread, Signal

logger = logging.getLogger(__name__)

# File extensions grouped by category
FILE_EXTENSIONS: dict[str, list[str]] = {
    "PDF": [".pdf"],
    "Images": [".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp", ".ico", ".tiff"],
    "Audio": [".mp3", ".wav", ".flac", ".ogg", ".aac", ".wma", ".m4a"],
    "Video": [".mp4", ".avi", ".mkv", ".webm", ".mov", ".wmv", ".flv", ".m4v"],
    "Documents": [".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".odt", ".ods", ".odp", ".rtf", ".txt", ".csv"],
    "Archives": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".tar.gz", ".tar.bz2"],
    "Code": [".py", ".js", ".html", ".css", ".json", ".xml", ".yaml", ".yml", ".sh", ".bat"],
}

ALL_EXTENSIONS: set[str] = set()
for exts in FILE_EXTENSIONS.values():
    ALL_EXTENSIONS.update(exts)

# Extensions that indicate a downloadable file (not an HTML page)
_PAGE_EXTENSIONS = {".html", ".htm", ".php", ".asp", ".aspx", ".jsp", ".shtml"}

USER_AGENT = (
    "Mozilla/5.0 (compatible; SafeToolDownloader/0.1; +https://safetoolhub.org)"
)


def _normalise_url(url: str) -> str:
    """Normalise a URL for dedup: strip fragment, trailing slash, lowercase host."""
    parsed = urlparse(url)
    path = parsed.path.rstrip("/") if parsed.path != "/" else "/"
    return urlunparse((
        parsed.scheme.lower(),
        parsed.netloc.lower(),
        path,
        parsed.params,
        parsed.query,
        "",  # strip fragment
    ))


def _get_file_extension(url: str) -> str:
    """Extract file extension from the URL path."""
    path = urlparse(url).path
    path = unquote(path)
    # Handle compound extensions like .tar.gz
    lower = path.lower()
    for compound in (".tar.gz", ".tar.bz2", ".tar.xz"):
        if lower.endswith(compound):
            return compound
    # Simple extension
    dot = path.rfind(".")
    if dot != -1:
        ext = path[dot:].lower()
        # Strip query-like suffixes that got into the path
        ext = ext.split("?")[0].split("#")[0]
        if ext and len(ext) <= 10:
            return ext
    return ""


def _get_filename(url: str) -> str:
    """Extract filename from URL path."""
    path = urlparse(url).path
    path = unquote(path)
    name = path.rstrip("/").rsplit("/", 1)[-1]
    return name if name else "unknown"


def _is_same_domain(url: str, base_url: str) -> bool:
    """Check if url belongs to the same domain as base_url."""
    return urlparse(url).netloc.lower() == urlparse(base_url).netloc.lower()


def _looks_like_page(url: str) -> bool:
    """Determine if a URL likely points to an HTML page rather than a file."""
    ext = _get_file_extension(url)
    if not ext:
        return True
    if ext in _PAGE_EXTENSIONS:
        return True
    # Directory-like URLs
    if urlparse(url).path.endswith("/"):
        return True
    return False


def _sanitize_filename(name: str) -> str:
    """Remove path traversal and dangerous characters from a filename."""
    # Remove any directory separators
    name = name.replace("/", "_").replace("\\", "_")
    # Remove null bytes and other control characters
    name = re.sub(r"[\x00-\x1f]", "", name)
    # Limit length
    if len(name) > 200:
        name = name[:200]
    return name or "unknown"


class FileInfo:
    """Information about a discovered file."""

    __slots__ = ("url", "filename", "extension", "size_hint", "source_page", "depth")

    def __init__(
        self,
        url: str,
        filename: str,
        extension: str,
        size_hint: int,
        source_page: str,
        depth: int = 0,
    ) -> None:
        self.url = url
        self.filename = _sanitize_filename(filename)
        self.extension = extension
        self.size_hint = size_hint
        self.source_page = source_page
        self.depth = depth

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "filename": self.filename,
            "extension": self.extension,
            "size_hint": self.size_hint,
            "source_page": self.source_page,
            "depth": self.depth,
        }


class ScannerWorker(QThread):
    """Background worker to scan web pages for downloadable files.

    Signals:
        files_found(list): List of FileInfo dicts found across all pages.
        scan_progress(str): Human-readable progress message.
        page_scanned(str, int, int): (url, depth, files_found_on_page).
        scan_error(str): Error message if scan fails.
        scan_finished(): Emitted when scan completes (success or failure).
    """

    files_found = Signal(list)
    scan_progress = Signal(str)
    scan_detail = Signal(str)
    page_scanned = Signal(str, int, int)
    scan_error = Signal(str)
    scan_finished = Signal()

    def __init__(
        self,
        url: str,
        extensions: list[str] | None = None,
        recursive: bool = False,
        max_depth: int = 1,
        delay: float = 0.5,
        max_pages: int = 100,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._base_url = url
        self._extensions = set(e.lower() for e in extensions) if extensions else None
        self._recursive = recursive
        self._max_depth = max_depth
        self._delay = delay
        self._max_pages = max_pages
        self._cancelled = False
        self._session: Optional[requests.Session] = None

    def cancel(self) -> None:
        """Request cancellation of the scan."""
        self._cancelled = True

    def run(self) -> None:
        """Execute the scan in a background thread."""
        try:
            self._session = requests.Session()
            self._session.headers.update({"User-Agent": USER_AGENT})

            all_files: list[dict] = []
            visited: set[str] = set()
            # BFS queue: (url, depth)
            queue: deque[tuple[str, int]] = deque()
            queue.append((self._base_url, 0))
            visited.add(_normalise_url(self._base_url))
            pages_scanned = 0

            while queue and not self._cancelled:
                if pages_scanned >= self._max_pages:
                    self.scan_progress.emit(
                        f"Reached max page limit ({self._max_pages}). Stopping scan."
                    )
                    break

                url, depth = queue.popleft()
                pages_scanned += 1

                # Show the URL path being scanned in the detail label
                parsed = urlparse(url)
                url_path = unquote(parsed.path) or "/"
                self.scan_detail.emit(f"{parsed.netloc}{url_path}")
                self.scan_progress.emit(
                    f"Scanning... {len(all_files)} files found"
                )

                try:
                    page_files, page_links = self._scan_page(url)
                except Exception as exc:
                    logger.warning("Error scanning %s: %s", url, exc)
                    self.scan_progress.emit(f"Error scanning {url}: {exc}")
                    continue

                # Filter by extensions if specified
                filtered = []
                for fi in page_files:
                    fi.depth = depth
                    if self._extensions is None or fi.extension in self._extensions:
                        filtered.append(fi.to_dict())

                all_files.extend(filtered)
                self.page_scanned.emit(url, depth, len(filtered))

                # Recursive: enqueue sub-pages
                if self._recursive and depth < self._max_depth:
                    for link in page_links:
                        norm = _normalise_url(link)
                        if norm not in visited and _is_same_domain(link, self._base_url):
                            visited.add(norm)
                            queue.append((link, depth + 1))

                # Politeness delay between pages
                if queue and self._delay > 0:
                    time.sleep(self._delay)

            if self._cancelled:
                self.scan_progress.emit("Scan cancelled.")
                self.scan_detail.emit("")
            else:
                # Deduplicate files by URL
                seen_urls: set[str] = set()
                unique_files: list[dict] = []
                for f in all_files:
                    if f["url"] not in seen_urls:
                        seen_urls.add(f["url"])
                        unique_files.append(f)

                # Try to fetch file sizes via HEAD requests
                _MAX_HEAD = 100
                if unique_files:
                    self.scan_detail.emit("")
                    self.scan_progress.emit(
                        f"Checking file sizes... (0/{len(unique_files)})"
                    )
                    for i, f in enumerate(unique_files):
                        if self._cancelled or i >= _MAX_HEAD:
                            break
                        size = self._try_get_file_size(f["url"])
                        if size >= 0:
                            f["size_hint"] = size
                        if (i + 1) % 5 == 0 or i + 1 == len(unique_files):
                            self.scan_progress.emit(
                                f"Checking file sizes... ({i + 1}/{len(unique_files)})"
                            )

                self.scan_detail.emit("")
                self.scan_progress.emit(
                    f"{len(unique_files)} files found"
                )
                self.files_found.emit(unique_files)

        except Exception as exc:
            logger.exception("Scanner worker error")
            self.scan_error.emit(str(exc))
        finally:
            if self._session:
                self._session.close()
            self.scan_finished.emit()

    def _try_get_file_size(self, url: str) -> int:
        """Try a HEAD request to get the file size. Returns -1 on failure."""
        if self._cancelled:
            return -1
        try:
            resp = self._session.head(url, timeout=2, allow_redirects=True)
            cl = resp.headers.get("Content-Length")
            return int(cl) if cl else -1
        except Exception:
            return -1

    def _scan_page(self, url: str) -> tuple[list[FileInfo], list[str]]:
        """Scan a single page and return (files, page_links_to_follow)."""
        resp = self._session.get(url, timeout=30, allow_redirects=True)
        resp.raise_for_status()

        content_type = resp.headers.get("Content-Type", "")
        if "text/html" not in content_type and "text/plain" not in content_type:
            # Not an HTML page — might be a direct file listing (e.g. Apache index)
            # Try to parse anyway if it looks like HTML
            if not resp.text.strip().startswith(("<", "<!DOCTYPE")):
                return [], []

        soup = BeautifulSoup(resp.text, "lxml")

        files: list[FileInfo] = []
        page_links: list[str] = []

        # Scan <a href="..."> links
        for tag in soup.find_all("a", href=True):
            href = tag["href"].strip()
            if not href or href.startswith(("#", "javascript:", "mailto:")):
                continue
            absolute = urljoin(url, href)
            ext = _get_file_extension(absolute)

            if ext and ext in ALL_EXTENSIONS:
                files.append(FileInfo(
                    url=absolute,
                    filename=_get_filename(absolute),
                    extension=ext,
                    size_hint=-1,
                    source_page=url,
                ))
            elif _looks_like_page(absolute):
                page_links.append(absolute)

        # Scan media tags
        for tag_name, attr in [("img", "src"), ("source", "src"), ("video", "src"), ("audio", "src")]:
            for tag in soup.find_all(tag_name, **{attr: True}):
                src = tag[attr].strip()
                if not src:
                    continue
                absolute = urljoin(url, src)
                ext = _get_file_extension(absolute)
                if ext and ext in ALL_EXTENSIONS:
                    files.append(FileInfo(
                        url=absolute,
                        filename=_get_filename(absolute),
                        extension=ext,
                        size_hint=-1,
                        source_page=url,
                    ))

        return files, page_links
