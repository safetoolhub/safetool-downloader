# This file is part of SafeTool Downloader, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Download progress widget — destination selector, download/cancel buttons, per-file progress."""

from __future__ import annotations

import platform
import subprocess
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from safetool_downloader_desktop.settings import get_output_dir
from safetool_downloader_desktop.styles.design_system import DesignSystem
from safetool_downloader_desktop.styles.icons import icon_manager


def _format_size(size_bytes: int) -> str:
    if size_bytes < 0:
        return "—"
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    if size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


class _ProgressRow(QFrame):
    """A single download progress row."""

    def __init__(self, index: int, filename: str, parent=None) -> None:
        super().__init__(parent)
        self._index = index
        self.setStyleSheet(DesignSystem.get_progress_row_style("waiting"))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(DesignSystem.SPACE_12)

        # Status icon
        self._icon = QLabel()
        icon_manager.set_label_icon(
            self._icon, "progress-clock",
            color=DesignSystem.COLOR_TEXT_SECONDARY, size=16,
        )
        self._icon.setFixedWidth(20)
        layout.addWidget(self._icon)

        # Filename
        name = QLabel(filename)
        name.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f" color: {DesignSystem.COLOR_TEXT};"
            f" border: none; background: transparent;"
        )
        name.setMinimumWidth(100)
        layout.addWidget(name, 2)

        # Progress bar
        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(8)
        self._progress.setStyleSheet(DesignSystem.get_progressbar_style())
        layout.addWidget(self._progress, 3)

        # Size / status label
        self._status = QLabel("Waiting...")
        self._status.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_XS}px;"
            f" color: {DesignSystem.COLOR_TEXT_SECONDARY};"
            f" border: none; background: transparent;"
        )
        self._status.setFixedWidth(120)
        self._status.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        layout.addWidget(self._status)

    def set_progress(self, percent: int, downloaded: int) -> None:
        if percent >= 0:
            self._progress.setValue(percent)
            self._status.setText(f"{_format_size(downloaded)} ({percent}%)")
        else:
            self._progress.setRange(0, 0)  # Indeterminate
            self._status.setText(f"{_format_size(downloaded)}")
        self.setStyleSheet(DesignSystem.get_progress_row_style("downloading"))
        icon_manager.set_label_icon(
            self._icon, "download",
            color=DesignSystem.COLOR_PRIMARY, size=16,
        )

    def set_complete(self, path: str) -> None:
        self._progress.setValue(100)
        self._status.setText("Complete")
        self._status.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_XS}px;"
            f" color: {DesignSystem.COLOR_SUCCESS};"
            f" font-weight: {DesignSystem.FONT_WEIGHT_BOLD};"
            f" border: none; background: transparent;"
        )
        self.setStyleSheet(DesignSystem.get_progress_row_style("complete"))
        icon_manager.set_label_icon(
            self._icon, "check-circle",
            color=DesignSystem.COLOR_SUCCESS, size=16,
        )

    def set_error(self, message: str) -> None:
        self._progress.setValue(0)
        self._status.setText("Error")
        self._status.setToolTip(message)
        self._status.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_XS}px;"
            f" color: {DesignSystem.COLOR_DANGER};"
            f" font-weight: {DesignSystem.FONT_WEIGHT_BOLD};"
            f" border: none; background: transparent;"
        )
        self.setStyleSheet(DesignSystem.get_progress_row_style("error"))
        icon_manager.set_label_icon(
            self._icon, "alert-circle",
            color=DesignSystem.COLOR_DANGER, size=16,
        )


class DownloadProgressWidget(QWidget):
    """Widget showing download destination, buttons, and per-file progress.

    Signals:
        download_requested(str): Output directory path.
        cancel_requested(): Cancel button clicked.
    """

    download_requested = Signal(str)
    cancel_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._rows: list[_ProgressRow] = []
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(DesignSystem.SPACE_12)

        # ── Destination + buttons card ────────────────────────────────
        top_card = QFrame()
        top_card.setStyleSheet(DesignSystem.get_card_style())
        top_layout = QVBoxLayout(top_card)
        top_layout.setSpacing(DesignSystem.SPACE_12)

        # Destination row
        dest_row = QHBoxLayout()
        dest_row.setSpacing(DesignSystem.SPACE_8)

        folder_icon = QLabel()
        icon_manager.set_label_icon(
            folder_icon, "folder-download",
            color=DesignSystem.COLOR_PRIMARY, size=20,
        )
        dest_row.addWidget(folder_icon)

        dest_label = QLabel("Download to:")
        dest_label.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_BASE}px;"
            f" font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};"
            f" color: {DesignSystem.COLOR_TEXT};"
            f" border: none; background: transparent;"
        )
        dest_row.addWidget(dest_label)

        self._dir_edit = QLineEdit(get_output_dir())
        self._dir_edit.setStyleSheet(DesignSystem.get_line_edit_style())
        self._dir_edit.setReadOnly(True)
        dest_row.addWidget(self._dir_edit, 1)

        btn_browse = QPushButton("Browse")
        btn_browse.setStyleSheet(DesignSystem.get_secondary_button_style())
        btn_browse.clicked.connect(self._browse_dir)
        dest_row.addWidget(btn_browse)

        top_layout.addLayout(dest_row)

        # Buttons row
        btn_row = QHBoxLayout()

        self._overall_progress = QProgressBar()
        self._overall_progress.setRange(0, 100)
        self._overall_progress.setValue(0)
        self._overall_progress.setTextVisible(True)
        self._overall_progress.setFormat("%v / %m files")
        self._overall_progress.setFixedHeight(24)
        self._overall_progress.setStyleSheet(
            DesignSystem.get_progressbar_style()
            + f" QProgressBar {{ height: 24px; font-size: {DesignSystem.FONT_SIZE_XS}px;"
            f" color: {DesignSystem.COLOR_TEXT}; text-align: center; }}"
        )
        self._overall_progress.setVisible(False)
        btn_row.addWidget(self._overall_progress, 1)

        self._summary_label = QLabel("")
        self._summary_label.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f" color: {DesignSystem.COLOR_TEXT_SECONDARY};"
            f" border: none; background: transparent;"
        )
        btn_row.addWidget(self._summary_label)

        btn_row.addStretch()

        self._btn_open_folder = QPushButton("Open Folder")
        self._btn_open_folder.setStyleSheet(DesignSystem.get_secondary_button_style())
        icon_manager.set_button_icon(
            self._btn_open_folder, "folder-open",
            color=DesignSystem.COLOR_TEXT_SECONDARY, size=16,
        )
        self._btn_open_folder.clicked.connect(self._open_folder)
        self._btn_open_folder.setVisible(False)
        btn_row.addWidget(self._btn_open_folder)

        self._btn_cancel = QPushButton("Cancel")
        self._btn_cancel.setStyleSheet(DesignSystem.get_danger_button_style())
        icon_manager.set_button_icon(
            self._btn_cancel, "stop", color="#FFFFFF", size=16,
        )
        self._btn_cancel.clicked.connect(self.cancel_requested.emit)
        self._btn_cancel.setVisible(False)
        btn_row.addWidget(self._btn_cancel)

        self._btn_download = QPushButton("Download")
        self._btn_download.setStyleSheet(DesignSystem.get_primary_button_style())
        icon_manager.set_button_icon(
            self._btn_download, "download", color="#FFFFFF", size=18,
        )
        self._btn_download.clicked.connect(
            lambda: self.download_requested.emit(self._dir_edit.text())
        )
        btn_row.addWidget(self._btn_download)

        top_layout.addLayout(btn_row)
        layout.addWidget(top_card)

        # ── Progress rows container ───────────────────────────────────
        self._progress_container = QFrame()
        self._progress_container.setStyleSheet(DesignSystem.get_table_container_style())
        pc_layout = QVBoxLayout(self._progress_container)
        pc_layout.setContentsMargins(0, 0, 0, 0)
        pc_layout.setSpacing(0)

        self._progress_scroll = QScrollArea()
        self._progress_scroll.setWidgetResizable(True)
        self._progress_scroll.setStyleSheet(DesignSystem.get_scroll_area_style())
        self._progress_scroll.setMaximumHeight(300)

        self._progress_widget = QWidget()
        self._progress_layout = QVBoxLayout(self._progress_widget)
        self._progress_layout.setContentsMargins(0, 0, 0, 0)
        self._progress_layout.setSpacing(0)
        self._progress_layout.addStretch()

        self._progress_scroll.setWidget(self._progress_widget)
        pc_layout.addWidget(self._progress_scroll)

        self._progress_container.setVisible(False)
        layout.addWidget(self._progress_container)

    # ── Public API ────────────────────────────────────────────────────

    def setup_downloads(self, files: list[dict]) -> None:
        """Create progress rows for all files to be downloaded."""
        self._clear_rows()
        for idx, f in enumerate(files):
            row = _ProgressRow(idx, f.get("filename", "unknown"))
            self._rows.append(row)
            self._progress_layout.insertWidget(idx, row)

        self._overall_progress.setRange(0, len(files))
        self._overall_progress.setValue(0)
        self._overall_progress.setVisible(True)
        self._progress_container.setVisible(True)
        self._btn_cancel.setVisible(True)
        self._btn_download.setEnabled(False)
        self._btn_open_folder.setVisible(False)
        self._summary_label.setText("")

    def update_file_progress(self, index: int, percent: int, downloaded: int) -> None:
        if 0 <= index < len(self._rows):
            self._rows[index].set_progress(percent, downloaded)

    def set_file_complete(self, index: int, path: str) -> None:
        if 0 <= index < len(self._rows):
            self._rows[index].set_complete(path)

    def set_file_error(self, index: int, error: str) -> None:
        if 0 <= index < len(self._rows):
            self._rows[index].set_error(error)

    def update_overall(self, completed: int, total: int) -> None:
        self._overall_progress.setValue(completed)

    def set_complete(self, success: int, errors: int) -> None:
        """Called when all downloads finish."""
        self._btn_cancel.setVisible(False)
        self._btn_download.setEnabled(True)
        self._btn_open_folder.setVisible(True)

        if errors == 0:
            self._summary_label.setText(f"✓ {success} files downloaded successfully")
            self._summary_label.setStyleSheet(
                f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
                f" color: {DesignSystem.COLOR_SUCCESS};"
                f" font-weight: {DesignSystem.FONT_WEIGHT_BOLD};"
                f" border: none; background: transparent;"
            )
        else:
            self._summary_label.setText(
                f"Downloaded {success} files, {errors} errors"
            )
            self._summary_label.setStyleSheet(
                f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
                f" color: {DesignSystem.COLOR_WARNING_TEXT};"
                f" font-weight: {DesignSystem.FONT_WEIGHT_BOLD};"
                f" border: none; background: transparent;"
            )

    def set_download_enabled(self, enabled: bool) -> None:
        self._btn_download.setEnabled(enabled)

    def get_output_dir(self) -> str:
        return self._dir_edit.text()

    # ── Private ───────────────────────────────────────────────────────

    def _clear_rows(self) -> None:
        for row in self._rows:
            self._progress_layout.removeWidget(row)
            row.deleteLater()
        self._rows.clear()

    def _browse_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self, "Select Download Directory", self._dir_edit.text(),
        )
        if path:
            self._dir_edit.setText(path)

    def _open_folder(self) -> None:
        folder = self._dir_edit.text()
        if not Path(folder).is_dir():
            return
        system = platform.system()
        if system == "Linux":
            subprocess.Popen(["xdg-open", folder])
        elif system == "Darwin":
            subprocess.Popen(["open", folder])
        elif system == "Windows":
            subprocess.Popen(["explorer", folder])
