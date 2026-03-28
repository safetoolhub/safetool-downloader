# This file is part of SafeTool Downloader, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Smoke tests for PySide6 UI components."""

from __future__ import annotations

import os
import sys

import pytest

# Skip the entire module if no display is available or PySide6 is missing
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
    """Provide a QApplication instance for UI tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


class TestUISmoke:
    """Basic instantiation tests for UI components."""

    def test_main_window_creates(self, qapp) -> None:
        from safetool_downloader_desktop.main_window import MainWindow

        window = MainWindow()
        assert window is not None
        assert window.windowTitle() != ""
        window.close()

    def test_url_input_widget_creates(self, qapp) -> None:
        from safetool_downloader_desktop.widgets.url_input_widget import UrlInputWidget

        widget = UrlInputWidget()
        assert widget is not None
        widget.close()

    def test_file_preview_table_creates(self, qapp) -> None:
        from safetool_downloader_desktop.widgets.file_preview_table import FilePreviewTable

        table = FilePreviewTable()
        assert table is not None
        table.close()
