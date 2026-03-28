# This file is part of SafeTool Downloader, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Main application window — header, URL input, file preview table, download progress."""

from __future__ import annotations

import platform
import shutil
import subprocess
from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from config import APP_NAME, get_full_version
from safetool_downloader_desktop.settings import (
    get_output_dir,
    get_recursive_delay,
    get_recursive_max_pages,
    load_setting,
    save_setting,
    LAST_URL,
)
from safetool_downloader_desktop.styles.design_system import DesignSystem
from safetool_downloader_desktop.styles.icons import icon_manager
from safetool_downloader_desktop.widgets.url_input_widget import UrlInputWidget
from safetool_downloader_desktop.widgets.file_preview_table import FilePreviewTable
from safetool_downloader_desktop.workers.scanner_worker import ScannerWorker
from safetool_downloader_desktop.workers.download_worker import DownloadWorker


class MainWindow(QMainWindow):
    """Single-screen main window for SafeTool Downloader."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"{APP_NAME}  v{get_full_version()}")
        self.setMinimumSize(DesignSystem.WINDOW_MIN_WIDTH, DesignSystem.WINDOW_MIN_HEIGHT)

        self._scanner: ScannerWorker | None = None
        self._downloader: DownloadWorker | None = None
        self._found_files: list[dict] = []

        self._build_ui()

        # Restore last URL
        last_url = load_setting(LAST_URL, "")
        if last_url:
            self._url_input.set_url(last_url)

    # ── UI construction ───────────────────────────────────────────────

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._create_header())

        # Content area with padding
        content = QWidget()
        content.setStyleSheet(f"background: {DesignSystem.COLOR_BACKGROUND};")
        clayout = QVBoxLayout(content)
        clayout.setContentsMargins(
            DesignSystem.SPACE_24, DesignSystem.SPACE_16,
            DesignSystem.SPACE_24, DesignSystem.SPACE_16,
        )
        clayout.setSpacing(DesignSystem.SPACE_16)

        # URL input
        self._url_input = UrlInputWidget()
        self._url_input.scan_requested.connect(self._start_scan)
        self._url_input.scan_cancel_requested.connect(self._cancel_scan)
        self._url_input.filter_changed.connect(self._on_filter_changed)
        clayout.addWidget(self._url_input)

        # File preview table (also used for download progress)
        self._file_table = FilePreviewTable()
        self._file_table.selection_changed.connect(self._on_selection_changed)
        self._file_table.setVisible(False)
        clayout.addWidget(self._file_table, 1)

        # Download controls bar (destination + buttons)
        self._download_bar = self._create_download_bar()
        self._download_bar.setVisible(False)
        clayout.addWidget(self._download_bar)

        # Spacer to push content to top when table is hidden
        self._bottom_spacer = QWidget()
        clayout.addWidget(self._bottom_spacer, 1)

        root.addWidget(content, 1)

    def _create_header(self) -> QFrame:
        """Create the branded header bar: Icon | Title + 'by safetoolhub' | settings + about."""
        card = QFrame()
        card.setObjectName("headerCard")
        card.setStyleSheet(DesignSystem.get_header_style())

        layout = QHBoxLayout(card)
        layout.setSpacing(DesignSystem.SPACE_12)
        layout.setContentsMargins(
            DesignSystem.SPACE_16, 0, DesignSystem.SPACE_16, 0
        )

        # App icon
        icon_container = QFrame()
        icon_container.setFixedSize(48, 48)
        icon_container.setStyleSheet(DesignSystem.get_header_icon_container_style())
        icon_layout = QHBoxLayout(icon_container)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        app_icon = QLabel()
        # Load application icon from assets
        icon_path = Path(__file__).parent.parent / "assets" / "icon.png"
        if icon_path.exists():
            pixmap = QPixmap(str(icon_path))
            scaled_pixmap = pixmap.scaled(
                36, 36,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            app_icon.setPixmap(scaled_pixmap)
        else:
            icon_manager.set_label_icon(
                app_icon, "download-multiple",
                color=DesignSystem.COLOR_PRIMARY, size=36,
            )
        icon_layout.addWidget(app_icon)
        layout.addWidget(icon_container)

        # Title + "by safetoolhub" on same row
        text_container = QWidget()
        text_layout = QVBoxLayout(text_container)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)

        title_row = QWidget()
        title_row_layout = QHBoxLayout(title_row)
        title_row_layout.setContentsMargins(0, 0, 0, 0)
        title_row_layout.setSpacing(DesignSystem.SPACE_12)
        title_row_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        title_label = QLabel(APP_NAME)
        title_label.setStyleSheet(DesignSystem.get_header_title_style())
        title_row_layout.addWidget(title_label)

        by_label = QLabel("by safetoolhub")
        by_label.setStyleSheet(DesignSystem.get_header_brand_label_style())
        by_label.setAlignment(Qt.AlignmentFlag.AlignBottom)
        title_row_layout.addWidget(by_label)
        title_row_layout.addStretch()

        text_layout.addWidget(title_row)
        layout.addWidget(text_container)

        # Spacer
        layout.addStretch()

        # Settings button
        btn_settings = QToolButton()
        btn_settings.setAutoRaise(True)
        btn_settings.setToolTip("Settings")
        icon_manager.set_button_icon(
            btn_settings, "cog",
            color=DesignSystem.COLOR_TEXT_SECONDARY, size=20,
        )
        btn_settings.setIconSize(QSize(20, 20))
        btn_settings.setStyleSheet(DesignSystem.get_icon_button_style())
        btn_settings.clicked.connect(self._show_settings)
        layout.addWidget(btn_settings)

        # About button
        btn_about = QToolButton()
        btn_about.setAutoRaise(True)
        btn_about.setToolTip("About")
        icon_manager.set_button_icon(
            btn_about, "information",
            color=DesignSystem.COLOR_TEXT_SECONDARY, size=20,
        )
        btn_about.setIconSize(QSize(20, 20))
        btn_about.setStyleSheet(DesignSystem.get_icon_button_style())
        btn_about.clicked.connect(self._show_about)
        layout.addWidget(btn_about)

        return card

    def _create_download_bar(self) -> QFrame:
        """Create the download controls bar: destination + buttons + progress."""
        bar = QFrame()
        bar.setStyleSheet(DesignSystem.get_card_style())
        layout = QVBoxLayout(bar)
        layout.setSpacing(DesignSystem.SPACE_12)

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

        self._disk_space_label = QLabel("")
        self._disk_space_label.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_XS}px;"
            f" color: {DesignSystem.COLOR_TEXT_SECONDARY};"
            f" border: none; background: transparent;"
        )
        dest_row.addWidget(self._disk_space_label)
        self._update_disk_space()

        layout.addLayout(dest_row)

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

        self._download_summary_label = QLabel("")
        self._download_summary_label.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f" color: {DesignSystem.COLOR_TEXT_SECONDARY};"
            f" border: none; background: transparent;"
        )
        btn_row.addWidget(self._download_summary_label)

        btn_row.addStretch()

        self._btn_new_scan = QPushButton("Scan New URL")
        self._btn_new_scan.setStyleSheet(DesignSystem.get_secondary_button_style())
        icon_manager.set_button_icon(
            self._btn_new_scan, "magnify",
            color=DesignSystem.COLOR_TEXT_SECONDARY, size=16,
        )
        self._btn_new_scan.clicked.connect(self._on_new_scan)
        self._btn_new_scan.setVisible(False)
        btn_row.addWidget(self._btn_new_scan)

        self._btn_open_folder = QPushButton("Open Folder")
        self._btn_open_folder.setStyleSheet(DesignSystem.get_secondary_button_style())
        icon_manager.set_button_icon(
            self._btn_open_folder, "folder-open",
            color=DesignSystem.COLOR_TEXT_SECONDARY, size=16,
        )
        self._btn_open_folder.clicked.connect(self._open_folder)
        self._btn_open_folder.setVisible(False)
        btn_row.addWidget(self._btn_open_folder)

        self._btn_cancel_dl = QPushButton("Cancel")
        self._btn_cancel_dl.setStyleSheet(DesignSystem.get_danger_button_style())
        icon_manager.set_button_icon(
            self._btn_cancel_dl, "stop", color="#FFFFFF", size=16,
        )
        self._btn_cancel_dl.clicked.connect(self._cancel_download)
        self._btn_cancel_dl.setVisible(False)
        btn_row.addWidget(self._btn_cancel_dl)

        self._btn_download = QPushButton("Download")
        self._btn_download.setStyleSheet(DesignSystem.get_primary_button_style())
        icon_manager.set_button_icon(
            self._btn_download, "download", color="#FFFFFF", size=18,
        )
        self._btn_download.clicked.connect(self._on_download_clicked)
        btn_row.addWidget(self._btn_download)

        layout.addLayout(btn_row)
        return bar

    # ── Scan slots ────────────────────────────────────────────────────

    def _start_scan(self, url: str, extensions: list[str], recursive: bool, max_depth: int) -> None:
        self._cancel_scan()
        self._file_table.clear()
        self._file_table.setVisible(False)
        self._download_bar.setVisible(False)
        self._bottom_spacer.setVisible(True)
        self._url_input.set_scanning(True)
        self._url_input.set_status("Scanning...")

        save_setting(LAST_URL, url)

        self._scanner = ScannerWorker(
            url=url,
            extensions=extensions if extensions else None,
            recursive=recursive,
            max_depth=max_depth,
            delay=get_recursive_delay(),
            max_pages=get_recursive_max_pages(),
        )
        self._scanner.scan_progress.connect(self._url_input.set_status)
        self._scanner.scan_detail.connect(self._url_input.set_scan_detail)
        self._scanner.files_found.connect(self._on_files_found)
        self._scanner.scan_error.connect(self._on_scan_error)
        self._scanner.scan_finished.connect(self._on_scan_finished)
        self._scanner.start()

    def _cancel_scan(self) -> None:
        if self._scanner and self._scanner.isRunning():
            self._scanner.cancel()
            self._scanner.wait(3000)
        self._scanner = None

    def _on_files_found(self, files: list) -> None:
        self._found_files = [f.to_dict() if hasattr(f, "to_dict") else f for f in files]
        self._file_table.set_files(self._found_files)
        self._file_table.setVisible(True)
        self._download_bar.setVisible(True)
        self._bottom_spacer.setVisible(False)
        self._btn_download.setEnabled(len(self._found_files) > 0)
        self._url_input.show_filters(True)
        # Apply current filter state to the table
        active_ext = self._url_input.get_active_extensions()
        if active_ext:
            self._file_table.filter_by_extensions(active_ext)
        # Refresh summary now that table is visible
        self._file_table.refresh_summary()

    def _on_scan_error(self, error: str) -> None:
        self._url_input.set_status(f"Error: {error}")

    def _on_scan_finished(self) -> None:
        self._url_input.set_scanning(False)
        if self._found_files:
            self._url_input.set_status(f"{len(self._found_files)} files found")
        elif not self._url_input._status_label.text().startswith("Error"):
            self._url_input.set_status("No files found")

    # ── Selection slot ────────────────────────────────────────────────

    def _on_selection_changed(self, selected: list) -> None:
        self._btn_download.setEnabled(len(selected) > 0)

    def _on_filter_changed(self, extensions: list[str]) -> None:
        """Apply file type filter to the table."""
        self._file_table.filter_by_extensions(extensions)

    # ── Download slots ────────────────────────────────────────────────

    def _on_download_clicked(self) -> None:
        selected = self._file_table.get_selected_files()
        if not selected:
            return
        self._start_download(self._dir_edit.text())

    def _start_download(self, output_dir: str) -> None:
        selected = self._file_table.get_selected_files()
        if not selected:
            return

        self._cancel_download()

        # Switch file table to download mode
        self._file_table.start_download_mode()
        self._url_input.set_filters_enabled(False)

        # Setup overall progress
        self._overall_progress.setRange(0, len(selected))
        self._overall_progress.setValue(0)
        self._overall_progress.setVisible(True)
        self._btn_cancel_dl.setVisible(True)
        self._btn_download.setEnabled(False)
        self._btn_open_folder.setVisible(False)
        self._btn_new_scan.setVisible(False)
        self._download_summary_label.setText("")

        self._downloader = DownloadWorker(
            files=selected,
            output_dir=output_dir,
        )
        self._downloader.file_progress.connect(self._file_table.update_download_progress)
        self._downloader.file_complete.connect(self._file_table.set_download_complete)
        self._downloader.file_error.connect(self._file_table.set_download_error)
        self._downloader.overall_progress.connect(self._on_overall_progress)
        self._downloader.all_complete.connect(self._on_all_complete)
        self._downloader.start()

    def _cancel_download(self) -> None:
        if self._downloader and self._downloader.isRunning():
            self._downloader.cancel()
            self._downloader.wait(5000)
        self._downloader = None

    def _on_overall_progress(self, completed: int, total: int) -> None:
        self._overall_progress.setValue(completed)

    def _on_all_complete(self, success: int, errors: int) -> None:
        self._btn_cancel_dl.setVisible(False)
        self._btn_download.setEnabled(True)
        self._btn_open_folder.setVisible(True)
        self._btn_new_scan.setVisible(True)
        self._overall_progress.setVisible(False)
        self._url_input.set_filters_enabled(True)

        if errors == 0:
            self._download_summary_label.setText(
                f"✓ {success} files downloaded successfully"
            )
            self._download_summary_label.setStyleSheet(
                f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
                f" color: {DesignSystem.COLOR_SUCCESS};"
                f" font-weight: {DesignSystem.FONT_WEIGHT_BOLD};"
                f" border: none; background: transparent;"
            )
        else:
            self._download_summary_label.setText(
                f"Downloaded {success} files, {errors} errors"
            )
            self._download_summary_label.setStyleSheet(
                f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
                f" color: {DesignSystem.COLOR_WARNING_TEXT};"
                f" font-weight: {DesignSystem.FONT_WEIGHT_BOLD};"
                f" border: none; background: transparent;"
            )

    def _on_new_scan(self) -> None:
        """Reset UI for a new scan."""
        self._found_files.clear()
        self._file_table.clear()
        self._file_table.setVisible(False)
        self._download_bar.setVisible(False)
        self._bottom_spacer.setVisible(True)
        self._btn_new_scan.setVisible(False)
        self._btn_open_folder.setVisible(False)
        self._overall_progress.setVisible(False)
        self._download_summary_label.setText("")
        self._url_input.set_status("")
        self._url_input.show_filters(False)
        self._url_input._url_edit.setFocus()

    # ── Helpers ───────────────────────────────────────────────────────

    def _browse_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self, "Select Download Directory", self._dir_edit.text(),
        )
        if path:
            self._dir_edit.setText(path)
            self._update_disk_space()

    def _update_disk_space(self) -> None:
        """Show free disk space for the current destination directory."""
        folder = self._dir_edit.text()
        try:
            usage = shutil.disk_usage(folder)
            free = usage.free
            if free < 1024 * 1024 * 1024:
                text = f"{free / (1024 * 1024):.0f} MB free"
            else:
                text = f"{free / (1024 * 1024 * 1024):.1f} GB free"
            self._disk_space_label.setText(text)
        except OSError:
            self._disk_space_label.setText("")

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

    # ── Dialog slots ──────────────────────────────────────────────────

    def _show_settings(self) -> None:
        from safetool_downloader_desktop.dialogs.settings_dialog import SettingsDialog

        dlg = SettingsDialog(self)
        dlg.exec()

    def _show_about(self) -> None:
        from safetool_downloader_desktop.dialogs.about_dialog import AboutDialog

        dlg = AboutDialog(self)
        dlg.exec()

    # ── Cleanup ───────────────────────────────────────────────────────

    def closeEvent(self, event) -> None:
        self._cancel_scan()
        self._cancel_download()
        super().closeEvent(event)
