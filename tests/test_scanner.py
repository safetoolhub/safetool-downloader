# This file is part of SafeTool Downloader, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Tests for scanner_worker — URL helpers and FileInfo."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from safetool_downloader_desktop.workers.scanner_worker import (
    ALL_EXTENSIONS,
    FILE_EXTENSIONS,
    FileInfo,
    ScannerWorker,
    _get_file_extension,
    _get_filename,
    _is_directory_index_sort_link,
    _is_same_domain,
    _looks_like_page,
    _normalise_url,
    _sanitize_filename,
)


class TestNormaliseUrl:
    """URL normalisation for deduplication."""

    def test_strips_fragment(self) -> None:
        assert _normalise_url("https://example.com/page#section") == \
               _normalise_url("https://example.com/page")

    def test_strips_trailing_slash(self) -> None:
        assert _normalise_url("https://example.com/path/") == \
               _normalise_url("https://example.com/path")

    def test_lowercases_host(self) -> None:
        assert _normalise_url("https://EXAMPLE.COM/path") == \
               _normalise_url("https://example.com/path")

    def test_preserves_query(self) -> None:
        url = _normalise_url("https://example.com/page?id=1")
        assert "id=1" in url

    def test_root_slash_preserved(self) -> None:
        url = _normalise_url("https://example.com/")
        assert url.endswith("/")

    def test_strips_apache_sort_query(self) -> None:
        """Apache sort links like ?C=N;O=D should normalise to the same URL."""
        base = _normalise_url("https://example.com/dir/")
        assert _normalise_url("https://example.com/dir/?C=N;O=D") == base
        assert _normalise_url("https://example.com/dir/?C=M;O=A") == base
        assert _normalise_url("https://example.com/dir/?C=S;O=A") == base
        assert _normalise_url("https://example.com/dir/?C=D;O=D") == base


class TestDirectoryIndexSortLink:
    """Detection of Apache/nginx directory-index sorting links."""

    def test_detects_sort_links(self) -> None:
        assert _is_directory_index_sort_link("https://example.com/dir/?C=N;O=D")
        assert _is_directory_index_sort_link("https://example.com/dir/?C=M;O=A")
        assert _is_directory_index_sort_link("https://example.com/dir/?C=S;O=A")
        assert _is_directory_index_sort_link("https://example.com/dir/?C=D;O=D")

    def test_ignores_normal_queries(self) -> None:
        assert not _is_directory_index_sort_link("https://example.com/page?id=1")
        assert not _is_directory_index_sort_link("https://example.com/page")

    def test_ignores_partial_matches(self) -> None:
        assert not _is_directory_index_sort_link("https://example.com/?C=X;O=D")
        assert not _is_directory_index_sort_link("https://example.com/?other=C=N;O=D")


class TestGetFileExtension:
    """File extension extraction from URLs."""

    def test_simple_extension(self) -> None:
        assert _get_file_extension("https://example.com/file.pdf") == ".pdf"

    def test_compound_tar_gz(self) -> None:
        assert _get_file_extension("https://example.com/archive.tar.gz") == ".tar.gz"

    def test_no_extension(self) -> None:
        assert _get_file_extension("https://example.com/page") == ""

    def test_query_stripped(self) -> None:
        ext = _get_file_extension("https://example.com/file.pdf?v=2")
        assert ext == ".pdf"

    def test_uppercase_normalised(self) -> None:
        assert _get_file_extension("https://example.com/file.PDF") == ".pdf"

    def test_encoded_url(self) -> None:
        assert _get_file_extension("https://example.com/my%20file.zip") == ".zip"


class TestGetFilename:
    """Filename extraction from URLs."""

    def test_simple(self) -> None:
        assert _get_filename("https://example.com/docs/report.pdf") == "report.pdf"

    def test_trailing_slash(self) -> None:
        assert _get_filename("https://example.com/docs/") == "docs"

    def test_root_url(self) -> None:
        name = _get_filename("https://example.com/")
        assert name  # Should return something, not empty

    def test_encoded_characters(self) -> None:
        name = _get_filename("https://example.com/my%20file.txt")
        assert "file" in name


class TestIsSameDomain:
    """Same-domain check."""

    def test_same_domain(self) -> None:
        assert _is_same_domain(
            "https://example.com/page2", "https://example.com/page1"
        )

    def test_different_domain(self) -> None:
        assert not _is_same_domain(
            "https://other.com/page", "https://example.com/page"
        )

    def test_case_insensitive(self) -> None:
        assert _is_same_domain(
            "https://EXAMPLE.COM/page", "https://example.com/page"
        )

    def test_subdomain_is_different(self) -> None:
        assert not _is_same_domain(
            "https://sub.example.com/page", "https://example.com/page"
        )


class TestLooksLikePage:
    """Heuristic for page vs file."""

    def test_html_extension(self) -> None:
        assert _looks_like_page("https://example.com/page.html")

    def test_php_extension(self) -> None:
        assert _looks_like_page("https://example.com/index.php")

    def test_no_extension(self) -> None:
        assert _looks_like_page("https://example.com/about")

    def test_file_extension(self) -> None:
        assert not _looks_like_page("https://example.com/file.pdf")

    def test_directory_url(self) -> None:
        assert _looks_like_page("https://example.com/docs/")


class TestSanitizeFilename:
    """Filename sanitization."""

    def test_removes_slashes(self) -> None:
        assert "/" not in _sanitize_filename("path/to/file.txt")
        assert "\\" not in _sanitize_filename("path\\to\\file.txt")

    def test_removes_null_bytes(self) -> None:
        assert "\x00" not in _sanitize_filename("file\x00.txt")

    def test_limits_length(self) -> None:
        long_name = "a" * 300
        assert len(_sanitize_filename(long_name)) <= 200

    def test_fallback_on_empty(self) -> None:
        result = _sanitize_filename("")
        assert result  # Should not be empty


class TestFileInfo:
    """FileInfo data class."""

    def test_creation(self) -> None:
        fi = FileInfo(
            url="https://example.com/file.pdf",
            filename="file.pdf",
            extension=".pdf",
            size_hint=1024,
            source_page="https://example.com/",
            depth=0,
        )
        assert fi.url == "https://example.com/file.pdf"
        assert fi.filename == "file.pdf"
        assert fi.extension == ".pdf"
        assert fi.size_hint == 1024
        assert fi.depth == 0

    def test_to_dict(self) -> None:
        fi = FileInfo(
            url="https://example.com/file.pdf",
            filename="file.pdf",
            extension=".pdf",
            size_hint=-1,
            source_page="https://example.com/",
        )
        d = fi.to_dict()
        assert d["url"] == "https://example.com/file.pdf"
        assert d["filename"] == "file.pdf"
        assert d["extension"] == ".pdf"
        assert d["depth"] == 0

    def test_filename_sanitized(self) -> None:
        fi = FileInfo(
            url="https://example.com/../../../etc/passwd",
            filename="../../../etc/passwd",
            extension="",
            size_hint=-1,
            source_page="https://example.com/",
        )
        assert "/" not in fi.filename
        assert "\\" not in fi.filename


class TestFileExtensions:
    """Extension registry is well-formed."""

    def test_all_categories_have_extensions(self) -> None:
        for cat, exts in FILE_EXTENSIONS.items():
            assert len(exts) > 0, f"Category {cat} has no extensions"

    def test_all_extensions_start_with_dot(self) -> None:
        for cat, exts in FILE_EXTENSIONS.items():
            for ext in exts:
                assert ext.startswith("."), f"{ext} in {cat} missing dot prefix"

    def test_all_extensions_aggregated(self) -> None:
        total = sum(len(exts) for exts in FILE_EXTENSIONS.values())
        assert len(ALL_EXTENSIONS) <= total  # Dedup possible
        assert len(ALL_EXTENSIONS) > 0


# ---------------------------------------------------------------------------
# Sitemap parsing tests
# ---------------------------------------------------------------------------

def _make_worker() -> ScannerWorker:
    """Return a ScannerWorker with a mock requests.Session attached."""
    worker = ScannerWorker.__new__(ScannerWorker)
    worker._base_url = "https://example.com/"
    worker._extensions = None
    worker._recursive = True
    worker._max_depth = 2
    worker._delay = 0.0
    worker._max_pages = 100
    worker._restrict_to_base_path = False
    worker._max_files = None
    worker._cancelled = False
    worker._rss_mode = False
    worker._session = MagicMock()
    return worker


def _mock_response(text: str, status_code: int = 200):
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    resp.raise_for_status = MagicMock()
    return resp


_URLSET_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/page-1/</loc></url>
  <url><loc>https://example.com/files/report.pdf</loc></url>
  <url><loc>https://example.com/images/photo.jpg</loc></url>
  <url><loc>https://example.com/about/</loc></url>
</urlset>
"""

_SITEMAP_INDEX_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap><loc>https://example.com/sitemap-pages.xml</loc></sitemap>
  <sitemap><loc>https://example.com/sitemap-files.xml</loc></sitemap>
</sitemapindex>
"""

_SITEMAP_PAGES_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/blog/post-1/</loc></url>
</urlset>
"""

_SITEMAP_FILES_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/downloads/data.zip</loc></url>
</urlset>
"""


class TestFetchSitemapUrls:
    """Unit tests for ScannerWorker._fetch_sitemap_urls."""

    def test_urlset_splits_files_and_pages(self) -> None:
        worker = _make_worker()
        worker._session.get.return_value = _mock_response(_URLSET_XML)
        files, pages = worker._fetch_sitemap_urls(
            "https://example.com/sitemap.xml", set()
        )
        file_urls = {f.url for f in files}
        assert "https://example.com/files/report.pdf" in file_urls
        assert "https://example.com/images/photo.jpg" in file_urls
        assert "https://example.com/page-1/" in pages
        assert "https://example.com/about/" in pages
        # File URLs must not appear in pages
        assert "https://example.com/files/report.pdf" not in pages

    def test_urlset_correct_extensions(self) -> None:
        worker = _make_worker()
        worker._session.get.return_value = _mock_response(_URLSET_XML)
        files, _ = worker._fetch_sitemap_urls(
            "https://example.com/sitemap.xml", set()
        )
        exts = {f.extension for f in files}
        assert ".pdf" in exts
        assert ".jpg" in exts

    def test_sitemap_index_follows_children(self) -> None:
        worker = _make_worker()
        responses = {
            "https://example.com/sitemap.xml": _SITEMAP_INDEX_XML,
            "https://example.com/sitemap-pages.xml": _SITEMAP_PAGES_XML,
            "https://example.com/sitemap-files.xml": _SITEMAP_FILES_XML,
        }
        worker._session.get.side_effect = (
            lambda url, **kw: _mock_response(responses[url])
        )
        files, pages = worker._fetch_sitemap_urls(
            "https://example.com/sitemap.xml", set()
        )
        assert any(f.url == "https://example.com/downloads/data.zip" for f in files)
        assert "https://example.com/blog/post-1/" in pages

    def test_deduplicates_via_visited_set(self) -> None:
        worker = _make_worker()
        worker._session.get.return_value = _mock_response(_URLSET_XML)
        visited: set[str] = set()
        worker._fetch_sitemap_urls("https://example.com/sitemap.xml", visited)
        # Second call with same visited set must be a no-op (no HTTP request)
        worker._session.get.reset_mock()
        files, pages = worker._fetch_sitemap_urls(
            "https://example.com/sitemap.xml", visited
        )
        worker._session.get.assert_not_called()
        assert files == []
        assert pages == []

    def test_returns_empty_on_http_error(self) -> None:
        worker = _make_worker()
        worker._session.get.side_effect = Exception("Connection refused")
        files, pages = worker._fetch_sitemap_urls(
            "https://example.com/sitemap.xml", set()
        )
        assert files == []
        assert pages == []

    def test_returns_empty_for_non_xml_content(self) -> None:
        worker = _make_worker()
        worker._session.get.return_value = _mock_response("<!DOCTYPE html><html></html>")
        files, pages = worker._fetch_sitemap_urls(
            "https://example.com/sitemap.xml", set()
        )
        # No sitemapindex or urlset — returns empty
        assert files == []
        assert pages == []

    def test_index_depth_limit(self) -> None:
        """Recursion must stop at _MAX_SITEMAP_INDEX_DEPTH."""
        worker = _make_worker()
        # Exceeding depth limit returns empty without fetching
        files, pages = worker._fetch_sitemap_urls(
            "https://example.com/deep.xml", set(), index_depth=10
        )
        worker._session.get.assert_not_called()
        assert files == []
        assert pages == []


# ---------------------------------------------------------------------------
# _scan_page — sitemap link detection
# ---------------------------------------------------------------------------

def _make_html_response(html: str, status_code: int = 200):
    """Fake requests.Response for HTML pages (with proper Content-Type dict)."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = html
    resp.headers = {"Content-Type": "text/html; charset=utf-8"}
    resp.raise_for_status = MagicMock()
    return resp


class TestScanPageSitemapLinks:
    """_scan_page returns sitemap URLs as the third element of its tuple."""

    def test_detects_link_rel_sitemap(self) -> None:
        worker = _make_worker()
        html = (
            '<!DOCTYPE html><html><head>'
            '<link rel="sitemap" href="/sitemap.xml" />'
            '</head><body></body></html>'
        )
        worker._session.get.return_value = _make_html_response(html)
        _, _, sitemaps = worker._scan_page("https://example.com/")
        assert "https://example.com/sitemap.xml" in sitemaps

    def test_no_sitemap_link_returns_empty_list(self) -> None:
        worker = _make_worker()
        html = "<!DOCTYPE html><html><head></head><body></body></html>"
        worker._session.get.return_value = _make_html_response(html)
        _, _, sitemaps = worker._scan_page("https://example.com/")
        assert sitemaps == []

    def test_multiple_sitemap_links_all_collected(self) -> None:
        worker = _make_worker()
        html = (
            '<!DOCTYPE html><html><head>'
            '<link rel="sitemap" href="/sitemap-pages.xml" />'
            '<link rel="sitemap" href="/sitemap-files.xml" />'
            '</head><body></body></html>'
        )
        worker._session.get.return_value = _make_html_response(html)
        _, _, sitemaps = worker._scan_page("https://example.com/")
        assert "https://example.com/sitemap-pages.xml" in sitemaps
        assert "https://example.com/sitemap-files.xml" in sitemaps
        assert len(sitemaps) == 2

    def test_relative_href_resolved_to_absolute(self) -> None:
        worker = _make_worker()
        html = (
            '<!DOCTYPE html><html><head>'
            '<link rel="sitemap" href="sitemap.xml" />'
            '</head><body></body></html>'
        )
        worker._session.get.return_value = _make_html_response(html)
        _, _, sitemaps = worker._scan_page("https://example.com/blog/")
        assert "https://example.com/blog/sitemap.xml" in sitemaps

    def test_sitemap_links_not_in_page_links(self) -> None:
        """Sitemap URLs must not bleed into page_links."""
        worker = _make_worker()
        html = (
            '<!DOCTYPE html><html><head>'
            '<link rel="sitemap" href="/sitemap.xml" />'
            '</head><body><a href="/about/">About</a></body></html>'
        )
        worker._session.get.return_value = _make_html_response(html)
        files, page_links, sitemaps = worker._scan_page("https://example.com/")
        assert "/sitemap.xml" not in str(page_links)
        assert "https://example.com/sitemap.xml" in sitemaps
        assert any("about" in p for p in page_links)


# ---------------------------------------------------------------------------
# run() — sitemap probe integration
# ---------------------------------------------------------------------------

def _run_with_mocks(
    url: str,
    fetch_sitemap_fn,
    scan_page_fn,
    **kwargs,
) -> list[dict]:
    """Run ScannerWorker with mocked _fetch_sitemap_urls and _scan_page."""
    collected: list[dict] = []
    worker = ScannerWorker(url=url, delay=0.0, max_pages=10, **kwargs)
    worker.files_found.connect(lambda files: collected.extend(files))
    with patch.object(worker, "_fetch_sitemap_urls", side_effect=fetch_sitemap_fn):
        with patch.object(worker, "_scan_page", side_effect=scan_page_fn):
            with patch.object(worker, "_try_get_file_size", return_value=-1):
                worker.run()
    return collected


def _sm_fi(url: str, ext: str = ".pdf") -> "FileInfo":
    return FileInfo(
        url=url,
        filename=url.rsplit("/", 1)[-1],
        extension=ext,
        size_hint=-1,
        source_page="https://example.com/sitemap.xml",
        depth=0,
    )


class TestScannerWorkerSitemapIntegration:
    """ScannerWorker.run() correctly uses sitemap data."""

    def test_pre_bfs_probe_files_appear_in_results(self) -> None:
        """Files discovered in the root sitemap.xml are included in files_found."""
        probe_file = _sm_fi("https://example.com/docs/guide.pdf")

        call_count = [0]

        def fetch_sm(url, visited, index_depth=0):
            call_count[0] += 1
            if call_count[0] == 1:  # pre-BFS probe
                return ([probe_file], [])
            return ([], [])

        files = _run_with_mocks(
            url="https://example.com/",
            fetch_sitemap_fn=fetch_sm,
            scan_page_fn=lambda u: ([], [], []),
        )
        assert any(f["url"] == "https://example.com/docs/guide.pdf" for f in files)

    def test_pre_bfs_probe_pages_seed_bfs_in_recursive_mode(self) -> None:
        """Page URLs from the sitemap probe are added to the BFS queue when recursive."""
        scanned_urls: list[str] = []

        def fetch_sm(url, visited, index_depth=0):
            return ([], ["https://example.com/from-sitemap/"])

        def scan_page(url):
            scanned_urls.append(url)
            if url == "https://example.com/from-sitemap/":
                return ([_sm_fi("https://example.com/from-sitemap/file.pdf")], [], [])
            return ([], [], [])

        files = _run_with_mocks(
            url="https://example.com/",
            fetch_sitemap_fn=fetch_sm,
            scan_page_fn=scan_page,
            recursive=True,
            max_depth=2,
        )
        assert "https://example.com/from-sitemap/" in scanned_urls
        assert any(f["url"] == "https://example.com/from-sitemap/file.pdf" for f in files)

    def test_pre_bfs_probe_pages_not_added_without_recursive(self) -> None:
        """Without recursive mode, sitemap page URLs are NOT enqueued."""
        scanned_urls: list[str] = []

        def fetch_sm(url, visited, index_depth=0):
            return ([], ["https://example.com/from-sitemap/"])

        def scan_page(url):
            scanned_urls.append(url)
            return ([], [], [])

        _run_with_mocks(
            url="https://example.com/",
            fetch_sitemap_fn=fetch_sm,
            scan_page_fn=scan_page,
            recursive=False,
        )
        assert "https://example.com/from-sitemap/" not in scanned_urls

    def test_inline_sitemap_processed_during_bfs(self) -> None:
        """When _scan_page returns a sitemap link, _fetch_sitemap_urls is called for it."""
        sm_file = _sm_fi("https://example.com/inline/asset.pdf")
        inline_sm_url = "https://example.com/inline-sitemap.xml"

        fetch_calls: list[str] = []

        def fetch_sm(url, visited, index_depth=0):
            fetch_calls.append(url)
            if inline_sm_url in url:
                return ([sm_file], [])
            return ([], [])

        def scan_page(url):
            # Main page returns an inline sitemap link
            return ([], [], [inline_sm_url])

        files = _run_with_mocks(
            url="https://example.com/",
            fetch_sitemap_fn=fetch_sm,
            scan_page_fn=scan_page,
        )
        assert any(inline_sm_url in c for c in fetch_calls)
        assert any(f["url"] == "https://example.com/inline/asset.pdf" for f in files)

    def test_extension_filter_applied_to_sitemap_files(self) -> None:
        """Sitemap files are subject to the same extension filter as scraped files."""
        pdf_file = _sm_fi("https://example.com/doc.pdf", ".pdf")
        mp3_file = _sm_fi("https://example.com/ep.mp3", ".mp3")

        def fetch_sm(url, visited, index_depth=0):
            return ([pdf_file, mp3_file], [])

        files = _run_with_mocks(
            url="https://example.com/",
            fetch_sitemap_fn=fetch_sm,
            scan_page_fn=lambda u: ([], [], []),
            extensions=[".pdf"],
        )
        file_urls = {f["url"] for f in files}
        assert "https://example.com/doc.pdf" in file_urls
        assert "https://example.com/ep.mp3" not in file_urls

    def test_sitemap_files_deduplicated_against_scraped_files(self) -> None:
        """A file found both via sitemap and via HTML scraping appears only once."""
        shared_url = "https://example.com/shared.pdf"
        sm_file = _sm_fi(shared_url, ".pdf")

        def fetch_sm(url, visited, index_depth=0):
            return ([sm_file], [])

        def scan_page(url):
            # The HTML scraper also finds the same file
            fi = FileInfo(
                url=shared_url,
                filename="shared.pdf",
                extension=".pdf",
                size_hint=-1,
                source_page=url,
            )
            return ([fi], [], [])

        files = _run_with_mocks(
            url="https://example.com/",
            fetch_sitemap_fn=fetch_sm,
            scan_page_fn=scan_page,
        )
        urls = [f["url"] for f in files]
        assert urls.count(shared_url) == 1


