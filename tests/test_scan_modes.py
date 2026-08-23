# This file is part of SafeTool Downloader, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Tests for the 3 scan modes: Web, RSS, and Direct."""

from __future__ import annotations

import sys
import pytest

from PySide6.QtWidgets import QApplication

from safetool_downloader_desktop.widgets.url_input_widget import UrlInputWidget


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


class TestUrlInputModes:
    """Test that the mode radio buttons and scan button exist."""

    def test_mode_group_exists(self, qapp):
        widget = UrlInputWidget()
        assert hasattr(widget, "_mode_group")
        assert widget._mode_group is not None

    def test_radio_web_exists(self, qapp):
        widget = UrlInputWidget()
        assert hasattr(widget, "_radio_web")
        assert widget._radio_web is not None

    def test_radio_rss_exists(self, qapp):
        widget = UrlInputWidget()
        assert hasattr(widget, "_radio_rss")
        assert widget._radio_rss is not None

    def test_radio_direct_exists(self, qapp):
        widget = UrlInputWidget()
        assert hasattr(widget, "_radio_direct")
        assert widget._radio_direct is not None

    def test_scan_button_exists(self, qapp):
        widget = UrlInputWidget()
        assert hasattr(widget, "_btn_scan")
        assert widget._btn_scan is not None

    def test_web_options_exists(self, qapp):
        widget = UrlInputWidget()
        assert hasattr(widget, "_web_options")
        assert widget._web_options is not None

    def test_direct_options_exists(self, qapp):
        widget = UrlInputWidget()
        assert hasattr(widget, "_direct_options")
        assert widget._direct_options is not None

    def test_auto_download_checkbox_exists(self, qapp):
        widget = UrlInputWidget()
        assert hasattr(widget, "_auto_download_check")
        assert widget._auto_download_check is not None

    def test_delay_spin_exists(self, qapp):
        widget = UrlInputWidget()
        assert hasattr(widget, "_delay_spin")
        assert widget._delay_spin is not None

    def test_delay_spin_range(self, qapp):
        widget = UrlInputWidget()
        assert widget._delay_spin.minimum() == 0.0
        assert widget._delay_spin.maximum() == 5.0

    def test_web_checked_by_default(self, qapp):
        widget = UrlInputWidget()
        assert widget._radio_web.isChecked() is True
        assert widget._radio_rss.isChecked() is False
        assert widget._radio_direct.isChecked() is False


class TestModeVisibility:
    """Test that _on_mode_changed correctly shows/hides options."""

    def test_web_mode_shows_web_options(self, qapp):
        widget = UrlInputWidget()
        widget.show()
        widget._radio_web.setChecked(True)
        assert widget._web_options.isVisible() is True
        assert widget._direct_options.isVisible() is False
        widget.close()

    def test_rss_mode_hides_all_options(self, qapp):
        widget = UrlInputWidget()
        widget.show()
        widget._radio_rss.setChecked(True)
        assert widget._web_options.isVisible() is False
        assert widget._direct_options.isVisible() is False
        widget.close()

    def test_direct_mode_shows_direct_options(self, qapp):
        widget = UrlInputWidget()
        widget.show()
        widget._radio_direct.setChecked(True)
        assert widget._web_options.isVisible() is False
        assert widget._direct_options.isVisible() is True
        widget.close()


class TestSignals:
    """Test that scan signals are correctly emitted based on mode."""

    def test_web_scan_signal_exists(self, qapp):
        widget = UrlInputWidget()
        assert hasattr(widget, "scan_requested")

    def test_rss_scan_signal_exists(self, qapp):
        widget = UrlInputWidget()
        assert hasattr(widget, "rss_scan_requested")

    def test_direct_scan_signal_exists(self, qapp):
        widget = UrlInputWidget()
        assert hasattr(widget, "direct_scan_requested")

    def test_web_scan_emits_with_delay(self, qapp):
        widget = UrlInputWidget()
        widget._url_combo.setCurrentText("http://example.com")
        widget._rec_check.setChecked(False)
        widget._delay_spin.setValue(1.5)
        widget._radio_web.setChecked(True)

        received = []
        widget.scan_requested.connect(lambda *args: received.append(args))
        widget._on_scan_clicked()

        assert len(received) == 1
        args = received[0]
        assert args[0] == "http://example.com"
        assert args[-1] == 1.5  # delay is last arg

    def test_rss_scan_emits_url(self, qapp):
        widget = UrlInputWidget()
        widget._url_combo.setCurrentText("http://example.com/feed.xml")
        widget._radio_rss.setChecked(True)

        received = []
        widget.rss_scan_requested.connect(lambda url: received.append(url))
        widget._on_scan_clicked()

        assert len(received) == 1
        assert received[0] == "http://example.com/feed.xml"

    def test_direct_scan_emits_url_and_auto_download(self, qapp):
        widget = UrlInputWidget()
        widget._url_combo.setCurrentText("http://example.com/files/")
        widget._auto_download_check.setChecked(True)
        widget._radio_direct.setChecked(True)

        received = []
        widget.direct_scan_requested.connect(lambda url, auto: received.append((url, auto)))
        widget._on_scan_clicked()

        assert len(received) == 1
        assert received[0] == ("http://example.com/files/", True)

    def test_direct_scan_emits_false_when_auto_unchecked(self, qapp):
        widget = UrlInputWidget()
        widget._url_combo.setCurrentText("http://example.com/files/")
        widget._auto_download_check.setChecked(False)
        widget._radio_direct.setChecked(True)

        received = []
        widget.direct_scan_requested.connect(lambda url, auto: received.append((url, auto)))
        widget._on_scan_clicked()

        assert len(received) == 1
        assert received[0] == ("http://example.com/files/", False)


class TestSetScanning:
    """Test that set_scanning correctly disables/enables controls."""

    def test_scanning_disables_controls(self, qapp):
        widget = UrlInputWidget()
        widget.set_scanning(True)
        assert widget._mode_group.isEnabled() is False
        assert widget._url_combo.isEnabled() is False

    def test_scanning_changes_button_to_cancel(self, qapp):
        widget = UrlInputWidget()
        widget.set_scanning(True)
        assert widget._btn_scan.text() == "Cancelar"

    def test_not_scanning_enables_controls(self, qapp):
        widget = UrlInputWidget()
        widget.set_scanning(True)
        widget.set_scanning(False)
        assert widget._mode_group.isEnabled() is True
        assert widget._btn_scan.isEnabled() is True
        assert widget._url_combo.isEnabled() is True
