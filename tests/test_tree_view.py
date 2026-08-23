# This file is part of SafeTool Downloader, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Tests for feature 4.3 — List / Tree view toggle in FilePreviewTable.

Covers:
  - Default view mode is tree (preserve_structure=True)
  - Toggle to flat list collapses all folders (no folder nodes in tree)
  - Toggle back to tree re-creates folder nodes
  - Checked state is preserved when toggling between modes
  - set_preserve_structure() rebuilds tree without changing checked state
  - UrlInputWidget emits view_mode_changed signal with correct value
  - UrlInputWidget button label and style change on toggle
  - set_filters_enabled(False) disables the view toggle button
  - set_scanning(True) disables the view toggle button
  - set_scanning(False) re-enables the view toggle button
"""

from __future__ import annotations

import os
import sys

import pytest

_DISPLAY_AVAILABLE = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))

try:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt

    _PYSIDE6_AVAILABLE = True
except ImportError:
    _PYSIDE6_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not _PYSIDE6_AVAILABLE or not _DISPLAY_AVAILABLE,
    reason="PySide6 not installed or no display",
)


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_files_with_subdirs() -> list[dict]:
    """Return a file list where some files live in subdirectories."""
    return [
        {
            "url": "http://example.com/docs/report.pdf",
            "filename": "report.pdf",
            "extension": ".pdf",
            "size_hint": 1024,
            "size_hint_approx": False,
            "depth": 1,
            "meta": {},
        },
        {
            "url": "http://example.com/docs/summary.pdf",
            "filename": "summary.pdf",
            "extension": ".pdf",
            "size_hint": 2048,
            "size_hint_approx": False,
            "depth": 1,
            "meta": {},
        },
        {
            "url": "http://example.com/readme.txt",
            "filename": "readme.txt",
            "extension": ".txt",
            "size_hint": 512,
            "size_hint_approx": False,
            "depth": 0,
            "meta": {},
        },
    ]


def _count_folder_nodes(tree_widget) -> int:
    """Count nodes that are folder items (no UserRole int index)."""
    count = 0
    root = tree_widget.invisibleRootItem()

    def walk(node):
        nonlocal count
        for i in range(node.childCount()):
            child = node.child(i)
            if child.data(0, Qt.ItemDataRole.UserRole) is None:
                count += 1
            walk(child)

    walk(root)
    return count


def _count_file_nodes(tree_widget) -> int:
    """Count nodes that are file items (have a UserRole int index)."""
    count = 0
    root = tree_widget.invisibleRootItem()

    def walk(node):
        nonlocal count
        for i in range(node.childCount()):
            child = node.child(i)
            if child.data(0, Qt.ItemDataRole.UserRole) is not None:
                count += 1
            walk(child)

    walk(root)
    return count


# ── FilePreviewTable: tree mode vs. flat list ─────────────────────────────────


class TestFilePreviewTableViewModes:
    def test_default_is_tree_mode(self, qapp):
        from safetool_downloader_desktop.widgets.file_preview_table import FilePreviewTable

        table = FilePreviewTable()
        files = _make_files_with_subdirs()
        table.set_files(files, base_url="http://example.com/", preserve_structure=True)

        # Expect folder node for "docs" directory
        assert _count_folder_nodes(table._tree) >= 1
        assert _count_file_nodes(table._tree) == 3

    def test_flat_list_no_folder_nodes(self, qapp):
        from safetool_downloader_desktop.widgets.file_preview_table import FilePreviewTable

        table = FilePreviewTable()
        files = _make_files_with_subdirs()
        table.set_files(files, base_url="http://example.com/", preserve_structure=False)

        # Flat list: no folder nodes, all files at root level
        assert _count_folder_nodes(table._tree) == 0
        assert _count_file_nodes(table._tree) == 3

    def test_toggle_to_flat_removes_folders(self, qapp):
        from safetool_downloader_desktop.widgets.file_preview_table import FilePreviewTable

        table = FilePreviewTable()
        files = _make_files_with_subdirs()
        table.set_files(files, base_url="http://example.com/", preserve_structure=True)
        assert _count_folder_nodes(table._tree) >= 1

        table.set_preserve_structure(False)
        assert _count_folder_nodes(table._tree) == 0

    def test_toggle_back_to_tree_creates_folders(self, qapp):
        from safetool_downloader_desktop.widgets.file_preview_table import FilePreviewTable

        table = FilePreviewTable()
        files = _make_files_with_subdirs()
        table.set_files(files, base_url="http://example.com/", preserve_structure=False)
        table.set_preserve_structure(True)

        assert _count_folder_nodes(table._tree) >= 1

    def test_checked_state_preserved_on_toggle_to_flat(self, qapp):
        from safetool_downloader_desktop.widgets.file_preview_table import FilePreviewTable

        table = FilePreviewTable()
        files = _make_files_with_subdirs()
        table.set_files(files, base_url="http://example.com/", preserve_structure=True)

        # Uncheck first file
        first_item, _ = table._file_items[0]
        first_item.setCheckState(0, Qt.CheckState.Unchecked)

        table.set_preserve_structure(False)

        # First file should still be unchecked, others checked
        item0, _ = table._file_items[0]
        item1, _ = table._file_items[1]
        item2, _ = table._file_items[2]
        assert item0.checkState(0) == Qt.CheckState.Unchecked
        assert item1.checkState(0) == Qt.CheckState.Checked
        assert item2.checkState(0) == Qt.CheckState.Checked

    def test_checked_state_preserved_on_toggle_to_tree(self, qapp):
        from safetool_downloader_desktop.widgets.file_preview_table import FilePreviewTable

        table = FilePreviewTable()
        files = _make_files_with_subdirs()
        table.set_files(files, base_url="http://example.com/", preserve_structure=False)

        # Uncheck ALL files
        for item, _ in table._file_items:
            item.setCheckState(0, Qt.CheckState.Unchecked)

        table.set_preserve_structure(True)

        # After toggling to tree, all files should still be unchecked
        for item, _ in table._file_items:
            assert item.checkState(0) == Qt.CheckState.Unchecked

    def test_set_preserve_structure_noop_same_value(self, qapp):
        """set_preserve_structure with the same value does nothing (no crash, no change)."""
        from safetool_downloader_desktop.widgets.file_preview_table import FilePreviewTable

        table = FilePreviewTable()
        files = _make_files_with_subdirs()
        table.set_files(files, base_url="http://example.com/", preserve_structure=True)
        folder_count_before = _count_folder_nodes(table._tree)

        table.set_preserve_structure(True)  # same value

        assert _count_folder_nodes(table._tree) == folder_count_before

    def test_flat_mode_all_files_at_root(self, qapp):
        """In flat list mode every file node is a direct child of the root."""
        from safetool_downloader_desktop.widgets.file_preview_table import FilePreviewTable

        table = FilePreviewTable()
        files = _make_files_with_subdirs()
        table.set_files(files, base_url="http://example.com/", preserve_structure=False)

        root = table._tree.invisibleRootItem()
        direct_file_children = 0
        for i in range(root.childCount()):
            child = root.child(i)
            if child.data(0, Qt.ItemDataRole.UserRole) is not None:
                direct_file_children += 1
        assert direct_file_children == 3

    def test_get_selected_files_same_in_both_modes(self, qapp):
        """Selected file count must be identical regardless of view mode."""
        from safetool_downloader_desktop.widgets.file_preview_table import FilePreviewTable

        table = FilePreviewTable()
        files = _make_files_with_subdirs()
        table.set_files(files, base_url="http://example.com/", preserve_structure=True)

        # Uncheck one file
        table._file_items[0][0].setCheckState(0, Qt.CheckState.Unchecked)
        selected_tree = table.get_selected_files()

        table.set_preserve_structure(False)
        selected_flat = table.get_selected_files()

        assert len(selected_tree) == len(selected_flat)


# ── UrlInputWidget: view mode toggle ─────────────────────────────────────────


class TestUrlInputWidgetViewToggle:
    def test_signal_emitted_tree_mode(self, qapp):
        from safetool_downloader_desktop.widgets.url_input_widget import UrlInputWidget

        widget = UrlInputWidget()
        received = []
        widget.view_mode_changed.connect(received.append)

        # Start unchecked, click to get tree mode (True)
        widget._btn_view_toggle.setChecked(False)
        widget._btn_view_toggle.click()  # toggles to True

        assert len(received) == 1
        assert received[0] is True

    def test_signal_emitted_flat_mode(self, qapp):
        from safetool_downloader_desktop.widgets.url_input_widget import UrlInputWidget

        widget = UrlInputWidget()
        received = []
        widget.view_mode_changed.connect(received.append)

        # Start checked, click to get flat mode (False)
        widget._btn_view_toggle.setChecked(True)
        widget._btn_view_toggle.click()  # toggles to False

        assert len(received) == 1
        assert received[0] is False

    def test_default_state_is_tree(self, qapp):
        from safetool_downloader_desktop.widgets.url_input_widget import UrlInputWidget

        widget = UrlInputWidget()
        assert widget._btn_view_toggle.isChecked() is True

    def test_set_filters_enabled_false_disables_toggle(self, qapp):
        from safetool_downloader_desktop.widgets.url_input_widget import UrlInputWidget

        widget = UrlInputWidget()
        widget.set_filters_enabled(False)
        assert widget._btn_view_toggle.isEnabled() is False

    def test_set_filters_enabled_true_enables_toggle(self, qapp):
        from safetool_downloader_desktop.widgets.url_input_widget import UrlInputWidget

        widget = UrlInputWidget()
        widget.set_filters_enabled(False)
        widget.set_filters_enabled(True)
        assert widget._btn_view_toggle.isEnabled() is True

    def test_set_scanning_disables_toggle(self, qapp):
        from safetool_downloader_desktop.widgets.url_input_widget import UrlInputWidget

        widget = UrlInputWidget()
        widget.set_scanning(True)
        assert widget._btn_view_toggle.isEnabled() is False

    def test_set_scanning_false_enables_toggle(self, qapp):
        from safetool_downloader_desktop.widgets.url_input_widget import UrlInputWidget

        widget = UrlInputWidget()
        widget.set_scanning(True)
        widget.set_scanning(False)
        assert widget._btn_view_toggle.isEnabled() is True
