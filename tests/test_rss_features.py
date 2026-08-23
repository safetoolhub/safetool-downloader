# This file is part of SafeTool Downloader, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Tests for RSS/Podcast feature: helpers, file table RSS mode, URL input RSS controls."""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone

import pytest

_DISPLAY_AVAILABLE = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))

try:
    from PySide6.QtWidgets import QApplication

    _PYSIDE6_AVAILABLE = True
except ImportError:
    _PYSIDE6_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not (_DISPLAY_AVAILABLE and _PYSIDE6_AVAILABLE),
    reason="No display available or PySide6 not installed",
)


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


# ── Helper function tests (no display needed) ──────────────────────────────

class TestFormatDuration:
    def test_seconds_only(self):
        from safetool_downloader_desktop.widgets.file_preview_table import _format_duration
        assert _format_duration("90") == "1:30"

    def test_seconds_over_hour(self):
        from safetool_downloader_desktop.widgets.file_preview_table import _format_duration
        assert _format_duration("3600") == "1:00:00"

    def test_hms_passthrough(self):
        from safetool_downloader_desktop.widgets.file_preview_table import _format_duration
        assert _format_duration("1:23:45") == "1:23:45"

    def test_empty_string(self):
        from safetool_downloader_desktop.widgets.file_preview_table import _format_duration
        assert _format_duration("") == ""

    def test_invalid_returns_original(self):
        from safetool_downloader_desktop.widgets.file_preview_table import _format_duration
        assert _format_duration("not-a-duration") == "not-a-duration"

    def test_mm_ss_passthrough(self):
        from safetool_downloader_desktop.widgets.file_preview_table import _format_duration
        assert _format_duration("45:00") == "45:00"

    def test_zero_seconds(self):
        from safetool_downloader_desktop.widgets.file_preview_table import _format_duration
        assert _format_duration("0") == "0:00"


class TestParseRssDate:
    def test_rfc2822_date(self):
        from safetool_downloader_desktop.widgets.file_preview_table import _parse_rss_date
        dt = _parse_rss_date("Mon, 01 Jan 2024 12:00:00 +0000")
        assert dt is not None
        assert dt.year == 2024
        assert dt.month == 1

    def test_iso8601_date(self):
        from safetool_downloader_desktop.widgets.file_preview_table import _parse_rss_date
        dt = _parse_rss_date("2024-06-15T10:30:00+00:00")
        assert dt is not None
        assert dt.year == 2024
        assert dt.month == 6

    def test_invalid_returns_none(self):
        from safetool_downloader_desktop.widgets.file_preview_table import _parse_rss_date
        dt = _parse_rss_date("not-a-date")
        assert dt is None

    def test_empty_returns_none(self):
        from safetool_downloader_desktop.widgets.file_preview_table import _parse_rss_date
        assert _parse_rss_date("") is None


class TestFormatRssDate:
    def test_valid_rfc2822(self):
        from safetool_downloader_desktop.widgets.file_preview_table import _format_rss_date
        result = _format_rss_date("Mon, 01 Jan 2024 12:00:00 +0000")
        assert result != ""
        assert "2024" in result

    def test_invalid_returns_original(self):
        from safetool_downloader_desktop.widgets.file_preview_table import _format_rss_date
        assert _format_rss_date("garbage") == "garbage"

    def test_empty_returns_empty(self):
        from safetool_downloader_desktop.widgets.file_preview_table import _format_rss_date
        assert _format_rss_date("") == ""


# ── UI tests (require display) ─────────────────────────────────────────────

class TestFilePreviewTableRssMode:
    def test_set_rss_mode_true_shows_columns(self, qapp):
        from safetool_downloader_desktop.widgets.file_preview_table import FilePreviewTable, _COL_DATE, _COL_DURATION
        table = FilePreviewTable()
        table.show()
        table.set_rss_mode(True)
        assert not table._tree.isColumnHidden(_COL_DATE)
        assert not table._tree.isColumnHidden(_COL_DURATION)
        assert table._btn_export_csv.isVisible()

    def test_set_rss_mode_false_hides_columns(self, qapp):
        from safetool_downloader_desktop.widgets.file_preview_table import FilePreviewTable, _COL_DATE, _COL_DURATION
        table = FilePreviewTable()
        table.show()
        table.set_rss_mode(True)
        table.set_rss_mode(False)
        assert table._tree.isColumnHidden(_COL_DATE)
        assert table._tree.isColumnHidden(_COL_DURATION)
        assert not table._btn_export_csv.isVisible()

    def test_export_csv_hidden_by_default(self, qapp):
        from safetool_downloader_desktop.widgets.file_preview_table import FilePreviewTable
        table = FilePreviewTable()
        assert not table._btn_export_csv.isVisible()

    def test_filter_rss_by_date_none_shows_all(self, qapp):
        from safetool_downloader_desktop.widgets.file_preview_table import FilePreviewTable
        table = FilePreviewTable()
        table.set_files(
            [
                {"url": "http://example.com/ep1.mp3", "name": "ep1.mp3", "size_hint": 0, "ext": ".mp3",
                 "meta": {"rss_date": "Mon, 01 Jan 2024 00:00:00 +0000"}},
                {"url": "http://example.com/ep2.mp3", "name": "ep2.mp3", "size_hint": 0, "ext": ".mp3",
                 "meta": {"rss_date": "Mon, 01 Jan 2020 00:00:00 +0000"}},
            ],
            base_url="http://example.com",
        )
        table.filter_rss_by_date(None)
        visible = [
            not table._tree.topLevelItem(i).isHidden()
            for i in range(table._tree.topLevelItemCount())
        ]
        assert all(visible)

    def test_filter_rss_by_date_hides_old_items(self, qapp):
        from safetool_downloader_desktop.widgets.file_preview_table import FilePreviewTable
        table = FilePreviewTable()
        table.set_files(
            [
                {"url": "http://example.com/ep1.mp3", "name": "ep1.mp3", "size_hint": 0, "ext": ".mp3",
                 "meta": {"rss_date": "Mon, 01 Jan 2020 00:00:00 +0000"}},  # old
            ],
            base_url="http://example.com",
        )
        table.filter_rss_by_date(30)  # last 30 days — should hide 2020 episode
        item = table._tree.topLevelItem(0)
        if item:
            assert item.isHidden()

    def test_item_passes_date_filter_none_cutoff(self, qapp):
        from safetool_downloader_desktop.widgets.file_preview_table import FilePreviewTable
        fi = {"meta": {"rss_date": "Mon, 01 Jan 2020 00:00:00 +0000"}}
        assert FilePreviewTable._item_passes_date_filter(fi, None) is True

    def test_item_passes_date_filter_recent(self, qapp):
        from safetool_downloader_desktop.widgets.file_preview_table import FilePreviewTable
        recent_date = (datetime.now(tz=timezone.utc) - timedelta(days=5)).strftime(
            "%a, %d %b %Y %H:%M:%S +0000"
        )
        fi = {"meta": {"rss_date": recent_date}}
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=30)
        assert FilePreviewTable._item_passes_date_filter(fi, cutoff) is True

    def test_item_passes_date_filter_old(self, qapp):
        from safetool_downloader_desktop.widgets.file_preview_table import FilePreviewTable
        fi = {"meta": {"rss_date": "Mon, 01 Jan 2020 00:00:00 +0000"}}
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=30)
        assert FilePreviewTable._item_passes_date_filter(fi, cutoff) is False

    def test_select_n_latest(self, qapp):
        from safetool_downloader_desktop.widgets.file_preview_table import FilePreviewTable
        table = FilePreviewTable()
        table.set_files(
            [
                {"url": f"http://example.com/ep{i}.mp3", "name": f"ep{i}.mp3", "size_hint": 0,
                 "ext": ".mp3", "meta": {"rss_date": f"Mon, {i:02d} Jan 2024 00:00:00 +0000"}}
                for i in range(1, 6)
            ],
            base_url="http://example.com",
        )
        table._select_n_latest(2)
        checked = []
        for item, fi in table._file_items:
            from PySide6.QtCore import Qt
            if item.checkState(0) == Qt.CheckState.Checked:
                checked.append(fi["name"])
        assert len(checked) == 2


class TestUrlInputWidgetRssMode:
    def test_rss_controls_hidden_by_default(self, qapp):
        from safetool_downloader_desktop.widgets.url_input_widget import UrlInputWidget
        widget = UrlInputWidget()
        parent = widget._rss_date_combo.parent()
        assert not widget._rss_date_combo.isVisibleTo(parent)

    def test_set_rss_mode_true_shows_controls(self, qapp):
        from safetool_downloader_desktop.widgets.url_input_widget import UrlInputWidget
        widget = UrlInputWidget()
        widget.set_rss_mode(True)
        parent = widget._rss_date_combo.parent()
        assert widget._rss_date_combo.isVisibleTo(parent)

    def test_set_rss_mode_false_hides_controls(self, qapp):
        from safetool_downloader_desktop.widgets.url_input_widget import UrlInputWidget
        widget = UrlInputWidget()
        widget.set_rss_mode(True)
        widget.set_rss_mode(False)
        parent = widget._rss_date_combo.parent()
        assert not widget._rss_date_combo.isVisibleTo(parent)

    def test_rss_date_filter_changed_signal(self, qapp):
        from safetool_downloader_desktop.widgets.url_input_widget import UrlInputWidget
        widget = UrlInputWidget()
        received = []
        widget.rss_date_filter_changed.connect(received.append)
        # Index 0 = All (None), index 1 = 30 days
        widget._rss_date_combo.setCurrentIndex(1)
        assert len(received) == 1


class TestScannerRssDuration:
    """Test that scanner extracts rss_duration from RSS feeds."""

    def test_rss_duration_in_meta(self):
        from safetool_downloader_desktop.workers.scanner_worker import ScannerWorker

        rss_xml = """<?xml version="1.0"?>
        <rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
          <channel>
            <title>Test Podcast</title>
            <item>
              <title>Episode 1</title>
              <enclosure url="http://example.com/ep1.mp3" length="1000000" type="audio/mpeg"/>
              <itunes:duration>1:23:45</itunes:duration>
            </item>
          </channel>
        </rss>"""

        worker = ScannerWorker.__new__(ScannerWorker)
        worker._cancelled = False
        worker._rss_mode = False

        files, _, _ = worker._scan_rss_feed("http://example.com/feed.xml", rss_xml)

        assert len(files) == 1
        assert files[0].meta.get("rss_duration") == "1:23:45"

    def test_rss_duration_missing_when_not_present(self):
        from safetool_downloader_desktop.workers.scanner_worker import ScannerWorker

        rss_xml = """<?xml version="1.0"?>
        <rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
          <channel>
            <title>Test Podcast</title>
            <item>
              <title>Episode 1</title>
              <enclosure url="http://example.com/ep1.mp3" length="1000000" type="audio/mpeg"/>
            </item>
          </channel>
        </rss>"""

        worker = ScannerWorker.__new__(ScannerWorker)
        worker._cancelled = False
        worker._rss_mode = False

        files, _, _ = worker._scan_rss_feed("http://example.com/feed.xml", rss_xml)

        assert len(files) == 1
        assert not (files[0].meta or {}).get("rss_duration")
