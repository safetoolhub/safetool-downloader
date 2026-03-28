# This file is part of SafeTool Downloader, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""File preview table — shows found files with checkboxes, paths, and download progress."""

from __future__ import annotations

from urllib.parse import urlparse, unquote

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from safetool_downloader_desktop.styles.design_system import DesignSystem
from safetool_downloader_desktop.styles.icons import icon_manager

# Map extensions to icon names
_EXT_ICON_MAP: dict[str, str] = {
    ".pdf": "file-pdf",
    ".jpg": "file-image", ".jpeg": "file-image", ".png": "file-image",
    ".gif": "file-image", ".webp": "file-image", ".svg": "file-image",
    ".bmp": "file-image", ".ico": "file-image", ".tiff": "file-image",
    ".mp3": "file-music", ".wav": "file-music", ".flac": "file-music",
    ".ogg": "file-music", ".aac": "file-music", ".wma": "file-music",
    ".m4a": "file-music",
    ".mp4": "file-video", ".avi": "file-video", ".mkv": "file-video",
    ".webm": "file-video", ".mov": "file-video", ".wmv": "file-video",
    ".flv": "file-video", ".m4v": "file-video",
    ".doc": "file-document", ".docx": "file-document",
    ".xls": "file-document", ".xlsx": "file-document",
    ".ppt": "file-document", ".pptx": "file-document",
    ".odt": "file-document", ".ods": "file-document",
    ".odp": "file-document", ".rtf": "file-document",
    ".txt": "file-document", ".csv": "file-document",
    ".zip": "file-archive", ".rar": "file-archive", ".7z": "file-archive",
    ".tar": "file-archive", ".gz": "file-archive", ".bz2": "file-archive",
    ".xz": "file-archive", ".tar.gz": "file-archive", ".tar.bz2": "file-archive",
    ".py": "file-code", ".js": "file-code", ".html": "file-code",
    ".css": "file-code", ".json": "file-code", ".xml": "file-code",
    ".yaml": "file-code", ".yml": "file-code", ".sh": "file-code",
    ".bat": "file-code",
}


def _format_size(size_bytes: int) -> str:
    """Format byte size to human-readable string."""
    if size_bytes < 0:
        return "—"
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    if size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def _extract_path_info(url: str, base_url: str) -> str:
    """Extract the directory path from a URL, relative to base."""
    parsed = urlparse(url)
    path = unquote(parsed.path)
    # Get directory only (remove filename)
    parts = path.rsplit("/", 1)
    directory = parts[0] if len(parts) > 1 else "/"
    return directory or "/"


class _FileRow(QFrame):
    """A single row in the file preview table — supports both preview and download modes."""

    toggled = Signal(int, bool)

    def __init__(self, index: int, file_info: dict, even: bool, base_url: str = "", parent=None) -> None:
        super().__init__(parent)
        self._index = index
        self._file_info = file_info
        self._checked = True
        self._filtered_in = True
        self.setStyleSheet(DesignSystem.get_table_row_style(even=even))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(DesignSystem.SPACE_8)

        # Checkbox
        self._checkbox = QCheckBox()
        self._checkbox.setChecked(True)
        self._checkbox.setStyleSheet(DesignSystem.get_checkbox_style())
        self._checkbox.toggled.connect(self._on_toggled)
        layout.addWidget(self._checkbox)

        # Status icon (used in download mode)
        self._status_icon = QLabel()
        ext = file_info.get("extension", "")
        icon_name = _EXT_ICON_MAP.get(ext, "file-unknown")
        icon_manager.set_label_icon(
            self._status_icon, icon_name, color=DesignSystem.COLOR_PRIMARY, size=18
        )
        self._status_icon.setFixedSize(28, 28)
        self._status_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._status_icon)

        # Filename + path column
        name_path_widget = QWidget()
        name_path_layout = QVBoxLayout(name_path_widget)
        name_path_layout.setContentsMargins(0, 0, 0, 0)
        name_path_layout.setSpacing(0)

        name_label = QLabel(file_info.get("filename", "unknown"))
        name_label.setStyleSheet(DesignSystem.get_table_row_text_style())
        name_label.setToolTip(file_info.get("url", ""))
        name_path_layout.addWidget(name_label)

        # Show full URL path
        url_path = _extract_path_info(
            file_info.get("url", ""), base_url
        )
        depth = file_info.get("depth", 0)
        depth_str = f"  [depth {depth}]" if depth > 0 else ""
        path_label = QLabel(f"{url_path}{depth_str}")
        path_label.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_XS}px;"
            f" color: {DesignSystem.COLOR_TEXT_SECONDARY};"
            f" border: none; background: transparent;"
        )
        path_label.setToolTip(file_info.get("source_page", ""))
        name_path_layout.addWidget(path_label)

        layout.addWidget(name_path_widget, 3)

        # Extension badge
        ext_label = QLabel(ext.upper().lstrip(".") if ext else "?")
        ext_label.setStyleSheet(
            f"QLabel {{ background-color: {DesignSystem.COLOR_SECONDARY_LIGHT};"
            f" color: {DesignSystem.COLOR_TEXT_SECONDARY};"
            f" border: none; border-radius: 4px; padding: 2px 8px;"
            f" font-size: {DesignSystem.FONT_SIZE_XS}px;"
            f" font-weight: {DesignSystem.FONT_WEIGHT_BOLD}; }}"
        )
        ext_label.setFixedWidth(50)
        ext_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(ext_label)

        # Size
        size_text = _format_size(file_info.get("size_hint", -1))
        self._size_label = QLabel(size_text)
        self._size_label.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f" color: {DesignSystem.COLOR_TEXT_SECONDARY};"
            f" font-family: {DesignSystem.FONT_FAMILY_MONO};"
            f" border: none; background: transparent;"
        )
        self._size_label.setFixedWidth(80)
        self._size_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        layout.addWidget(self._size_label)

        # Progress bar (hidden until download starts)
        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(8)
        self._progress.setFixedWidth(120)
        self._progress.setStyleSheet(DesignSystem.get_progressbar_style())
        self._progress.setVisible(False)
        layout.addWidget(self._progress)

        # Download status label (hidden until download starts)
        self._dl_status = QLabel("")
        self._dl_status.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_XS}px;"
            f" color: {DesignSystem.COLOR_TEXT_SECONDARY};"
            f" border: none; background: transparent;"
        )
        self._dl_status.setFixedWidth(100)
        self._dl_status.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self._dl_status.setVisible(False)
        layout.addWidget(self._dl_status)

    def _on_toggled(self, checked: bool) -> None:
        self._checked = checked
        self.toggled.emit(self._index, checked)

    def is_checked(self) -> bool:
        return self._checked

    def set_checked(self, checked: bool) -> None:
        self._checked = checked
        self._checkbox.setChecked(checked)

    def file_info(self) -> dict:
        return self._file_info

    def is_filtered_in(self) -> bool:
        return self._filtered_in

    def set_filtered(self, visible: bool) -> None:
        self._filtered_in = visible
        self.setVisible(visible)

    # ── Download mode ─────────────────────────────────────────────────

    def enter_download_mode(self) -> None:
        """Switch row to show download progress."""
        self._checkbox.setVisible(False)
        self._progress.setVisible(True)
        self._dl_status.setVisible(True)
        self._dl_status.setText("Waiting...")
        self._size_label.setVisible(False)

    def set_progress(self, percent: int, downloaded: int) -> None:
        if percent >= 0:
            self._progress.setValue(percent)
            self._dl_status.setText(f"{_format_size(downloaded)} ({percent}%)")
        else:
            self._progress.setRange(0, 0)
            self._dl_status.setText(f"{_format_size(downloaded)}")
        self.setStyleSheet(DesignSystem.get_progress_row_style("downloading"))
        icon_manager.set_label_icon(
            self._status_icon, "download",
            color=DesignSystem.COLOR_PRIMARY, size=18,
        )

    def set_complete(self, path: str) -> None:
        self._progress.setRange(0, 100)
        self._progress.setValue(100)
        self._dl_status.setText("Complete")
        self._dl_status.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_XS}px;"
            f" color: {DesignSystem.COLOR_SUCCESS};"
            f" font-weight: {DesignSystem.FONT_WEIGHT_BOLD};"
            f" border: none; background: transparent;"
        )
        self.setStyleSheet(DesignSystem.get_progress_row_style("complete"))
        icon_manager.set_label_icon(
            self._status_icon, "check-circle",
            color=DesignSystem.COLOR_SUCCESS, size=18,
        )

    def set_error(self, message: str) -> None:
        self._progress.setValue(0)
        self._dl_status.setText("Error")
        self._dl_status.setToolTip(message)
        self._dl_status.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_XS}px;"
            f" color: {DesignSystem.COLOR_DANGER};"
            f" font-weight: {DesignSystem.FONT_WEIGHT_BOLD};"
            f" border: none; background: transparent;"
        )
        self.setStyleSheet(DesignSystem.get_progress_row_style("error"))
        icon_manager.set_label_icon(
            self._status_icon, "alert-circle",
            color=DesignSystem.COLOR_DANGER, size=18,
        )

    def exit_download_mode(self) -> None:
        """Restore row to preview mode."""
        self._checkbox.setVisible(True)
        self._progress.setVisible(False)
        self._dl_status.setVisible(False)
        self._size_label.setVisible(True)
        # Restore original icon
        ext = self._file_info.get("extension", "")
        icon_name = _EXT_ICON_MAP.get(ext, "file-unknown")
        icon_manager.set_label_icon(
            self._status_icon, icon_name, color=DesignSystem.COLOR_PRIMARY, size=18
        )


class FilePreviewTable(QWidget):
    """Table displaying found files with selection controls and download progress.

    Signals:
        selection_changed(list): List of selected file info dicts.
    """

    selection_changed = Signal(list)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._rows: list[_FileRow] = []
        self._all_files: list[dict] = []
        self._download_mode = False
        self._selected_indices: list[int] = []
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Container card
        self._container = QFrame()
        self._container.setStyleSheet(DesignSystem.get_table_container_style())
        container_layout = QVBoxLayout(self._container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        # ── Table header ──────────────────────────────────────────────
        header = QFrame()
        header.setStyleSheet(DesignSystem.get_table_header_style())
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 10, 12, 10)
        header_layout.setSpacing(DesignSystem.SPACE_8)

        # Select all checkbox
        self._select_all_cb = QCheckBox()
        self._select_all_cb.setChecked(True)
        self._select_all_cb.setStyleSheet(DesignSystem.get_checkbox_style())
        self._select_all_cb.toggled.connect(self._on_select_all)
        header_layout.addWidget(self._select_all_cb)

        # Spacer for icon column
        spacer = QWidget()
        spacer.setFixedWidth(28)
        header_layout.addWidget(spacer)

        for text, stretch, width in [
            ("File / Path", 3, 0),
            ("Type", 0, 50),
            ("Size", 0, 80),
        ]:
            lbl = QLabel(text)
            lbl.setStyleSheet(DesignSystem.get_table_header_cell_style())
            if width:
                lbl.setFixedWidth(width)
                if text == "Size":
                    lbl.setAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )
            if stretch:
                header_layout.addWidget(lbl, stretch)
            else:
                header_layout.addWidget(lbl)

        container_layout.addWidget(header)

        # ── Scrollable file rows ──────────────────────────────────────
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet(DesignSystem.get_scroll_area_style())

        self._rows_widget = QWidget()
        self._rows_layout = QVBoxLayout(self._rows_widget)
        self._rows_layout.setContentsMargins(0, 0, 0, 0)
        self._rows_layout.setSpacing(0)
        self._rows_layout.addStretch()

        self._scroll.setWidget(self._rows_widget)
        container_layout.addWidget(self._scroll, 1)

        # ── Summary bar ───────────────────────────────────────────────
        self._summary = QFrame()
        self._summary.setStyleSheet(DesignSystem.get_table_summary_style())
        summary_layout = QHBoxLayout(self._summary)
        summary_layout.setContentsMargins(16, 10, 16, 10)
        summary_layout.setSpacing(DesignSystem.SPACE_12)

        self._summary_label = QLabel("No files found")
        self._summary_label.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f" font-weight: {DesignSystem.FONT_WEIGHT_BOLD};"
            f" color: {DesignSystem.COLOR_TEXT};"
            f" border: none; background: transparent;"
        )
        summary_layout.addWidget(self._summary_label)
        summary_layout.addStretch()

        # Action buttons
        btn_all = QPushButton("Select All")
        btn_all.setStyleSheet(DesignSystem.get_secondary_button_style())
        btn_all.clicked.connect(lambda: self._set_all_checked(True))
        summary_layout.addWidget(btn_all)

        btn_none = QPushButton("Deselect All")
        btn_none.setStyleSheet(DesignSystem.get_secondary_button_style())
        btn_none.clicked.connect(lambda: self._set_all_checked(False))
        summary_layout.addWidget(btn_none)

        btn_invert = QPushButton("Invert")
        btn_invert.setStyleSheet(DesignSystem.get_secondary_button_style())
        btn_invert.clicked.connect(self._invert_selection)
        summary_layout.addWidget(btn_invert)

        container_layout.addWidget(self._summary)

        layout.addWidget(self._container)

    # ── Public API ────────────────────────────────────────────────────

    def set_files(self, files: list[dict]) -> None:
        """Populate the table with found files."""
        self._all_files = files
        self._download_mode = False
        self._clear_rows()

        # Determine base URL from first file
        base_url = ""
        if files:
            first_url = files[0].get("source_page", files[0].get("url", ""))
            parsed = urlparse(first_url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"

        for idx, file_info in enumerate(files):
            row = _FileRow(idx, file_info, even=(idx % 2 == 0), base_url=base_url)
            row.toggled.connect(self._on_row_toggled)
            self._rows.append(row)
            self._rows_layout.insertWidget(idx, row)

        self._update_summary()

    def get_selected_files(self) -> list[dict]:
        """Return list of selected file info dicts (filtered + checked only)."""
        return [
            row.file_info()
            for row in self._rows
            if row.is_filtered_in() and row.is_checked()
        ]

    def clear(self) -> None:
        """Remove all rows."""
        self._clear_rows()
        self._all_files.clear()
        self._download_mode = False
        self._update_summary()

    def refresh_summary(self) -> None:
        """Re-compute and display the summary (call after table becomes visible)."""
        self._update_summary()

    def filter_by_extensions(self, extensions: list[str]) -> None:
        """Show/hide rows based on file extensions. Empty = show all."""
        ext_set = set(extensions) if extensions else None
        for row in self._rows:
            visible = ext_set is None or row.file_info().get("extension", "") in ext_set
            row.set_filtered(visible)
        self._update_summary()

    # ── Download mode API ─────────────────────────────────────────────

    def start_download_mode(self) -> None:
        """Switch table to download progress mode — only show selected rows."""
        self._download_mode = True
        self._selected_indices = []
        self._select_all_cb.setVisible(False)

        idx = 0
        for row in self._rows:
            if row.is_checked():
                row.enter_download_mode()
                row.setVisible(True)
                self._selected_indices.append(self._rows.index(row))
                idx += 1
            else:
                row.setVisible(False)

    def update_download_progress(self, index: int, percent: int, downloaded: int) -> None:
        """Update progress for file at download-order index."""
        if 0 <= index < len(self._selected_indices):
            row_idx = self._selected_indices[index]
            self._rows[row_idx].set_progress(percent, downloaded)

    def set_download_complete(self, index: int, path: str) -> None:
        if 0 <= index < len(self._selected_indices):
            row_idx = self._selected_indices[index]
            self._rows[row_idx].set_complete(path)

    def set_download_error(self, index: int, error: str) -> None:
        if 0 <= index < len(self._selected_indices):
            row_idx = self._selected_indices[index]
            self._rows[row_idx].set_error(error)

    # ── Private ───────────────────────────────────────────────────────

    def _clear_rows(self) -> None:
        for row in self._rows:
            self._rows_layout.removeWidget(row)
            row.deleteLater()
        self._rows.clear()
        self._selected_indices.clear()

    def _on_select_all(self, checked: bool) -> None:
        for row in self._rows:
            if row.isVisible():
                row.set_checked(checked)
        self._update_summary()

    def _set_all_checked(self, checked: bool) -> None:
        self._select_all_cb.setChecked(checked)
        for row in self._rows:
            if row.isVisible():
                row.set_checked(checked)
        self._update_summary()

    def _invert_selection(self) -> None:
        for row in self._rows:
            if row.isVisible():
                row.set_checked(not row.is_checked())
        self._update_summary()

    def _on_row_toggled(self, index: int, checked: bool) -> None:
        self._update_summary()

    def _update_summary(self) -> None:
        total = len(self._all_files)
        visible_rows = [r for r in self._rows if r.is_filtered_in()]
        selected_rows = [r for r in visible_rows if r.is_checked()]
        visible = len(visible_rows)
        sel_count = len(selected_rows)

        # Sum sizes of selected files
        total_bytes = sum(
            r.file_info().get("size_hint", -1)
            for r in selected_rows
            if r.file_info().get("size_hint", -1) > 0
        )
        size_str = f"  ({_format_size(total_bytes)})" if total_bytes > 0 else ""

        if total == 0:
            self._summary_label.setText("No files found")
        elif visible < total:
            self._summary_label.setText(
                f"{sel_count} of {visible} shown selected{size_str}  \u2014  {total} total"
            )
        else:
            self._summary_label.setText(
                f"{sel_count} of {total} files selected{size_str}"
            )

        self.selection_changed.emit(self.get_selected_files())
