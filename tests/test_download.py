# This file is part of SafeTool Downloader, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Tests for download_worker — filename utilities."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from safetool_downloader_desktop.workers.download_worker import (
    _resolve_output_path,
    _sanitize_dirname,
    _sanitize_filename,
    _unique_path,
    _write_id3_tags,
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


class TestSanitizeDirname:
    """Directory name sanitization helper."""

    def test_removes_slashes(self) -> None:
        assert "/" not in _sanitize_dirname("a/b")
        assert "\\" not in _sanitize_dirname("a\\b")

    def test_decodes_percent_encoding(self) -> None:
        result = _sanitize_dirname("CEH%20v13%20PDF")
        assert result == "CEH v13 PDF"

    def test_strips_dots_spaces(self) -> None:
        result = _sanitize_dirname("  ..dir.. ")
        assert not result.startswith(".")
        assert not result.endswith(".")

    def test_fallback_on_empty(self) -> None:
        assert _sanitize_dirname("") == "dir"

    def test_limits_length(self) -> None:
        assert len(_sanitize_dirname("x" * 200)) <= 100


class TestResolveOutputPath:
    """Destination path resolution for preserve_structure."""

    BASE = "https://example.com/Courses/CEHv13/"

    def test_flat_layout_when_disabled(self, tmp_output: Path) -> None:
        url = "https://example.com/Courses/CEHv13/Module1/file.pdf"
        result = _resolve_output_path(url, self.BASE, tmp_output, preserve_structure=False)
        assert result == tmp_output / "file.pdf"

    def test_flat_layout_no_base_url(self, tmp_output: Path) -> None:
        url = "https://example.com/Courses/CEHv13/Module1/file.pdf"
        result = _resolve_output_path(url, "", tmp_output, preserve_structure=True)
        assert result == tmp_output / "file.pdf"

    def test_preserves_single_subdir(self, tmp_output: Path) -> None:
        url = "https://example.com/Courses/CEHv13/Module1/file.pdf"
        result = _resolve_output_path(url, self.BASE, tmp_output, preserve_structure=True)
        assert result == tmp_output / "Module1" / "file.pdf"

    def test_preserves_nested_subdirs(self, tmp_output: Path) -> None:
        url = "https://example.com/Courses/CEHv13/Module2/Tools/eTracker/setup.exe"
        result = _resolve_output_path(url, self.BASE, tmp_output, preserve_structure=True)
        assert result == tmp_output / "Module2" / "Tools" / "eTracker" / "setup.exe"

    def test_file_at_base_level(self, tmp_output: Path) -> None:
        url = "https://example.com/Courses/CEHv13/readme.txt"
        result = _resolve_output_path(url, self.BASE, tmp_output, preserve_structure=True)
        assert result == tmp_output / "readme.txt"

    def test_percent_encoded_dirs_decoded(self, tmp_output: Path) -> None:
        url = "https://example.com/Courses/CEHv13/CEH%20v13%20PDF/guide.pdf"
        result = _resolve_output_path(url, self.BASE, tmp_output, preserve_structure=True)
        assert result == tmp_output / "CEH v13 PDF" / "guide.pdf"

    def test_file_outside_base_path_falls_back_flat(self, tmp_output: Path) -> None:
        url = "https://example.com/Other/file.zip"
        result = _resolve_output_path(url, self.BASE, tmp_output, preserve_structure=True)
        assert result == tmp_output / "file.zip"

    def test_base_without_trailing_slash(self, tmp_output: Path) -> None:
        base = "https://example.com/Courses/CEHv13"
        url = "https://example.com/Courses/CEHv13/Module1/file.pdf"
        result = _resolve_output_path(url, base, tmp_output, preserve_structure=True)
        assert result == tmp_output / "Module1" / "file.pdf"

    def test_subdir_created_on_disk(self, tmp_output: Path) -> None:
        url = "https://example.com/Courses/CEHv13/Module1/file.pdf"
        result = _resolve_output_path(url, self.BASE, tmp_output, preserve_structure=True)
        result.parent.mkdir(parents=True, exist_ok=True)
        assert (tmp_output / "Module1").is_dir()

    def test_filename_override_flat(self, tmp_output: Path) -> None:
        """filename_override replaces the URL-derived leaf name in flat layout."""
        url = "https://cdn.example.com/ep-123-abc.mp3"
        result = _resolve_output_path(
            url, "", tmp_output, preserve_structure=False,
            filename_override="My Great Episode.mp3",
        )
        assert result == tmp_output / "My Great Episode.mp3"

    def test_filename_override_with_structure(self, tmp_output: Path) -> None:
        """filename_override replaces only the leaf while subdirs come from the URL."""
        base = "https://example.com/podcast/"
        url = "https://example.com/podcast/season1/ep-7.mp3"
        result = _resolve_output_path(
            url, base, tmp_output, preserve_structure=True,
            filename_override="Episode 7 - The Pilot.mp3",
        )
        assert result == tmp_output / "season1" / "Episode 7 - The Pilot.mp3"

    def test_filename_override_none_falls_back_to_url(self, tmp_output: Path) -> None:
        """When filename_override is None the URL-derived name is used as before."""
        url = "https://example.com/files/report.pdf"
        result = _resolve_output_path(
            url, "", tmp_output, preserve_structure=False, filename_override=None
        )
        assert result == tmp_output / "report.pdf"


# ---------------------------------------------------------------------------
# RSS metadata extraction
# ---------------------------------------------------------------------------

_RSS_WITH_META = """\
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
  <channel>
    <title>My Test Podcast</title>
    <itunes:author>Jane Doe</itunes:author>
    <itunes:image href="https://example.com/cover.jpg" />
    <item>
      <title>Episode 1 — Intro</title>
      <pubDate>Mon, 01 Jan 2024 00:00:00 GMT</pubDate>
      <itunes:episode>1</itunes:episode>
      <itunes:season>1</itunes:season>
      <itunes:summary>A brief introduction.</itunes:summary>
      <enclosure url="https://cdn.example.com/ep1.mp3" type="audio/mpeg" length="12345678"/>
    </item>
    <item>
      <title>Episode 2 — Deep Dive</title>
      <pubDate>Mon, 08 Jan 2024 00:00:00 GMT</pubDate>
      <itunes:episode>2</itunes:episode>
      <enclosure url="https://cdn.example.com/ep2.mp3" type="audio/mpeg" length="9876543"/>
    </item>
  </channel>
</rss>
"""


class TestRssFeedMetaExtraction:
    """ScannerWorker._scan_rss_feed stores rich metadata in FileInfo.meta."""

    def _scan(self, rss_text: str):
        from safetool_downloader_desktop.workers.scanner_worker import ScannerWorker
        worker = ScannerWorker.__new__(ScannerWorker)
        worker._rss_mode = False
        worker._session = MagicMock()
        files, _, _ = worker._scan_rss_feed("https://example.com/feed.xml", rss_text)
        return files

    def test_filename_uses_episode_title(self) -> None:
        files = self._scan(_RSS_WITH_META)
        assert files[0].filename == "Episode 1 \u2014 Intro.mp3"

    def test_meta_episode_title(self) -> None:
        files = self._scan(_RSS_WITH_META)
        assert files[0].meta["rss_title"] == "Episode 1 \u2014 Intro"

    def test_meta_podcast_album(self) -> None:
        files = self._scan(_RSS_WITH_META)
        assert files[0].meta["rss_album"] == "My Test Podcast"

    def test_meta_podcast_artist(self) -> None:
        files = self._scan(_RSS_WITH_META)
        assert files[0].meta["rss_artist"] == "Jane Doe"

    def test_meta_track_with_season(self) -> None:
        files = self._scan(_RSS_WITH_META)
        assert files[0].meta["rss_track"] == "1x1"

    def test_meta_track_without_season(self) -> None:
        files = self._scan(_RSS_WITH_META)
        assert files[1].meta["rss_track"] == "2"

    def test_meta_pub_date(self) -> None:
        files = self._scan(_RSS_WITH_META)
        assert "2024" in files[0].meta["rss_date"]

    def test_meta_cover_image_url(self) -> None:
        files = self._scan(_RSS_WITH_META)
        assert files[0].meta["rss_image_url"] == "https://example.com/cover.jpg"

    def test_meta_description(self) -> None:
        files = self._scan(_RSS_WITH_META)
        assert "introduction" in files[0].meta["rss_description"]

    def test_meta_in_to_dict(self) -> None:
        files = self._scan(_RSS_WITH_META)
        d = files[0].to_dict()
        assert "meta" in d
        assert d["meta"]["rss_album"] == "My Test Podcast"

    def test_size_hint_approx_set_for_rss(self) -> None:
        """Files from RSS enclosures must have size_hint_approx=True."""
        files = self._scan(_RSS_WITH_META)
        assert files[0].size_hint_approx is True

    def test_size_hint_approx_in_to_dict(self) -> None:
        files = self._scan(_RSS_WITH_META)
        d = files[0].to_dict()
        assert d["size_hint_approx"] is True

    def test_size_hint_approx_false_when_no_length(self) -> None:
        """If <enclosure> has no length attribute, size_hint_approx must be False."""
        rss_no_length = _RSS_WITH_META.replace(
            'type="audio/mpeg" length="12345678"', 'type="audio/mpeg"'
        )
        files = self._scan(rss_no_length)
        assert files[0].size_hint_approx is False


# ---------------------------------------------------------------------------
# _write_id3_tags
# ---------------------------------------------------------------------------

def _make_silent_mp3(path: Path) -> None:
    """Create a stub .mp3 file whose ID3 tags can be read/written by mutagen.id3.ID3."""
    # _write_id3_tags uses ID3() directly (not MP3()), so any non-empty file suffices.
    path.write_bytes(b"\x00" * 64)


class TestWriteId3Tags:
    """_write_id3_tags writes ID3 metadata to MP3 files."""

    def _meta(self, **overrides) -> dict:
        base = {
            "rss_title": "Test Episode",
            "rss_album": "Test Podcast",
            "rss_artist": "Test Author",
            "rss_track": "1",
            "rss_date": "2024-01-01",
            "rss_description": "A test episode.",
            "rss_image_url": "",
        }
        base.update(overrides)
        return base

    def _file_info(self, **meta_overrides) -> dict:
        return {"url": "https://cdn.example.com/ep.mp3", "meta": self._meta(**meta_overrides)}

    def _read_tags(self, mp3: Path):
        from mutagen.id3 import ID3
        return ID3(str(mp3))

    def test_writes_title_tag(self, tmp_output: Path) -> None:
        mp3 = tmp_output / "ep.mp3"
        _make_silent_mp3(mp3)
        _write_id3_tags(mp3, self._file_info(), MagicMock())
        assert str(self._read_tags(mp3)["TIT2"]) == "Test Episode"

    def test_writes_album_tag(self, tmp_output: Path) -> None:
        mp3 = tmp_output / "ep.mp3"
        _make_silent_mp3(mp3)
        _write_id3_tags(mp3, self._file_info(), MagicMock())
        assert str(self._read_tags(mp3)["TALB"]) == "Test Podcast"

    def test_writes_artist_tag(self, tmp_output: Path) -> None:
        mp3 = tmp_output / "ep.mp3"
        _make_silent_mp3(mp3)
        _write_id3_tags(mp3, self._file_info(), MagicMock())
        assert str(self._read_tags(mp3)["TPE1"]) == "Test Author"

    def test_writes_track_tag(self, tmp_output: Path) -> None:
        mp3 = tmp_output / "ep.mp3"
        _make_silent_mp3(mp3)
        _write_id3_tags(mp3, self._file_info(rss_track="7"), MagicMock())
        assert str(self._read_tags(mp3)["TRCK"]) == "7"

    def test_skips_when_no_meta(self, tmp_output: Path) -> None:
        """No-op when file_info has no 'meta' key."""
        mp3 = tmp_output / "ep.mp3"
        _make_silent_mp3(mp3)
        before_mtime = mp3.stat().st_mtime
        _write_id3_tags(mp3, {"url": "https://example.com/ep.mp3"}, MagicMock())
        # File should be unchanged (no tags written)
        assert mp3.stat().st_mtime == before_mtime

    def test_fetches_cover_art(self, tmp_output: Path) -> None:
        mp3 = tmp_output / "ep.mp3"
        _make_silent_mp3(mp3)
        fake_img = b"\xff\xd8\xff\xe0" + b"\x00" * 100  # JPEG magic bytes
        session = MagicMock()
        img_resp = MagicMock()
        img_resp.content = fake_img
        img_resp.headers = {"Content-Type": "image/jpeg"}
        img_resp.raise_for_status = MagicMock()
        session.get.return_value = img_resp
        _write_id3_tags(
            mp3,
            self._file_info(rss_image_url="https://example.com/cover.jpg"),
            session,
        )
        assert "APIC:Cover" in self._read_tags(mp3)

    def test_cover_art_failure_does_not_raise(self, tmp_output: Path) -> None:
        """A failed cover-art fetch must never propagate as an exception."""
        mp3 = tmp_output / "ep.mp3"
        _make_silent_mp3(mp3)
        session = MagicMock()
        session.get.side_effect = Exception("Network error")
        # Should not raise
        _write_id3_tags(
            mp3,
            self._file_info(rss_image_url="https://example.com/cover.jpg"),
            session,
        )
        tags = self._read_tags(mp3)
        assert str(tags["TIT2"]) == "Test Episode"
