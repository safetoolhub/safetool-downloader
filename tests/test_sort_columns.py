# This file is part of SafeTool Downloader, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Tests for feature 4.1 — sortable columns in FilePreviewTable.

Covers:
  - _parse_duration_secs() helper (no display required)
  - _SortableTreeItem numeric comparison for size and duration columns
  - FilePreviewTable: header sorting is enabled after set_files()
  - Sort by name, type, size (numeric), date, duration (numeric)
  - Sort indicator is cleared on each new scan (set_files resets to discovery order)
  - Sorting is disabled in download mode and restored on exit_download_mode()
"""

from __future__ import annotations

import os
import sys

import pytest

_DISPLAY_AVAILABLE = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))

try:
    from PySide6.QtWidgets import QApplication

    _PYSIDE6_AVAILABLE = True
except ImportError:
    _PYSIDE6_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not _PYSIDE6_AVAILABLE,
    reason="PySide6 not installed",
)


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


# ── _parse_duration_secs (no display needed) ──────────────────────────────────

class TestParseDurationSecs:
    def test_empty_string(self):
        from safetool_downloader_desktop.widgets.file_preview_table import _parse_duration_secs
        assert _parse_duration_secs("") == -1

    def test_integer_seconds(self):
        from safetool_downloader_desktop.widgets.file_preview_table import _parse_duration_secs
        assert _parse_duration_secs("90") == 90

    def test_zero_seconds(self):
        from safetool_downloader_desktop.widgets.file_preview_table import _parse_duration_secs
        assert _parse_duration_secs("0") == 0

    def test_mm_ss(self):
        from safetool_downloader_desktop.widgets.file_preview_table import _parse_duration_secs
        assert _parse_duration_secs("1:30") == 90

    def test_hh_mm_ss(self):
        from safetool_downloader_desktop.widgets.file_preview_table import _parse_duration_secs
        assert _parse_duration_secs("1:23:45") == 5025

    def test_hh_mm_ss_zero_hours(self):
        from safetool_downloader_desktop.widgets.file_preview_table import _parse_duration_secs
        assert _parse_duration_secs("0:05:30") == 330

    def test_invalid_text(self):
        from safetool_downloader_desktop.widgets.file_preview_table import _parse_duration_secs
        assert _parse_duration_secs("not-a-duration") == -1

    def test_colon_with_invalid_parts(self):
        from safetool_downloader_desktop.widgets.file_preview_table import _parse_duration_secs
        assert _parse_duration_secs("1:xx:45") == -1

    def test_too_many_colons(self):
        from safetool_downloader_desktop.widgets.file_preview_table import _parse_duration_secs
        # 4 parts → neither 2 nor 3 → -1
        assert _parse_duration_secs("1:2:3:4") == -1


# ── Widget tests (need a QApplication, display optional for headless) ─────────

_widget_mark = pytest.mark.skipif(
    not (_DISPLAY_AVAILABLE and _PYSIDE6_AVAILABLE),
    reason="No display available or PySide6 not installed",
)


def _make_file(filename: str, ext: str, size: int, rss_date: str = "", rss_duration: str = "") -> dict:
    meta: dict = {}
    if rss_date:
        meta["rss_date"] = rss_date
    if rss_duration:
        meta["rss_duration"] = rss_duration
    return {
        "url": f"https://example.com/{filename}",
        "filename": filename,
        "extension": ext,
        "size_hint": size,
        "size_hint_approx": False,
        "meta": meta,
    }


@_widget_mark
class TestSortingEnabled:
    """FilePreviewTable exposes interactive column sorting."""

    def test_sorting_enabled_after_set_files(self, qapp):
        from safetool_downloader_desktop.widgets.file_preview_table import FilePreviewTable
        table = FilePreviewTable()
        table.set_files([_make_file("a.mp3", ".mp3", 1000)])
        assert table._tree.isSortingEnabled()

    def test_sort_indicator_reset_on_new_scan(self, qapp):
        from safetool_downloader_desktop.widgets.file_preview_table import FilePreviewTable
        from PySide6.QtCore import Qt
        table = FilePreviewTable()
        files = [_make_file("b.mp3", ".mp3", 500), _make_file("a.mp3", ".mp3", 1000)]
        table.set_files(files)
        # Simulate user sorting by name
        table._tree.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        # New scan should reset the sort indicator
        table.set_files(files)
        assert table._tree.header().sortIndicatorSection() == -1

    def test_sorting_disabled_during_download_mode(self, qapp):
        from safetool_downloader_desktop.widgets.file_preview_table import FilePreviewTable
        table = FilePreviewTable()
        table.set_files([_make_file("a.mp3", ".mp3", 1000)])
        table.start_download_mode()
        assert not table._tree.isSortingEnabled()

    def test_sorting_restored_after_exit_download_mode(self, qapp):
        from safetool_downloader_desktop.widgets.file_preview_table import FilePreviewTable
        table = FilePreviewTable()
        table.set_files([_make_file("a.mp3", ".mp3", 1000)])
        table.start_download_mode()
        table.exit_download_mode()
        assert table._tree.isSortingEnabled()


@_widget_mark
class TestSortByName:
    """Clicking the Name header sorts files alphabetically."""

    def _visible_names(self, table) -> list[str]:
        from PySide6.QtCore import Qt
        result = []
        root = table._tree.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            if item.data(0, Qt.ItemDataRole.UserRole) is not None:
                result.append(item.text(0).strip())
        return result

    def test_sort_name_ascending(self, qapp):
        from safetool_downloader_desktop.widgets.file_preview_table import FilePreviewTable
        from PySide6.QtCore import Qt
        table = FilePreviewTable()
        table.set_files([
            _make_file("zoo.mp3", ".mp3", 100),
            _make_file("alpha.mp3", ".mp3", 200),
            _make_file("middle.mp3", ".mp3", 150),
        ])
        table._tree.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        names = self._visible_names(table)
        assert names == sorted(names)

    def test_sort_name_descending(self, qapp):
        from safetool_downloader_desktop.widgets.file_preview_table import FilePreviewTable
        from PySide6.QtCore import Qt
        table = FilePreviewTable()
        table.set_files([
            _make_file("alpha.mp3", ".mp3", 100),
            _make_file("zoo.mp3", ".mp3", 200),
            _make_file("middle.mp3", ".mp3", 150),
        ])
        table._tree.sortByColumn(0, Qt.SortOrder.DescendingOrder)
        names = self._visible_names(table)
        assert names == sorted(names, reverse=True)


@_widget_mark
class TestSortByType:
    """Clicking the Type header sorts by extension string."""

    def _visible_types(self, table) -> list[str]:
        from PySide6.QtCore import Qt
        result = []
        root = table._tree.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            if item.data(0, Qt.ItemDataRole.UserRole) is not None:
                result.append(item.text(1))
        return result

    def test_sort_type_ascending(self, qapp):
        from safetool_downloader_desktop.widgets.file_preview_table import FilePreviewTable, _COL_TYPE
        from PySide6.QtCore import Qt
        table = FilePreviewTable()
        table.set_files([
            _make_file("video.mp4", ".mp4", 500),
            _make_file("audio.mp3", ".mp3", 100),
            _make_file("doc.pdf", ".pdf", 200),
        ])
        table._tree.sortByColumn(_COL_TYPE, Qt.SortOrder.AscendingOrder)
        types = self._visible_types(table)
        assert types == sorted(types)


@_widget_mark
class TestSortBySize:
    """Size column sorts by numeric byte value, not by formatted display string."""

    def _visible_sizes(self, table) -> list[int]:
        from PySide6.QtCore import Qt
        from safetool_downloader_desktop.widgets.file_preview_table import _COL_SIZE
        result = []
        root = table._tree.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            if item.data(0, Qt.ItemDataRole.UserRole) is not None:
                val = item.data(_COL_SIZE, Qt.ItemDataRole.UserRole)
                result.append(val)
        return result

    def test_sort_size_ascending_numeric(self, qapp):
        from safetool_downloader_desktop.widgets.file_preview_table import FilePreviewTable, _COL_SIZE
        from PySide6.QtCore import Qt
        table = FilePreviewTable()
        # These sizes are chosen so lexicographic order differs from numeric order:
        # "1.0 GB" < "500 MB" lexicographically, but 1 GB > 500 MB numerically
        table.set_files([
            _make_file("big.bin", ".bin", 1_073_741_824),   # 1 GB
            _make_file("small.bin", ".bin", 1_024),          # 1 KB
            _make_file("medium.bin", ".bin", 524_288_000),   # 500 MB
        ])
        table._tree.sortByColumn(_COL_SIZE, Qt.SortOrder.AscendingOrder)
        sizes = self._visible_sizes(table)
        assert sizes == sorted(sizes), "Sort should be numeric, not lexicographic"

    def test_sort_size_descending_numeric(self, qapp):
        from safetool_downloader_desktop.widgets.file_preview_table import FilePreviewTable, _COL_SIZE
        from PySide6.QtCore import Qt
        table = FilePreviewTable()
        table.set_files([
            _make_file("big.bin", ".bin", 1_073_741_824),
            _make_file("small.bin", ".bin", 1_024),
            _make_file("medium.bin", ".bin", 524_288_000),
        ])
        table._tree.sortByColumn(_COL_SIZE, Qt.SortOrder.DescendingOrder)
        sizes = self._visible_sizes(table)
        assert sizes == sorted(sizes, reverse=True)

    def test_unknown_size_sorts_consistently(self, qapp):
        from safetool_downloader_desktop.widgets.file_preview_table import FilePreviewTable, _COL_SIZE
        from PySide6.QtCore import Qt
        table = FilePreviewTable()
        table.set_files([
            _make_file("known.bin", ".bin", 5_000),
            _make_file("unknown.bin", ".bin", -1),  # unknown size
        ])
        # Should not raise; unknown (-1) sorts before any positive size
        table._tree.sortByColumn(_COL_SIZE, Qt.SortOrder.AscendingOrder)
        sizes = self._visible_sizes(table)
        assert sizes[0] == -1  # unknown goes first in ascending order


@_widget_mark
class TestSortByDate:
    """Date column (YYYY-MM-DD) sorts chronologically via text comparison."""

    def _visible_dates(self, table) -> list[str]:
        from PySide6.QtCore import Qt
        from safetool_downloader_desktop.widgets.file_preview_table import _COL_DATE
        result = []
        root = table._tree.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            if item.data(0, Qt.ItemDataRole.UserRole) is not None:
                result.append(item.text(_COL_DATE))
        return result

    def test_sort_date_ascending(self, qapp):
        from safetool_downloader_desktop.widgets.file_preview_table import FilePreviewTable, _COL_DATE
        from PySide6.QtCore import Qt
        table = FilePreviewTable()
        table.set_rss_mode(True)
        table.set_files([
            _make_file("ep3.mp3", ".mp3", 100, rss_date="Mon, 01 Mar 2024 00:00:00 +0000"),
            _make_file("ep1.mp3", ".mp3", 100, rss_date="Mon, 01 Jan 2024 00:00:00 +0000"),
            _make_file("ep2.mp3", ".mp3", 100, rss_date="Thu, 01 Feb 2024 00:00:00 +0000"),
        ])
        table._tree.sortByColumn(_COL_DATE, Qt.SortOrder.AscendingOrder)
        dates = self._visible_dates(table)
        assert dates == sorted(dates)

    def test_sort_date_descending(self, qapp):
        from safetool_downloader_desktop.widgets.file_preview_table import FilePreviewTable, _COL_DATE
        from PySide6.QtCore import Qt
        table = FilePreviewTable()
        table.set_rss_mode(True)
        table.set_files([
            _make_file("ep1.mp3", ".mp3", 100, rss_date="Mon, 01 Jan 2024 00:00:00 +0000"),
            _make_file("ep3.mp3", ".mp3", 100, rss_date="Mon, 01 Mar 2024 00:00:00 +0000"),
            _make_file("ep2.mp3", ".mp3", 100, rss_date="Thu, 01 Feb 2024 00:00:00 +0000"),
        ])
        table._tree.sortByColumn(_COL_DATE, Qt.SortOrder.DescendingOrder)
        dates = self._visible_dates(table)
        assert dates == sorted(dates, reverse=True)


@_widget_mark
class TestSortByDuration:
    """Duration column sorts by total seconds, not by formatted HH:MM:SS string."""

    def _visible_duration_secs(self, table) -> list[int]:
        from PySide6.QtCore import Qt
        from safetool_downloader_desktop.widgets.file_preview_table import _COL_DURATION
        result = []
        root = table._tree.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            if item.data(0, Qt.ItemDataRole.UserRole) is not None:
                val = item.data(_COL_DURATION, Qt.ItemDataRole.UserRole)
                result.append(val)
        return result

    def test_sort_duration_ascending_numeric(self, qapp):
        from safetool_downloader_desktop.widgets.file_preview_table import FilePreviewTable, _COL_DURATION
        from PySide6.QtCore import Qt
        table = FilePreviewTable()
        table.set_rss_mode(True)
        # "9:00" = 540 s, "1:00:00" = 3600 s, "10:00" = 600 s
        # Lexicographically: "10:00" < "9:00" < "1:00:00" — but numerically: 540 < 600 < 3600
        table.set_files([
            _make_file("ep_9min.mp3", ".mp3", 100, rss_duration="9:00"),
            _make_file("ep_1hr.mp3", ".mp3", 100, rss_duration="1:00:00"),
            _make_file("ep_10min.mp3", ".mp3", 100, rss_duration="10:00"),
        ])
        table._tree.sortByColumn(_COL_DURATION, Qt.SortOrder.AscendingOrder)
        secs = self._visible_duration_secs(table)
        assert secs == sorted(secs), "Duration sort must be numeric, not lexicographic"

    def test_sort_duration_descending_numeric(self, qapp):
        from safetool_downloader_desktop.widgets.file_preview_table import FilePreviewTable, _COL_DURATION
        from PySide6.QtCore import Qt
        table = FilePreviewTable()
        table.set_rss_mode(True)
        table.set_files([
            _make_file("ep_9min.mp3", ".mp3", 100, rss_duration="9:00"),
            _make_file("ep_1hr.mp3", ".mp3", 100, rss_duration="1:00:00"),
            _make_file("ep_10min.mp3", ".mp3", 100, rss_duration="10:00"),
        ])
        table._tree.sortByColumn(_COL_DURATION, Qt.SortOrder.DescendingOrder)
        secs = self._visible_duration_secs(table)
        assert secs == sorted(secs, reverse=True)
