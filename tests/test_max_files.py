# This file is part of SafeTool Downloader, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Tests for the max_files scan limit feature.

Covers:
- ScannerWorker respects max_files and stops collecting after N files.
- max_files=None (unlimited) leaves full results intact.
- The limit is applied even when a single page yields more files than the limit.
- ScannerWorker.__init__ accepts max_files keyword without error.
- UrlInputWidget.get_max_download_files() returns correct values.
"""

from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

from safetool_downloader_desktop.workers.scanner_worker import (
    FileInfo,
    ScannerWorker,
)

# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_file(n: int) -> FileInfo:
    """Create a dummy FileInfo for testing."""
    return FileInfo(
        url=f"https://example.com/file{n}.mp3",
        filename=f"file{n}.mp3",
        extension=".mp3",
        size_hint=-1,
        source_page="https://example.com/",
        depth=0,
    )


def _make_page_response(n_files: int, page_links: list[str] | None = None):
    """Return (files, page_links, sitemap_links) as _scan_page would."""
    files = [_make_file(i) for i in range(n_files)]
    return files, page_links or [], []


# ── ScannerWorker.max_files — unit tests (mocked network) ─────────────────────

class TestScannerWorkerMaxFiles:
    """ScannerWorker stops collecting files when max_files is reached."""

    def _run_worker(
        self,
        scan_page_side_effect,
        max_files: int | None,
        max_pages: int = 10,
        recursive: bool = False,
        max_depth: int = 1,
    ) -> list[dict]:
        """Run the scanner synchronously using mocked _scan_page. Returns collected files."""
        collected: list[list] = [[]]

        worker = ScannerWorker(
            url="https://example.com/",
            max_files=max_files,
            max_pages=max_pages,
            delay=0.0,
            recursive=recursive,
            max_depth=max_depth,
        )

        # Capture files_found signal
        worker.files_found.connect(lambda files: collected[0].__iadd__(files))

        with patch.object(worker, "_scan_page", side_effect=scan_page_side_effect):
            with patch.object(worker, "_try_get_file_size", return_value=-1):
                worker.run()

        return collected[0]

    # ── unlimited ──────────────────────────────────────────────────────────────

    def test_unlimited_returns_all_files(self) -> None:
        """max_files=None collects all files without truncation."""
        files = self._run_worker(
            scan_page_side_effect=[_make_page_response(10)],
            max_files=None,
        )
        assert len(files) == 10

    # ── exact limit ────────────────────────────────────────────────────────────

    def test_exact_limit_single_page(self) -> None:
        """Exactly max_files files are returned when the page has more."""
        files = self._run_worker(
            scan_page_side_effect=[_make_page_response(20)],
            max_files=5,
        )
        assert len(files) == 5

    def test_limit_of_one(self) -> None:
        """max_files=1 returns exactly one file."""
        files = self._run_worker(
            scan_page_side_effect=[_make_page_response(50)],
            max_files=1,
        )
        assert len(files) == 1

    def test_limit_equals_available(self) -> None:
        """When max_files equals the number of files, all are returned."""
        files = self._run_worker(
            scan_page_side_effect=[_make_page_response(7)],
            max_files=7,
        )
        assert len(files) == 7

    def test_limit_larger_than_available(self) -> None:
        """When max_files > files on page, no truncation happens."""
        files = self._run_worker(
            scan_page_side_effect=[_make_page_response(3)],
            max_files=100,
        )
        assert len(files) == 3

    # ── multi-page BFS ─────────────────────────────────────────────────────────

    def test_stops_after_limit_across_pages(self) -> None:
        """Scanner stops after accumulating max_files across multiple pages via recursive BFS."""
        # Page 1 returns 4 files + link to page 2
        # Page 2 returns 4 files (would bring total to 8, but limit is 5)
        # Expected: 4 from page 1 + 1 from page 2 = 5 total
        page1 = ([_make_file(i) for i in range(4)], ["https://example.com/page2/"], [])
        page2 = ([_make_file(i + 10) for i in range(4)], [], [])

        files = self._run_worker(
            scan_page_side_effect=[page1, page2],
            max_files=5,
            max_pages=10,
            recursive=True,
            max_depth=2,
        )
        assert len(files) == 5

    def test_never_exceeds_limit(self) -> None:
        """Total collected files must never exceed max_files, regardless of page size."""
        for limit in (1, 3, 7, 10, 15):
            pages = [_make_page_response(20)] * 5
            files = self._run_worker(
                scan_page_side_effect=pages,
                max_files=limit,
                max_pages=10,
            )
            assert len(files) <= limit, f"limit={limit} but got {len(files)}"

    # ── constructor ────────────────────────────────────────────────────────────

    def test_max_files_none_stored(self) -> None:
        """max_files=None is stored as None."""
        w = ScannerWorker(url="https://example.com/", max_files=None)
        assert w._max_files is None

    def test_max_files_value_stored(self) -> None:
        """max_files integer is stored correctly."""
        w = ScannerWorker(url="https://example.com/", max_files=42)
        assert w._max_files == 42

    def test_default_max_files_is_none(self) -> None:
        """By default max_files is None (unlimited)."""
        w = ScannerWorker(url="https://example.com/")
        assert w._max_files is None


# ── UrlInputWidget.get_max_download_files() ────────────────────────────────────

_DISPLAY_AVAILABLE = bool(
    os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")
)

try:
    from PySide6.QtWidgets import QApplication
    _PYSIDE6_AVAILABLE = True
except ImportError:
    _PYSIDE6_AVAILABLE = False

_UI_AVAILABLE = _DISPLAY_AVAILABLE and _PYSIDE6_AVAILABLE


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


@pytest.mark.skipif(not _UI_AVAILABLE, reason="No display or PySide6 not installed")
class TestUrlInputWidgetMaxFiles:
    """UrlInputWidget.get_max_download_files() returns correct values."""

    @pytest.fixture()
    def widget(self, qapp):
        from safetool_downloader_desktop.widgets.url_input_widget import UrlInputWidget
        w = UrlInputWidget()
        return w

    def test_default_is_none(self, widget) -> None:
        """Default value (0 / ∞) should return None."""
        assert widget.get_max_download_files() is None

    def test_set_to_ten(self, widget) -> None:
        """Setting spinbox to 10 returns 10."""
        widget._max_files_spin.setValue(10)
        assert widget.get_max_download_files() == 10

    def test_set_back_to_zero_returns_none(self, widget) -> None:
        """Resetting spinbox to 0 returns None (unlimited)."""
        widget._max_files_spin.setValue(5)
        widget._max_files_spin.setValue(0)
        assert widget.get_max_download_files() is None

    def test_spinbox_disabled_during_scan(self, widget) -> None:
        """Spinbox is disabled while scanning."""
        widget.set_scanning(True)
        assert not widget._max_files_spin.isEnabled()

    def test_spinbox_enabled_after_scan(self, widget) -> None:
        """Spinbox is re-enabled after scanning stops."""
        widget.set_scanning(True)
        widget.set_scanning(False)
        assert widget._max_files_spin.isEnabled()
