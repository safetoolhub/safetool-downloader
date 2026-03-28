# This file is part of SafeTool Downloader, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Extended UI tests — design system, icon manager, dialogs, workers."""

from __future__ import annotations

import os
import sys

import pytest

_DISPLAY_AVAILABLE = bool(
    os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")
)

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


# ─── Design System ───────────────────────────────────────────────────

class TestDesignSystem:
    """Design system returns valid style strings."""

    def test_all_style_methods(self, qapp) -> None:
        from safetool_downloader_desktop.styles.design_system import DesignSystem

        methods = [
            ("get_stylesheet", []),
            ("get_header_style", []),
            ("get_header_title_style", []),
            ("get_header_icon_container_style", []),
            ("get_header_brand_label_style", []),
            ("get_primary_button_style", []),
            ("get_secondary_button_style", []),
            ("get_danger_button_style", []),
            ("get_icon_button_style", []),
            ("get_card_style", []),
            ("get_url_input_style", []),
            ("get_scan_button_style", []),
            ("get_table_container_style", []),
            ("get_table_header_style", []),
            ("get_table_header_cell_style", []),
            ("get_table_row_text_style", []),
            ("get_table_summary_style", []),
            ("get_progressbar_style", []),
        ]
        for method_name, args in methods:
            method = getattr(DesignSystem, method_name)
            result = method(*args)
            assert isinstance(result, str), f"{method_name} did not return str"
            assert len(result) > 0, f"{method_name} returned empty string"

    def test_filter_chip_style_active_and_inactive(self, qapp) -> None:
        from safetool_downloader_desktop.styles.design_system import DesignSystem

        active = DesignSystem.get_filter_chip_style(active=True)
        inactive = DesignSystem.get_filter_chip_style(active=False)
        assert active != inactive

    def test_table_row_style_even_odd(self, qapp) -> None:
        from safetool_downloader_desktop.styles.design_system import DesignSystem

        even = DesignSystem.get_table_row_style(even=True)
        odd = DesignSystem.get_table_row_style(even=False)
        assert isinstance(even, str)
        assert isinstance(odd, str)

    def test_progress_row_style_states(self, qapp) -> None:
        from safetool_downloader_desktop.styles.design_system import DesignSystem

        for state in ["waiting", "downloading", "complete", "error"]:
            style = DesignSystem.get_progress_row_style(state)
            assert isinstance(style, str)

    def test_color_constants_are_hex(self, qapp) -> None:
        from safetool_downloader_desktop.styles.design_system import DesignSystem

        for attr in ["COLOR_PRIMARY", "COLOR_BACKGROUND", "COLOR_SURFACE",
                     "COLOR_TEXT", "COLOR_TEXT_SECONDARY", "COLOR_BORDER"]:
            val = getattr(DesignSystem, attr)
            assert isinstance(val, str)
            assert val.startswith("#")


# ─── Icon Manager ────────────────────────────────────────────────────

class TestIconManager:
    """Icon manager provides icons for all required keys."""

    def test_icon_manager_singleton(self, qapp) -> None:
        from safetool_downloader_desktop.styles.icons import icon_manager

        assert icon_manager is not None

    def test_get_icon_returns_qicon(self, qapp) -> None:
        from PySide6.QtGui import QIcon
        from safetool_downloader_desktop.styles.icons import icon_manager

        icon = icon_manager.get_icon("download")
        assert isinstance(icon, QIcon)

    def test_known_icon_names(self, qapp) -> None:
        from safetool_downloader_desktop.styles.icons import icon_manager

        # All semantic names used in the app should be registered
        known_names = ["download", "magnify", "folder-open", "settings",
                       "information", "cancel", "check", "alert-circle",
                       "open-in-new"]
        for name in known_names:
            icon = icon_manager.get_icon(name)
            assert icon is not None, f"Icon '{name}' not found"

    def test_set_button_icon(self, qapp) -> None:
        from PySide6.QtWidgets import QPushButton
        from safetool_downloader_desktop.styles.icons import icon_manager

        btn = QPushButton("Test")
        icon_manager.set_button_icon(btn, "download")
        assert not btn.icon().isNull()


# ─── Worker Signals ──────────────────────────────────────────────────

class TestWorkerSignals:
    """Verify workers have expected signals."""

    def test_scanner_worker_signals(self, qapp) -> None:
        from safetool_downloader_desktop.workers.scanner_worker import ScannerWorker

        worker = ScannerWorker("https://example.com")
        assert hasattr(worker, "files_found")
        assert hasattr(worker, "scan_progress")
        assert hasattr(worker, "scan_detail")
        assert hasattr(worker, "page_scanned")
        assert hasattr(worker, "scan_error")
        assert hasattr(worker, "scan_finished")

    def test_scanner_worker_cancel(self, qapp) -> None:
        from safetool_downloader_desktop.workers.scanner_worker import ScannerWorker

        worker = ScannerWorker("https://example.com")
        worker.cancel()
        assert worker._cancelled is True

    def test_download_worker_signals(self, qapp) -> None:
        from safetool_downloader_desktop.workers.download_worker import DownloadWorker

        worker = DownloadWorker([], "/tmp/test")
        assert hasattr(worker, "file_progress")
        assert hasattr(worker, "file_complete")
        assert hasattr(worker, "file_error")
        assert hasattr(worker, "overall_progress")
        assert hasattr(worker, "all_complete")

    def test_download_worker_cancel(self, qapp) -> None:
        from safetool_downloader_desktop.workers.download_worker import DownloadWorker

        worker = DownloadWorker([], "/tmp/test")
        worker.cancel()
        assert worker._cancelled is True


# ─── Dialogs ─────────────────────────────────────────────────────────

class TestDialogs:
    """Dialog instantiation tests."""

    def test_about_dialog_creates(self, qapp) -> None:
        from safetool_downloader_desktop.dialogs.about_dialog import AboutDialog

        dialog = AboutDialog()
        assert dialog is not None
        dialog.close()

    def test_settings_dialog_creates(self, qapp) -> None:
        from safetool_downloader_desktop.dialogs.settings_dialog import SettingsDialog

        dialog = SettingsDialog()
        assert dialog is not None
        dialog.close()
