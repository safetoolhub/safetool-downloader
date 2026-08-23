# This file is part of SafeTool Downloader, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Tests for DirectoryScannerWorker — Apache/nginx directory index parsing."""

from __future__ import annotations

import pytest

from safetool_downloader_desktop.workers.directory_scanner_worker import (
    _normalise_url,
    _get_file_extension,
    _get_filename,
    _is_same_domain,
    _is_under_base_path,
    _parse_size_text,
    _sanitize_filename,
    FileInfo,
)


class TestNormaliseUrl:
    def test_strips_trailing_slash(self):
        assert _normalise_url("http://example.com/dir/") == "http://example.com/dir"

    def test_preserves_root_slash(self):
        assert _normalise_url("http://example.com/") == "http://example.com/"

    def test_strips_sort_params(self):
        assert _normalise_url("http://example.com/dir/?C=N;O=D") == "http://example.com/dir"
        assert _normalise_url("http://example.com/dir/?C=M;O=A") == "http://example.com/dir"
        assert _normalise_url("http://example.com/dir/?C=S;O=A") == "http://example.com/dir"

    def test_preserves_non_sort_params(self):
        result = _normalise_url("http://example.com/dir/?foo=bar")
        assert "foo=bar" in result

    def test_strips_fragment(self):
        assert _normalise_url("http://example.com/dir/#section") == "http://example.com/dir"

    def test_lowercase_host(self):
        assert _normalise_url("http://EXAMPLE.COM/dir/") == "http://example.com/dir"


class TestGetFileExtension:
    def test_simple_extension(self):
        assert _get_file_extension("http://example.com/file.pdf") == ".pdf"

    def test_compound_extension_tar_gz(self):
        assert _get_file_extension("http://example.com/file.tar.gz") == ".tar.gz"

    def test_compound_extension_tar_bz2(self):
        assert _get_file_extension("http://example.com/file.tar.bz2") == ".tar.bz2"

    def test_no_extension(self):
        assert _get_file_extension("http://example.com/file") == ""

    def test_url_encoded(self):
        assert _get_file_extension("http://example.com/my%20file.pdf") == ".pdf"

    def test_directory_url(self):
        assert _get_file_extension("http://example.com/dir/") == ""


class TestGetFilename:
    def test_simple_filename(self):
        assert _get_filename("http://example.com/dir/file.pdf") == "file.pdf"

    def test_url_encoded(self):
        assert _get_filename("http://example.com/dir/my%20file.pdf") == "my file.pdf"

    def test_directory_returns_last_segment(self):
        assert _get_filename("http://example.com/dir/subdir/") == "subdir"

    def test_root_returns_unknown(self):
        assert _get_filename("http://example.com/") == "unknown"


class TestIsSameDomain:
    def test_same_domain(self):
        assert _is_same_domain("http://example.com/a", "http://example.com/b") is True

    def test_different_domain(self):
        assert _is_same_domain("http://other.com/a", "http://example.com/b") is False

    def test_case_insensitive(self):
        assert _is_same_domain("http://EXAMPLE.COM/a", "http://example.com/b") is True


class TestIsUnderBasePath:
    def test_under_base_path(self):
        assert _is_under_base_path(
            "http://example.com/courses/ceh/module1/",
            "http://example.com/courses/ceh/"
        ) is True

    def test_not_under_base_path(self):
        assert _is_under_base_path(
            "http://example.com/other/",
            "http://example.com/courses/ceh/"
        ) is False

    def test_base_path_without_trailing_slash(self):
        assert _is_under_base_path(
            "http://example.com/courses/ceh/module1/",
            "http://example.com/courses/ceh"
        ) is True


class TestParseSizeText:
    def test_megabytes(self):
        assert _parse_size_text("  1.8M  ") == int(1.8 * 1024**2)

    def test_kilobytes(self):
        assert _parse_size_text("304K") == int(304 * 1024)

    def test_gigabytes(self):
        assert _parse_size_text("2.5G") == int(2.5 * 1024**3)

    def test_invalid_text(self):
        assert _parse_size_text("invalid") == -1

    def test_dash_returns_negative(self):
        assert _parse_size_text("  -  ") == -1

    def test_empty_string(self):
        assert _parse_size_text("") == -1

    def test_case_insensitive(self):
        assert _parse_size_text("1.8m") == int(1.8 * 1024**2)


class TestSanitizeFilename:
    def test_removes_slashes(self):
        assert "/" not in _sanitize_filename("path/to/file")
        assert "\\" not in _sanitize_filename("path\\to\\file")

    def test_removes_control_chars(self):
        result = _sanitize_filename("file\x00name")
        assert "\x00" not in result

    def test_truncates_long_names(self):
        long_name = "a" * 300
        assert len(_sanitize_filename(long_name)) <= 200

    def test_empty_becomes_unknown(self):
        assert _sanitize_filename("") == "unknown"


class TestFileInfo:
    def test_to_dict(self):
        fi = FileInfo(
            url="http://example.com/file.pdf",
            filename="file.pdf",
            extension=".pdf",
            size_hint=1024,
            source_page="http://example.com/",
            depth=0,
        )
        d = fi.to_dict()
        assert d["url"] == "http://example.com/file.pdf"
        assert d["filename"] == "file.pdf"
        assert d["extension"] == ".pdf"
        assert d["size_hint"] == 1024
        assert d["depth"] == 0
        assert "meta" not in d

    def test_to_dict_with_meta(self):
        fi = FileInfo(
            url="http://example.com/file.mp3",
            filename="file.mp3",
            extension=".mp3",
            size_hint=2048,
            source_page="http://example.com/",
            meta={"title": "Test"},
        )
        d = fi.to_dict()
        assert d["meta"] == {"title": "Test"}

    def test_filename_is_sanitized(self):
        fi = FileInfo(
            url="http://example.com/file.pdf",
            filename="path/to/file.pdf",
            extension=".pdf",
            size_hint=-1,
            source_page="http://example.com/",
        )
        assert "/" not in fi.filename
