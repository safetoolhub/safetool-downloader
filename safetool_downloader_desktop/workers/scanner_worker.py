# This file is part of SafeTool Downloader, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Scanner worker — scans web pages for downloadable files with optional recursion."""

from __future__ import annotations

import logging
import re
import time
from collections import Counter, deque
from typing import Optional
from urllib.parse import urljoin, urlparse, urlunparse, unquote

import requests
from bs4 import BeautifulSoup
from PySide6.QtCore import QThread, Signal

from safetool_downloader_desktop.i18n import tr

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
    "Executables": [".exe", ".msi", ".dmg", ".pkg", ".deb", ".rpm", ".appimage", ".apk", ".run", ".bin"],
    "Disk Images": [".iso", ".img", ".ova", ".ovf", ".vmdk", ".vdi", ".vhd", ".vhdx", ".qcow2"],
}

ALL_EXTENSIONS: set[str] = set()
for exts in FILE_EXTENSIONS.values():
    ALL_EXTENSIONS.update(exts)

# Extensions that indicate a downloadable file (not an HTML page)
_PAGE_EXTENSIONS = {".html", ".htm", ".php", ".asp", ".aspx", ".jsp", ".shtml"}

# Content types that indicate an RSS/Atom feed
_RSS_CONTENT_TYPES = (
    "application/xml",
    "application/rss+xml",
    "text/xml",
    "application/atom+xml",
)

# Maximum recursion depth when following sitemap index files
_MAX_SITEMAP_INDEX_DEPTH = 3

# Query parameters used by Apache/nginx directory index sorting links
# (e.g. ?C=N;O=D, ?C=M;O=A, ?C=S;O=A, ?C=D;O=A). These produce the same
# content in a different sort order and must be skipped to avoid wasting
# the page budget during recursive scans.
_DIRECTORY_INDEX_SORT_RE = re.compile(r"^C=[NMSD];O=[AD]$")

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"
)


def _normalise_url(url: str) -> str:
    """Normalise a URL for dedup: strip fragment, trailing slash, lowercase host.

    Also strips Apache/nginx directory-index sorting query parameters so that
    the same directory with different sort orders is treated as a single page.
    """
    parsed = urlparse(url)
    path = parsed.path.rstrip("/") if parsed.path != "/" else "/"
    query = parsed.query
    # Strip directory-index sorting params (e.g. C=N;O=D)
    if query and _DIRECTORY_INDEX_SORT_RE.match(query):
        query = ""
    return urlunparse((
        parsed.scheme.lower(),
        parsed.netloc.lower(),
        path,
        parsed.params,
        query,
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


def _is_directory_index_sort_link(url: str) -> bool:
    """Return True if *url* is an Apache/nginx directory sorting link.

    These links (e.g. ``?C=N;O=D``) sort the same directory listing by
    name/date/size in ascending or descending order.  Following them
    wastes the page budget without discovering new content.
    """
    query = urlparse(url).query
    return bool(query and _DIRECTORY_INDEX_SORT_RE.match(query))


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


def _is_under_base_path(url: str, base_url: str) -> bool:
    """Check if *url* is under the same path prefix as *base_url*.

    e.g. base_url=https://example.com/Courses/CEH/ allows
    https://example.com/Courses/CEH/Module1/ but not https://example.com/Other/.
    """
    base_path = urlparse(base_url).path
    # Ensure base_path ends with "/" so we don't accidentally match siblings
    if not base_path.endswith("/"):
        base_path = base_path + "/"
    return urlparse(url).path.startswith(base_path)


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


def build_directory_tree_report(base_url: str, files: list[dict]) -> str:
    """Build a human-readable directory tree report from scan results.

    Returns a multi-line string showing the directory tree with per-directory
    file counts and extension breakdown, plus a global extension summary.
    """
    SEP = "─" * 72

    base_path = urlparse(base_url).path
    if not base_path.endswith("/"):
        base_path += "/"

    # dir_key (decoded relative path) → {"files": [...], "exts": Counter}
    DirEntry = dict  # {"files": list[str], "exts": Counter}
    dir_data: dict[str, DirEntry] = {"": {"files": [], "exts": Counter()}}

    for f in files:
        raw_path = unquote(urlparse(f["url"]).path)
        if raw_path.startswith(base_path):
            rel = raw_path[len(base_path):]
        else:
            rel = raw_path.lstrip("/")
        parts = [p for p in rel.split("/") if p]
        if not parts:
            continue
        filename = parts[-1]
        dir_parts = parts[:-1]
        ext = f.get("extension", "")
        # Ensure every ancestor directory exists in the map
        for i in range(len(dir_parts) + 1):
            k = "/".join(dir_parts[:i])
            if k not in dir_data:
                dir_data[k] = {"files": [], "exts": Counter()}
        key = "/".join(dir_parts)
        dir_data[key]["files"].append(filename)
        if ext:
            dir_data[key]["exts"][ext] += 1

    def _direct_subdirs(parent: str) -> list[str]:
        prefix = parent + "/" if parent else ""
        result = []
        for k in dir_data:
            if k == parent or not k.startswith(prefix):
                continue
            if "/" not in k[len(prefix):]:
                result.append(k)
        return sorted(result)

    lines: list[str] = []

    def _ext_summary(exts: Counter) -> str:
        if not exts:
            return ""
        return "  →  " + ", ".join(
            f"{e}\xd7{c}" for e, c in sorted(exts.items())
        )

    def _render(key: str, indent: str, last: bool) -> None:
        connector = "└── " if last else "├── "
        name = key.rsplit("/", 1)[-1]
        children = _direct_subdirs(key)
        entry = dir_data.get(key, {"files": [], "exts": Counter()})
        file_cnt = len(entry["files"])
        lines.append(
            f"{indent}{connector}{name}/"
            f"  [subdirs: {len(children)} | files: {file_cnt}]"
            f"{_ext_summary(entry['exts'])}"
        )
        child_indent = indent + ("    " if last else "│   ")
        for i, c in enumerate(children):
            _render(c, child_indent, i == len(children) - 1)

    root_name = base_path.rstrip("/").rsplit("/", 1)[-1] or "/"
    root_children = _direct_subdirs("")
    root_entry = dir_data.get("", {"files": [], "exts": Counter()})
    root_files = len(root_entry["files"])
    total_dirs = len(dir_data)
    total_files = sum(len(v["files"]) for v in dir_data.values())

    # All extensions across all dirs for the global summary
    all_exts: Counter = Counter()
    for entry in dir_data.values():
        all_exts.update(entry["exts"])

    lines.append(tr("scanner.tree_report_title"))
    lines.append(SEP)
    lines.append(tr("scanner.tree_report_base_url", url=base_url))
    lines.append(tr("scanner.tree_report_total", dirs=total_dirs, files=total_files))
    lines.append("")
    lines.append(
        f"   {root_name}/"
        f"  [subdirs: {len(root_children)} | files: {root_files}]"
        f"{_ext_summary(root_entry['exts'])}"
    )
    for i, c in enumerate(root_children):
        _render(c, "   ", i == len(root_children) - 1)
    lines.append("")
    lines.append(SEP)
    lines.append(tr("scanner.tree_report_extension_breakdown"))
    if all_exts:
        for ext, count in sorted(all_exts.items(), key=lambda x: (-x[1], x[0])):
            lines.append(f"  {ext:<22} {count:>5} file(s)")
    else:
        lines.append(f"  {tr('scanner.tree_report_none')}")
    lines.append("")
    lines.append(SEP)
    return "\n".join(lines)


def _log_directory_tree(base_url: str, files: list[dict]) -> None:
    """Log the directory tree report line-by-line at INFO level."""
    for line in build_directory_tree_report(base_url, files).splitlines():
        logger.info("%s", line)


class FileInfo:
    """Information about a discovered file."""

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
    page_limit_reached = Signal(int)  # emitted with the max_pages value when the limit is hit
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
        restrict_to_base_path: bool = True,
        max_files: int | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._base_url = url
        self._extensions = set(e.lower() for e in extensions) if extensions else None
        self._recursive = recursive
        self._max_depth = max_depth
        self._delay = delay
        self._max_pages = max_pages
        self._restrict_to_base_path = restrict_to_base_path
        self._max_files = max_files
        self._cancelled = False
        self._rss_mode = False
        self._session: Optional[requests.Session] = None

    def cancel(self) -> None:
        """Request cancellation of the scan."""
        self._cancelled = True

    @property
    def is_rss_feed(self) -> bool:
        """Whether the last scan detected an RSS/podcast feed."""
        return self._rss_mode

    def run(self) -> None:
        """Execute the scan in a background thread."""
        try:
            self._session = requests.Session()
            self._session.headers.update({"User-Agent": USER_AGENT})

            logger.info(
                "Starting scan: url=%s recursive=%s max_depth=%s max_pages=%s "
                "restrict_path=%s delay=%.1fs extensions=%s",
                self._base_url,
                self._recursive,
                self._max_depth,
                self._max_pages,
                self._restrict_to_base_path,
                self._delay,
                self._extensions or "ALL",
            )

            all_files: list[dict] = []
            visited: set[str] = set()
            # BFS queue: (url, depth)
            queue: deque[tuple[str, int]] = deque()
            queue.append((self._base_url, 0))
            visited.add(_normalise_url(self._base_url))
            pages_scanned = 0

            # --- Sitemap discovery (pre-BFS seeding) ---
            # Probe /sitemap.xml at the root of the domain before the BFS starts
            # so that its URLs can be used to seed the queue immediately.
            visited_sitemaps: set[str] = set()
            _parsed_base = urlparse(self._base_url)
            _sitemap_root = f"{_parsed_base.scheme}://{_parsed_base.netloc}/sitemap.xml"
            self.scan_progress.emit(tr("scanner.sitemap_probing"))
            _sm_files, _sm_pages = self._fetch_sitemap_urls(_sitemap_root, visited_sitemaps)
            if _sm_files or _sm_pages:
                logger.info(
                    "Sitemap discovery at %s: %d files, %d page URLs",
                    _sitemap_root, len(_sm_files), len(_sm_pages),
                )
                self.scan_progress.emit(
                    tr("scanner.sitemap_found",
                       page_count=len(_sm_pages),
                       file_count=len(_sm_files))
                )
                # Seed BFS queue with sitemap page URLs (only in recursive mode)
                if self._recursive:
                    for _pg_url in _sm_pages:
                        _norm = _normalise_url(_pg_url)
                        if _norm in visited:
                            continue
                        if not _is_same_domain(_pg_url, self._base_url):
                            continue
                        if self._restrict_to_base_path and not _is_under_base_path(
                            _pg_url, self._base_url
                        ):
                            continue
                        visited.add(_norm)
                        queue.append((_pg_url, 0))
                # Add sitemap file URLs directly (with the same filters as BFS files)
                for _fi in _sm_files:
                    if (
                        self._restrict_to_base_path
                        and not self._rss_mode
                        and not _is_under_base_path(_fi.url, self._base_url)
                    ):
                        continue
                    if self._extensions is None or _fi.extension in self._extensions:
                        all_files.append(_fi.to_dict())

            while queue and not self._cancelled:
                if pages_scanned >= self._max_pages:
                    logger.warning(
                        "Page limit reached (%d). Stopping scan. "
                        "Queue still has %d pages pending.",
                        self._max_pages,
                        len(queue),
                    )
                    self.scan_progress.emit(
                        tr("scanner.page_limit_reached", max_pages=self._max_pages)
                    )
                    self.page_limit_reached.emit(self._max_pages)
                    break

                url, depth = queue.popleft()
                pages_scanned += 1

                logger.info(
                    "Scanning page %d/%d (depth %d, queue %d): %s",
                    pages_scanned,
                    self._max_pages,
                    depth,
                    len(queue),
                    url,
                )

                # Show the URL path being scanned in the detail label
                parsed = urlparse(url)
                url_path = unquote(parsed.path) or "/"
                self.scan_detail.emit(f"{parsed.netloc}{url_path}")
                self.scan_progress.emit(
                    tr("scanner.scanning_files_found", count=len(all_files))
                )

                try:
                    page_files, page_links, page_sitemap_links = self._scan_page(url)
                except Exception as exc:
                    logger.warning("Error scanning %s: %s", url, exc)
                    self.scan_progress.emit(f"Error scanning {url}: {exc}")
                    continue

                logger.info(
                    "  Found %d files and %d page links on %s",
                    len(page_files),
                    len(page_links),
                    url,
                )

                # Process sitemaps declared in the page HTML (<link rel="sitemap">)
                for sm_url in page_sitemap_links:
                    if self._cancelled:
                        break
                    sm_files, sm_pages = self._fetch_sitemap_urls(sm_url, visited_sitemaps)
                    page_files.extend(sm_files)
                    if self._recursive:
                        page_links.extend(sm_pages)
                    if sm_files or sm_pages:
                        logger.info(
                            "  Inline sitemap %s: +%d files, +%d pages",
                            sm_url, len(sm_files), len(sm_pages),
                        )

                # Filter by extensions and base path if specified
                filtered = []
                for fi in page_files:
                    fi.depth = depth
                    
                    if self._restrict_to_base_path and not self._rss_mode and not _is_under_base_path(fi.url, self._base_url):
                        logger.debug("  Skipped file (outside base path): %s", fi.url)
                        continue

                    if self._extensions is None or fi.extension in self._extensions:
                        filtered.append(fi.to_dict())
                    else:
                        logger.debug(
                            "  Skipped file (extension filter): %s (%s)",
                            fi.filename,
                            fi.extension,
                        )

                # Truncate to respect max_files limit before adding
                if self._max_files is not None:
                    remaining = self._max_files - len(all_files)
                    if remaining <= 0:
                        logger.info(
                            "Max files limit (%d) already reached — stopping scan.",
                            self._max_files,
                        )
                        queue.clear()
                        break
                    if len(filtered) > remaining:
                        filtered = filtered[:remaining]

                all_files.extend(filtered)
                self.page_scanned.emit(url, depth, len(filtered))

                # Stop as soon as the file limit is reached
                if self._max_files is not None and len(all_files) >= self._max_files:
                    logger.info(
                        "Max files limit (%d) reached (%d collected) — stopping scan.",
                        self._max_files, len(all_files),
                    )
                    queue.clear()
                    break

                # Recursive: enqueue sub-pages
                if self._recursive and depth < self._max_depth:
                    enqueued = 0
                    for link in page_links:
                        norm = _normalise_url(link)
                        if norm in visited:
                            logger.debug("  Skip (already visited): %s", link)
                            continue
                        if not _is_same_domain(link, self._base_url):
                            logger.debug("  Skip (different domain): %s", link)
                            continue
                        if self._restrict_to_base_path and not _is_under_base_path(
                            link, self._base_url
                        ):
                            logger.debug("  Skip (outside base path): %s", link)
                            continue
                        visited.add(norm)
                        queue.append((link, depth + 1))
                        enqueued += 1
                    if enqueued:
                        logger.info(
                            "  Enqueued %d new pages at depth %d (queue size: %d)",
                            enqueued,
                            depth + 1,
                            len(queue),
                        )
                elif self._recursive and depth >= self._max_depth:
                    logger.info(
                        "  Max depth %d reached — not following %d page links",
                        self._max_depth,
                        len(page_links),
                    )

                # Politeness delay between pages
                if queue and self._delay > 0:
                    time.sleep(self._delay)

            if self._cancelled:
                logger.info("Scan cancelled by user.")
                self.scan_progress.emit(tr("scanner.scan_cancelled"))
                self.scan_detail.emit("")
            else:
                # Deduplicate files by URL
                seen_urls: set[str] = set()
                unique_files: list[dict] = []
                for f in all_files:
                    if f["url"] not in seen_urls:
                        seen_urls.add(f["url"])
                        unique_files.append(f)

                dupes = len(all_files) - len(unique_files)
                logger.info(
                    "Scan complete: %d pages scanned, %d files found "
                    "(%d duplicates removed), %d unique files.",
                    pages_scanned,
                    len(all_files),
                    dupes,
                    len(unique_files),
                )

                # Log directory tree so the user can verify all folders were visited
                if unique_files:
                    _log_directory_tree(self._base_url, unique_files)

                # Try to fetch file sizes via HEAD requests
                _MAX_HEAD = 100
                if unique_files:
                    self.scan_detail.emit("")
                    self.scan_progress.emit(
                        tr("scanner.checking_sizes_start", total=len(unique_files))
                    )
                    for i, f in enumerate(unique_files):
                        if self._cancelled or i >= _MAX_HEAD:
                            break
                        size = self._try_get_file_size(f["url"])
                        if size >= 0:
                            f["size_hint"] = size
                        if (i + 1) % 5 == 0 or i + 1 == len(unique_files):
                            self.scan_progress.emit(
                                tr("scanner.checking_sizes", current=i + 1, total=len(unique_files))
                            )

                self.scan_detail.emit("")
                self.scan_progress.emit(
                    tr("scanner.files_found", count=len(unique_files))
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

    def _scan_page(self, url: str) -> tuple[list[FileInfo], list[str], list[str]]:
        """Scan a single page and return (files, page_links, sitemap_links).

        *sitemap_links* are URLs found in ``<link rel="sitemap">`` tags that
        the caller should process via :meth:`_fetch_sitemap_urls`.
        """
        resp = self._session.get(url, timeout=30, allow_redirects=True)
        resp.raise_for_status()

        content_type = resp.headers.get("Content-Type", "")
        logger.debug("  GET %s → %d, Content-Type: %s", url, resp.status_code, content_type)

        # Check for RSS/Atom feeds (e.g. podcast feeds)
        if any(ct in content_type for ct in _RSS_CONTENT_TYPES):
            text = resp.text.strip()
            if "<rss" in text[:1000] or "<feed" in text[:1000]:
                logger.info("  Detected RSS/Atom feed — switching to RSS parser")
                return self._scan_rss_feed(url, text)

        if "text/html" not in content_type and "text/plain" not in content_type:
            # Not an HTML page — might be a direct file listing (e.g. Apache index)
            # Try to parse anyway if it looks like HTML
            if not resp.text.strip().startswith(("<", "<!DOCTYPE")):
                logger.debug("  Not HTML and doesn't look like markup — skipping parse")
                return [], [], []

        soup = BeautifulSoup(resp.text, "lxml")

        files: list[FileInfo] = []
        page_links: list[str] = []
        sitemap_links: list[str] = []

        # Scan <a href="..."> links
        for tag in soup.find_all("a", href=True):
            href = tag["href"].strip()
            if not href or href.startswith(("#", "javascript:", "mailto:")):
                continue
            absolute = urljoin(url, href)

            # Skip Apache/nginx directory-index sorting links — they show
            # the same content sorted differently and waste the page budget.
            if _is_directory_index_sort_link(absolute):
                logger.debug("  Skip sort link: %s", href)
                continue

            ext = _get_file_extension(absolute)

            if ext and ext in ALL_EXTENSIONS:
                # Known downloadable file extension
                logger.debug("  File (known ext %s): %s", ext, _get_filename(absolute))
                files.append(FileInfo(
                    url=absolute,
                    filename=_get_filename(absolute),
                    extension=ext,
                    size_hint=-1,
                    source_page=url,
                ))
            elif _looks_like_page(absolute):
                logger.debug("  Page link: %s", absolute)
                page_links.append(absolute)
            elif ext:
                # Unknown extension — still treat as a downloadable file.
                # This catches .iso, .deb, .exe, .msi, .ova, .vmdk, etc.
                logger.debug("  File (other ext %s): %s", ext, _get_filename(absolute))
                files.append(FileInfo(
                    url=absolute,
                    filename=_get_filename(absolute),
                    extension=ext,
                    size_hint=-1,
                    source_page=url,
                ))
            else:
                logger.debug("  Ignored link (no ext, not page-like): %s", absolute)

        # Scan media tags
        for tag_name, attr in [("img", "src"), ("source", "src"), ("video", "src"), ("audio", "src")]:
            for tag in soup.find_all(tag_name, **{attr: True}):
                src = tag[attr].strip()
                if not src:
                    continue
                absolute = urljoin(url, src)
                ext = _get_file_extension(absolute)
                if ext and ext in ALL_EXTENSIONS:
                    logger.debug("  Media file (%s %s): %s", tag_name, ext, _get_filename(absolute))
                    files.append(FileInfo(
                        url=absolute,
                        filename=_get_filename(absolute),
                        extension=ext,
                        size_hint=-1,
                        source_page=url,
                    ))

        # Detect sitemaps declared in <link rel="sitemap" href="..."> tags
        for link_tag in soup.find_all("link", rel=True):
            rel = link_tag.get("rel", [])
            if isinstance(rel, list):
                rel_vals = [r.lower() for r in rel]
            else:
                rel_vals = [rel.lower()]
            if "sitemap" in rel_vals:
                href = link_tag.get("href", "").strip()
                if href:
                    sitemap_links.append(urljoin(url, href))

        logger.debug(
            "  Totals for %s: %d files, %d page links, %d sitemap links",
            url, len(files), len(page_links), len(sitemap_links),
        )
        return files, page_links, sitemap_links

    def _scan_rss_feed(self, url: str, text: str) -> tuple[list[FileInfo], list[str], list[str]]:
        """Parse an RSS/Atom feed and extract enclosure URLs (e.g. podcast episodes).

        RSS feeds embed media files in ``<enclosure url="..." />`` tags inside
        each ``<item>``.  This method extracts those URLs and builds
        human-readable filenames from the episode ``<title>`` and ``<pubDate>``
        instead of the typically opaque CDN filenames.

        Also collects channel-level metadata (podcast title, author, cover art
        URL) and per-episode metadata (title, date, episode/season number,
        description) stored in ``FileInfo.meta`` for ID3 tagging on download.
        """
        self._rss_mode = True
        soup = BeautifulSoup(text, "xml")

        files: list[FileInfo] = []

        # ── Channel-level metadata ────────────────────────────────────────────
        channel = soup.find("channel")
        podcast_title = ""
        podcast_author = ""
        podcast_image_url = ""

        if channel:
            ch_title = channel.find("title")
            if ch_title:
                podcast_title = ch_title.get_text(strip=True)

            # <itunes:author> preferred; fall back to <managingEditor>
            itunes_author = channel.find("itunes:author")
            if itunes_author:
                podcast_author = itunes_author.get_text(strip=True)
            else:
                managing = channel.find("managingEditor")
                if managing:
                    podcast_author = managing.get_text(strip=True)

            # <itunes:image href="..."> preferred; fall back to <image><url>
            itunes_img = channel.find("itunes:image")
            if itunes_img and itunes_img.get("href"):
                podcast_image_url = itunes_img["href"].strip()
            else:
                img_tag = channel.find("image")
                if img_tag:
                    url_tag = img_tag.find("url")
                    if url_tag:
                        podcast_image_url = url_tag.get_text(strip=True)

        # ── Per-episode items ─────────────────────────────────────────────────
        episode_index = 0
        for item in soup.find_all("item"):
            enclosure = item.find("enclosure")
            if not enclosure or not enclosure.get("url"):
                continue

            file_url = enclosure["url"].strip()
            ext = _get_file_extension(file_url)

            # Build a human-readable filename from the episode title
            title_tag = item.find("title")
            title_text = title_tag.get_text(strip=True) if title_tag else ""

            if title_text:
                safe_title = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', title_text)
                safe_title = safe_title.replace('/', '-')
                filename = f"{safe_title}{ext}" if ext else f"{safe_title}.mp3"
            else:
                filename = _get_filename(file_url)

            # Get file size from the enclosure length attribute
            size_hint = -1
            length = enclosure.get("length")
            if length:
                try:
                    size_hint = int(length)
                except ValueError:
                    pass

            # ── Per-episode metadata for ID3 tagging ─────────────────────────
            episode_index += 1

            pub_date = ""
            pub_date_tag = item.find("pubDate")
            if pub_date_tag:
                pub_date = pub_date_tag.get_text(strip=True)

            episode_number = ""
            ep_tag = item.find("itunes:episode")
            if ep_tag:
                episode_number = ep_tag.get_text(strip=True)

            season_number = ""
            season_tag = item.find("itunes:season")
            if season_tag:
                season_number = season_tag.get_text(strip=True)

            track_str = episode_number or str(episode_index)
            if season_number:
                track_str = f"{season_number}x{track_str}"

            description = ""
            desc_tag = item.find("itunes:summary") or item.find("description")
            if desc_tag:
                raw = desc_tag.get_text(separator=" ", strip=True)
                description = raw[:500]  # cap to avoid huge comments

            duration_str = ""
            duration_tag = item.find("itunes:duration")
            if duration_tag:
                duration_str = duration_tag.get_text(strip=True)

            meta: dict = {
                "rss_title": title_text or _get_filename(file_url),
                "rss_album": podcast_title,
                "rss_artist": podcast_author,
                "rss_track": track_str,
                "rss_date": pub_date,
                "rss_description": description,
                "rss_image_url": podcast_image_url,
                "rss_duration": duration_str,
            }

            files.append(FileInfo(
                url=file_url,
                filename=_sanitize_filename(filename),
                extension=ext or ".mp3",
                size_hint=size_hint,
                size_hint_approx=size_hint > 0,  # RSS-declared sizes are approximate
                source_page=url,
                meta=meta,
            ))

        logger.info(
            "  RSS feed parsed: %d episodes with enclosures found", len(files)
        )
        return files, [], []

    def _fetch_sitemap_urls(
        self,
        sitemap_url: str,
        visited_sitemaps: set[str],
        index_depth: int = 0,
    ) -> tuple[list[FileInfo], list[str]]:
        """Fetch and parse a sitemap or sitemap index.

        Handles both ``<sitemapindex>`` (which references child sitemaps) and
        ``<urlset>`` (which lists canonical page and file URLs).  Sitemap index
        files are followed recursively up to *_MAX_SITEMAP_INDEX_DEPTH* levels.

        Returns:
            A 2-tuple ``(file_infos, page_urls)`` where *file_infos* are
            directly downloadable files found in the sitemap, and *page_urls*
            are page links suitable for adding to the BFS queue.
        """
        if index_depth > _MAX_SITEMAP_INDEX_DEPTH:
            logger.debug(
                "  Sitemap index depth limit (%d) reached at %s",
                _MAX_SITEMAP_INDEX_DEPTH,
                sitemap_url,
            )
            return [], []

        norm = _normalise_url(sitemap_url)
        if norm in visited_sitemaps:
            return [], []
        visited_sitemaps.add(norm)

        logger.debug(
            "  Fetching sitemap: %s (index_depth=%d)", sitemap_url, index_depth
        )
        try:
            resp = self._session.get(sitemap_url, timeout=15, allow_redirects=True)
            resp.raise_for_status()
        except Exception as exc:
            logger.debug("  Sitemap fetch failed for %s: %s", sitemap_url, exc)
            return [], []

        text = resp.text.strip()
        if not text.startswith("<"):
            return [], []

        soup = BeautifulSoup(text, "xml")
        file_infos: list[FileInfo] = []
        page_urls: list[str] = []

        # Sitemap index: <sitemapindex><sitemap><loc>…</loc></sitemap>…</sitemapindex>
        sitemapindex = soup.find("sitemapindex")
        if sitemapindex:
            logger.info("  Sitemap index at %s — following child sitemaps", sitemap_url)
            for sitemap_tag in sitemapindex.find_all("sitemap"):
                loc_tag = sitemap_tag.find("loc")
                if loc_tag:
                    child_url = loc_tag.get_text(strip=True)
                    if child_url and not self._cancelled:
                        c_files, c_pages = self._fetch_sitemap_urls(
                            child_url, visited_sitemaps, index_depth + 1
                        )
                        file_infos.extend(c_files)
                        page_urls.extend(c_pages)
            return file_infos, page_urls

        # Regular URL set: <urlset><url><loc>…</loc></url>…</urlset>
        urlset = soup.find("urlset")
        if urlset:
            logger.info("  URL-set sitemap at %s", sitemap_url)
            for url_tag in urlset.find_all("url"):
                loc_tag = url_tag.find("loc")
                if not loc_tag:
                    continue
                url_text = loc_tag.get_text(strip=True)
                if not url_text:
                    continue

                ext = _get_file_extension(url_text)
                if ext and ext in ALL_EXTENSIONS:
                    file_infos.append(FileInfo(
                        url=url_text,
                        filename=_get_filename(url_text),
                        extension=ext,
                        size_hint=-1,
                        source_page=sitemap_url,
                        depth=0,
                    ))
                elif _looks_like_page(url_text):
                    page_urls.append(url_text)
                elif ext:
                    # Unknown extension — treat as downloadable file
                    file_infos.append(FileInfo(
                        url=url_text,
                        filename=_get_filename(url_text),
                        extension=ext,
                        size_hint=-1,
                        source_page=sitemap_url,
                        depth=0,
                    ))

        return file_infos, page_urls
