# This file is part of SafeTool Downloader, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Tests for URL history feature (feature 4.6)."""

from __future__ import annotations

import pytest


class TestUrlHistorySettings:
    """Unit tests for URL history helper functions in settings.py."""

    def setup_method(self) -> None:
        from safetool_downloader_desktop.settings import clear_url_history
        clear_url_history()

    def teardown_method(self) -> None:
        from safetool_downloader_desktop.settings import clear_url_history
        clear_url_history()

    def test_get_url_history_empty_by_default(self) -> None:
        from safetool_downloader_desktop.settings import get_url_history
        assert get_url_history() == []

    def test_add_url_appears_in_history(self) -> None:
        from safetool_downloader_desktop.settings import add_url_to_history, get_url_history
        add_url_to_history("https://example.com")
        assert "https://example.com" in get_url_history()

    def test_most_recent_url_is_first(self) -> None:
        from safetool_downloader_desktop.settings import add_url_to_history, get_url_history
        add_url_to_history("https://first.com")
        add_url_to_history("https://second.com")
        history = get_url_history()
        assert history[0] == "https://second.com"
        assert history[1] == "https://first.com"

    def test_duplicate_url_not_stored_twice(self) -> None:
        from safetool_downloader_desktop.settings import add_url_to_history, get_url_history
        add_url_to_history("https://example.com")
        add_url_to_history("https://example.com")
        history = get_url_history()
        assert history.count("https://example.com") == 1

    def test_readding_url_moves_it_to_front(self) -> None:
        from safetool_downloader_desktop.settings import add_url_to_history, get_url_history
        add_url_to_history("https://first.com")
        add_url_to_history("https://second.com")
        add_url_to_history("https://first.com")
        history = get_url_history()
        assert history[0] == "https://first.com"
        assert len(history) == 2

    def test_history_trimmed_to_max_size(self) -> None:
        from safetool_downloader_desktop.settings import (
            add_url_to_history,
            get_url_history,
            URL_HISTORY_MAX_SIZE,
        )
        for i in range(URL_HISTORY_MAX_SIZE + 5):
            add_url_to_history(f"https://example.com/page/{i}")
        assert len(get_url_history()) == URL_HISTORY_MAX_SIZE

    def test_clear_url_history_removes_all(self) -> None:
        from safetool_downloader_desktop.settings import add_url_to_history, clear_url_history, get_url_history
        add_url_to_history("https://example.com")
        add_url_to_history("https://other.com")
        clear_url_history()
        assert get_url_history() == []

    def test_non_http_url_not_added(self) -> None:
        from safetool_downloader_desktop.settings import add_url_to_history, get_url_history
        add_url_to_history("ftp://example.com/file.zip")
        assert get_url_history() == []

    def test_empty_url_not_added(self) -> None:
        from safetool_downloader_desktop.settings import add_url_to_history, get_url_history
        add_url_to_history("")
        assert get_url_history() == []

    def test_https_url_is_accepted(self) -> None:
        from safetool_downloader_desktop.settings import add_url_to_history, get_url_history
        add_url_to_history("https://secure.example.com/feed.rss")
        assert "https://secure.example.com/feed.rss" in get_url_history()

    def test_http_url_is_accepted(self) -> None:
        from safetool_downloader_desktop.settings import add_url_to_history, get_url_history
        add_url_to_history("http://legacy.example.com/")
        assert "http://legacy.example.com/" in get_url_history()

    def test_url_history_max_size_is_positive(self) -> None:
        from safetool_downloader_desktop.settings import URL_HISTORY_MAX_SIZE
        assert URL_HISTORY_MAX_SIZE > 0

    def test_get_url_history_returns_list(self) -> None:
        from safetool_downloader_desktop.settings import get_url_history
        assert isinstance(get_url_history(), list)


# ── UI tests (require display) ────────────────────────────────────────

import os
import sys

_DISPLAY_AVAILABLE = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))

try:
    from PySide6.QtWidgets import QApplication
    _PYSIDE6_AVAILABLE = True
except ImportError:
    _PYSIDE6_AVAILABLE = False

pytestmark_ui = pytest.mark.skipif(
    not (_DISPLAY_AVAILABLE and _PYSIDE6_AVAILABLE),
    reason="No display available or PySide6 not installed",
)


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


@pytestmark_ui
class TestUrlHistoryWidget:
    """UI tests for the URL combo history in UrlInputWidget."""

    def setup_method(self) -> None:
        from safetool_downloader_desktop.settings import clear_url_history
        clear_url_history()

    def teardown_method(self) -> None:
        from safetool_downloader_desktop.settings import clear_url_history
        clear_url_history()

    def test_widget_has_url_combo(self, qapp) -> None:
        from PySide6.QtWidgets import QComboBox
        from safetool_downloader_desktop.widgets.url_input_widget import UrlInputWidget
        widget = UrlInputWidget()
        assert hasattr(widget, "_url_combo")
        assert isinstance(widget._url_combo, QComboBox)
        assert widget._url_combo.isEditable()
        widget.close()

    def test_widget_has_clear_history_button(self, qapp) -> None:
        from safetool_downloader_desktop.widgets.url_input_widget import UrlInputWidget
        widget = UrlInputWidget()
        assert hasattr(widget, "_btn_clear_history")
        widget.close()

    def test_clear_history_button_hidden_when_no_history(self, qapp) -> None:
        from safetool_downloader_desktop.widgets.url_input_widget import UrlInputWidget
        widget = UrlInputWidget()
        assert not widget._btn_clear_history.isVisible()
        widget.close()

    def test_clear_history_button_visible_after_adding_history(self, qapp) -> None:
        from safetool_downloader_desktop.settings import add_url_to_history
        from safetool_downloader_desktop.widgets.url_input_widget import UrlInputWidget
        add_url_to_history("https://example.com")
        widget = UrlInputWidget()
        # isVisibleTo checks visibility relative to the parent widget
        # (isVisible() returns False for unshown parents)
        assert widget._btn_clear_history.isVisibleTo(widget)
        widget.close()

    def test_get_url_returns_current_text(self, qapp) -> None:
        from safetool_downloader_desktop.widgets.url_input_widget import UrlInputWidget
        widget = UrlInputWidget()
        widget.set_url("https://test.example.com")
        assert widget.get_url() == "https://test.example.com"
        widget.close()

    def test_set_url_updates_combo_text(self, qapp) -> None:
        from safetool_downloader_desktop.widgets.url_input_widget import UrlInputWidget
        widget = UrlInputWidget()
        widget.set_url("https://podcast.example.com/feed")
        assert widget._url_combo.currentText() == "https://podcast.example.com/feed"
        widget.close()

    def test_history_items_loaded_on_init(self, qapp) -> None:
        from safetool_downloader_desktop.settings import add_url_to_history
        from safetool_downloader_desktop.widgets.url_input_widget import UrlInputWidget
        add_url_to_history("https://alpha.com")
        add_url_to_history("https://beta.com")
        widget = UrlInputWidget()
        combo_items = [widget._url_combo.itemText(i) for i in range(widget._url_combo.count())]
        assert "https://beta.com" in combo_items
        assert "https://alpha.com" in combo_items
        widget.close()

    def test_clear_history_button_hides_after_click(self, qapp) -> None:
        from safetool_downloader_desktop.settings import add_url_to_history
        from safetool_downloader_desktop.widgets.url_input_widget import UrlInputWidget
        add_url_to_history("https://example.com")
        widget = UrlInputWidget()
        widget._btn_clear_history.click()
        assert not widget._btn_clear_history.isVisible()
        widget.close()

    def test_clear_history_button_clears_combo_items(self, qapp) -> None:
        from safetool_downloader_desktop.settings import add_url_to_history
        from safetool_downloader_desktop.widgets.url_input_widget import UrlInputWidget
        add_url_to_history("https://example.com")
        add_url_to_history("https://other.com")
        widget = UrlInputWidget()
        widget._btn_clear_history.click()
        assert widget._url_combo.count() == 0
        widget.close()

    def test_clear_history_preserves_current_text(self, qapp) -> None:
        from safetool_downloader_desktop.settings import add_url_to_history
        from safetool_downloader_desktop.widgets.url_input_widget import UrlInputWidget
        add_url_to_history("https://example.com")
        widget = UrlInputWidget()
        widget.set_url("https://typed.example.com")
        widget._btn_clear_history.click()
        assert widget.get_url() == "https://typed.example.com"
        widget.close()
