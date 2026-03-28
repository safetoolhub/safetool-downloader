# This file is part of SafeTool Downloader, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Tests for scanner_worker — URL helpers and FileInfo."""

from __future__ import annotations

import pytest

from safetool_downloader_desktop.workers.scanner_worker import (
    ALL_EXTENSIONS,
    FILE_EXTENSIONS,
    FileInfo,
    _get_file_extension,
    _get_filename,
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
