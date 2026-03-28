# This file is part of SafeTool Downloader, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Tests for download_worker — filename utilities."""

from __future__ import annotations

from pathlib import Path

from safetool_downloader_desktop.workers.download_worker import (
    _sanitize_filename,
    _unique_path,
)


class TestSanitizeFilename:
    """Download worker filename sanitization."""

    def test_removes_slashes(self) -> None:
        result = _sanitize_filename("path/to/file.txt")
        assert "/" not in result
        assert "\\" not in result

    def test_removes_special_chars(self) -> None:
        result = _sanitize_filename('file<>:"|?*.txt')
        assert "<" not in result
        assert ">" not in result

    def test_limits_length(self) -> None:
        long_name = "x" * 300 + ".pdf"
        assert len(_sanitize_filename(long_name)) <= 200

    def test_fallback_on_empty(self) -> None:
        result = _sanitize_filename("")
        assert result == "download"

    def test_strips_dots_and_spaces(self) -> None:
        result = _sanitize_filename("  ..file.txt.  ")
        assert not result.startswith(".")
        assert not result.endswith(".")


class TestUniquePath:
    """File deduplication helper."""

    def test_returns_original_if_no_conflict(self, tmp_output: Path) -> None:
        target = tmp_output / "file.pdf"
        assert _unique_path(target) == target

    def test_appends_counter_on_conflict(self, tmp_output: Path) -> None:
        original = tmp_output / "file.pdf"
        original.touch()
        unique = _unique_path(original)
        assert unique != original
        assert unique.name == "file_1.pdf"

    def test_increments_counter(self, tmp_output: Path) -> None:
        (tmp_output / "file.pdf").touch()
        (tmp_output / "file_1.pdf").touch()
        unique = _unique_path(tmp_output / "file.pdf")
        assert unique.name == "file_2.pdf"

    def test_preserves_extension(self, tmp_output: Path) -> None:
        (tmp_output / "archive.tar.gz").touch()
        unique = _unique_path(tmp_output / "archive.tar.gz")
        assert unique.name.endswith(".gz")
