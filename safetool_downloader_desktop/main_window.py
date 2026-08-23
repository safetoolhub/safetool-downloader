# This file is part of SafeTool Downloader, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Main application window — header, URL input, file preview table, download progress."""

from __future__ import annotations

import logging
import platform
import shutil
import subprocess
from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
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
from safetool_downloader_desktop.i18n import tr
from safetool_downloader_desktop.settings import (
    get_duplicate_action,
    get_output_dir,
    get_recursive_delay,
    get_recursive_max_pages,
    is_preserve_structure_enabled,
    load_setting,
    save_setting,
    DUPLICATE_ACTION,
    DUPLICATE_SKIP,
    DUPLICATE_OVERWRITE,
    DUPLICATE_RENAME,
    LAST_URL,
)
from safetool_downloader_desktop.styles.design_system import DesignSystem
from safetool_downloader_desktop.styles.icons import icon_manager
from safetool_downloader_desktop.widgets.url_input_widget import UrlInputWidget
from safetool_downloader_desktop.widgets.file_preview_table import FilePreviewTable
from safetool_downloader_desktop.workers.scanner_worker import ScannerWorker
from safetool_downloader_desktop.workers.directory_scanner_worker import DirectoryScannerWorker
from safetool_downloader_desktop.workers.download_worker import DownloadWorker

logger = logging.getLogger(__name__)


def _fmt_size(size_bytes: int) -> str:
    """Human-readable byte size."""
    if size_bytes <= 0:
        return "0 B"
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    if size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


class MainWindow(QMainWindow):
    """Single-screen main window for SafeTool Downloader."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(tr("main_window.title", app_name=APP_NAME, version=get_full_version()))
        self.setMinimumSize(DesignSystem.WINDOW_MIN_WIDTH, DesignSystem.WINDOW_MIN_HEIGHT)

        self._scanner: ScannerWorker | None = None
        self._direct_scanner: DirectoryScannerWorker | None = None
        self._downloader: DownloadWorker | None = None
        self._found_files: list[dict] = []
        self._scan_url: str = ""
        self._dl_selected_files: list[dict] = []
        self._total_dl_bytes: int = 0
        self._completed_dl_bytes: int = 0
        self._is_rss_scan: bool = False
        self._tree_view_mode: bool = True
        self._direct_auto_download: bool = False
        self._current_scan_mode: str = ""

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
        content.setStyleSheet(f"QWidget {{ background: {DesignSystem.COLOR_BACKGROUND}; }}")
        clayout = QVBoxLayout(content)
        clayout.setContentsMargins(
            DesignSystem.SPACE_24, DesignSystem.SPACE_16,
            DesignSystem.SPACE_24, DesignSystem.SPACE_16,
        )
        clayout.setSpacing(DesignSystem.SPACE_16)

        # Top Control Card (URL + Destination)
        self._top_card = QFrame()
        self._top_card.setStyleSheet(DesignSystem.get_card_style())
        top_layout = QVBoxLayout(self._top_card)
        top_layout.setContentsMargins(
            DesignSystem.SPACE_16, DesignSystem.SPACE_12,
            DesignSystem.SPACE_16, DesignSystem.SPACE_12
        )
        top_layout.setSpacing(DesignSystem.SPACE_12)

        # URL input (Remove its own card styling if we put it in top_card, or let UrlInputWidget handle it)
        self._url_input = UrlInputWidget()
        self._url_input.scan_requested.connect(self._start_web_scan)
        self._url_input.scan_cancel_requested.connect(self._cancel_scan)
        self._url_input.rss_scan_requested.connect(self._start_rss_scan)
        self._url_input.direct_scan_requested.connect(self._start_direct_scan)
        self._url_input.filter_changed.connect(self._on_filter_changed)
        self._url_input.settings_requested.connect(self._show_settings)
        self._url_input.tree_analysis_requested.connect(self._show_tree_analysis)
        self._url_input.rss_date_filter_changed.connect(self._on_rss_date_filter_changed)
        self._url_input.view_mode_changed.connect(self._on_view_mode_changed)
        top_layout.addWidget(self._url_input)

        # Separator line
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFrameShadow(QFrame.Plain)
        sep.setStyleSheet(f"QFrame {{ background-color: {DesignSystem.COLOR_BORDER_LIGHT}; max-height: 1px; border: none; }}")
        top_layout.addWidget(sep)

        # Destination bar (ALWAYS visible)
        self._destination_bar = self._create_destination_bar()
        top_layout.addWidget(self._destination_bar)

        clayout.addWidget(self._top_card)

        # Filters toolbar — compact row with minimal spacing
        self._filter_row = self._url_input._filter_row
        filter_wrapper = QWidget()
        filter_wrapper_layout = QVBoxLayout(filter_wrapper)
        filter_wrapper_layout.setContentsMargins(DesignSystem.SPACE_24, 4, DesignSystem.SPACE_24, 4)
        filter_wrapper_layout.setSpacing(0)
        filter_wrapper_layout.addWidget(self._filter_row)
        clayout.addWidget(filter_wrapper)

        # File preview table (also used for download progress)
        self._file_table = FilePreviewTable()
        self._file_table.selection_changed.connect(self._on_selection_changed)
        self._file_table.setVisible(False)
        clayout.addWidget(self._file_table, 1)

        # Download controls (hidden until after scan)
        self._download_controls = self._create_download_controls()
        self._download_controls.setVisible(False)
        clayout.addWidget(self._download_controls)

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
        btn_settings.setToolTip(tr("main_window.settings_tooltip"))
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
        btn_about.setToolTip(tr("main_window.about_tooltip"))
        icon_manager.set_button_icon(
            btn_about, "information",
            color=DesignSystem.COLOR_TEXT_SECONDARY, size=20,
        )
        btn_about.setIconSize(QSize(20, 20))
        btn_about.setStyleSheet(DesignSystem.get_icon_button_style())
        btn_about.clicked.connect(self._show_about)
        layout.addWidget(btn_about)

        return card

    def _create_destination_bar(self) -> QFrame:
        """Create the destination bar (ALWAYS visible): folder + browse + disk space."""
        bar = QFrame()
        bar.setStyleSheet("QFrame { background: transparent; border: none; padding: 0px; }")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(DesignSystem.SPACE_8)

        folder_icon = QLabel()
        icon_manager.set_label_icon(
            folder_icon, "folder-download",
            color=DesignSystem.COLOR_PRIMARY, size=18,
        )
        layout.addWidget(folder_icon)

        dest_label = QLabel(tr("main_window.download_to"))
        dest_label.setStyleSheet(
            f"QLabel {{"
            f"  font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f"  font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};"
            f"  color: {DesignSystem.COLOR_TEXT_SECONDARY};"
            f"  border: none; background: transparent;"
            f"}}"
        )
        layout.addWidget(dest_label)

        self._dir_edit = QLineEdit(get_output_dir())
        self._dir_edit.setStyleSheet(
            f"QLineEdit {{"
            f"  border: 1px solid {DesignSystem.COLOR_BORDER};"
            f"  background-color: {DesignSystem.COLOR_BACKGROUND};"
            f"  border-radius: {DesignSystem.RADIUS_BASE}px;"
            f"  padding: 4px 8px;"
            f"  font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f"  color: {DesignSystem.COLOR_TEXT};"
            f"  min-height: 24px;"
            f"  max-height: 24px;"
            f"}}"
            f"QLineEdit:focus {{"
            f"  border-color: {DesignSystem.COLOR_PRIMARY};"
            f"}}"
        )
        self._dir_edit.setReadOnly(True)
        layout.addWidget(self._dir_edit, 1)

        self._btn_browse = QPushButton(tr("main_window.browse"))
        self._btn_browse.setStyleSheet(
            f"QPushButton {{"
            f"  background-color: {DesignSystem.COLOR_SURFACE};"
            f"  color: {DesignSystem.COLOR_TEXT};"
            f"  border: 1px solid {DesignSystem.COLOR_BORDER};"
            f"  border-radius: {DesignSystem.RADIUS_BASE}px;"
            f"  padding: 4px 12px;"
            f"  font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f"  min-height: 24px;"
            f"  max-height: 24px;"
            f"}}"
            f"QPushButton:hover {{"
            f"  background-color: {DesignSystem.COLOR_SECONDARY_LIGHT};"
            f"  border-color: {DesignSystem.COLOR_TEXT_SECONDARY};"
            f"}}"
        )
        self._btn_browse.clicked.connect(self._browse_dir)

        self._disk_space_label = QLabel("")
        self._disk_space_label.setStyleSheet(
            f"QLabel {{"
            f"  font-size: {DesignSystem.FONT_SIZE_XS}px;"
            f"  color: {DesignSystem.COLOR_TEXT_SECONDARY};"
            f"  border: none; background: transparent;"
            f"}}"
        )
        self._update_disk_space()

        self._btn_scan = QPushButton(tr("common.scan"))
        self._btn_scan.setStyleSheet(DesignSystem.get_scan_button_style())
        icon_manager.set_button_icon(
            self._btn_scan, "magnify", color="#FFFFFF", size=18
        )
        self._btn_scan.clicked.connect(self._on_scan_clicked)

        layout.addWidget(self._btn_browse)
        layout.addWidget(self._disk_space_label)
        layout.addWidget(self._btn_scan)

        return bar

    def _create_download_controls(self) -> QFrame:
        """Create download controls (hidden until after scan): progress + buttons."""
        bar = QFrame()
        bar.setStyleSheet(DesignSystem.get_card_style())
        layout = QVBoxLayout(bar)
        layout.setSpacing(DesignSystem.SPACE_12)

        btn_row = QHBoxLayout()

        self._overall_progress = QProgressBar()
        self._overall_progress.setRange(0, 100)
        self._overall_progress.setValue(0)
        self._overall_progress.setTextVisible(True)
        self._overall_progress.setFormat(tr("main_window.files_format"))
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
            f"QLabel {{"
            f"  font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f"  color: {DesignSystem.COLOR_TEXT_SECONDARY};"
            f"  border: none; background: transparent;"
            f"}}"
        )
        btn_row.addWidget(self._download_summary_label)

        btn_row.addStretch()

        self._btn_new_scan = QPushButton(tr("main_window.scan_new_url"))
        self._btn_new_scan.setStyleSheet(DesignSystem.get_secondary_button_style())
        icon_manager.set_button_icon(
            self._btn_new_scan, "magnify",
            color=DesignSystem.COLOR_TEXT_SECONDARY, size=16,
        )
        self._btn_new_scan.clicked.connect(self._on_new_scan)
        self._btn_new_scan.setVisible(False)
        btn_row.addWidget(self._btn_new_scan)

        self._btn_open_folder = QPushButton(tr("main_window.open_folder"))
        self._btn_open_folder.setStyleSheet(DesignSystem.get_secondary_button_style())
        icon_manager.set_button_icon(
            self._btn_open_folder, "folder-open",
            color=DesignSystem.COLOR_TEXT_SECONDARY, size=16,
        )
        self._btn_open_folder.clicked.connect(self._open_folder)
        self._btn_open_folder.setVisible(False)
        btn_row.addWidget(self._btn_open_folder)

        self._btn_cancel_dl = QPushButton(tr("common.cancel"))
        self._btn_cancel_dl.setStyleSheet(DesignSystem.get_danger_button_style())
        icon_manager.set_button_icon(
            self._btn_cancel_dl, "stop", color="#FFFFFF", size=16,
        )
        self._btn_cancel_dl.clicked.connect(self._cancel_download)
        self._btn_cancel_dl.setVisible(False)
        btn_row.addWidget(self._btn_cancel_dl)

        _dup_lbl_style = (
            f"QLabel {{"
            f"  font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f"  color: {DesignSystem.COLOR_TEXT_SECONDARY};"
            f"  border: none; background: transparent;"
            f"}}"
        )
        self._dup_label = QLabel(tr("url_input.duplicate_label"))
        self._dup_label.setStyleSheet(_dup_lbl_style)
        btn_row.addWidget(self._dup_label)

        self._duplicate_combo = QComboBox()
        self._duplicate_combo.setStyleSheet(
            DesignSystem.get_combobox_style() if hasattr(DesignSystem, "get_combobox_style") else ""
        )
        self._duplicate_combo.addItem(tr("url_input.duplicate_skip"), DUPLICATE_SKIP)
        self._duplicate_combo.addItem(tr("url_input.duplicate_overwrite"), DUPLICATE_OVERWRITE)
        self._duplicate_combo.addItem(tr("url_input.duplicate_rename"), DUPLICATE_RENAME)
        _current_dup = get_duplicate_action()
        for _i in range(self._duplicate_combo.count()):
            if self._duplicate_combo.itemData(_i) == _current_dup:
                self._duplicate_combo.setCurrentIndex(_i)
                break
        self._duplicate_combo.currentIndexChanged.connect(self._on_duplicate_changed)
        btn_row.addWidget(self._duplicate_combo)

        self._preserve_structure_check = QCheckBox(tr("main_window.preserve_structure"))
        self._preserve_structure_check.setStyleSheet(DesignSystem.get_checkbox_style())
        self._preserve_structure_check.setChecked(is_preserve_structure_enabled())
        self._preserve_structure_check.setToolTip(tr("main_window.preserve_structure_tooltip"))
        self._preserve_structure_check.toggled.connect(self._on_preserve_structure_changed)
        btn_row.addWidget(self._preserve_structure_check)

        self._btn_download = QPushButton(tr("common.download"))
        self._btn_download.setStyleSheet(DesignSystem.get_primary_button_style())
        icon_manager.set_button_icon(
            self._btn_download, "download", color="#FFFFFF", size=18,
        )
        self._btn_download.clicked.connect(self._on_download_clicked)
        btn_row.addWidget(self._btn_download)

        layout.addLayout(btn_row)
        return bar

    # ── Scan slots ────────────────────────────────────────────────────

    def _start_web_scan(self, url: str, extensions: list[str], recursive: bool, max_depth: int, restrict_to_base_path: bool, max_pages: int, max_files: int | None = None, delay: float = 0.5) -> None:
        """Start a Web mode scan with configurable options."""
        logger.info(
            "Starting Web scan: url=%s recursive=%s depth=%d max_pages=%d restrict_path=%s max_files=%s delay=%.1fs extensions=%s",
            url, recursive, max_depth, max_pages, restrict_to_base_path,
            max_files if max_files is not None else "unlimited",
            delay, extensions or "ALL",
        )
        self._cancel_scan()
        self._cancel_direct_scan()
        self._file_table.clear()
        self._file_table.setVisible(False)
        self._url_input.show_filters(False)
        self._download_controls.setVisible(False)
        self._bottom_spacer.setVisible(True)
        self._set_scan_button_scanning(True)
        self._url_input.set_status(tr("main_window.scanning"))
        self._url_input.hide_page_limit_warning()

        save_setting(LAST_URL, url)
        self._scan_url = url
        self._is_rss_scan = False
        self._direct_auto_download = False
        self._current_scan_mode = "web"
        self._url_input.set_rss_mode(False)

        self._scanner = ScannerWorker(
            url=url,
            extensions=extensions if extensions else None,
            recursive=recursive,
            max_depth=max_depth,
            delay=delay,
            max_pages=max_pages,
            restrict_to_base_path=restrict_to_base_path,
            max_files=max_files,
        )
        self._scanner.scan_progress.connect(self._url_input.set_status)
        self._scanner.scan_detail.connect(self._url_input.set_scan_detail)
        self._scanner.page_limit_reached.connect(self._url_input.show_page_limit_warning)
        self._scanner.files_found.connect(self._on_files_found)
        self._scanner.scan_error.connect(self._on_scan_error)
        self._scanner.scan_finished.connect(self._on_scan_finished)
        self._scanner.start()

    def _start_rss_scan(self, url: str) -> None:
        """Start an RSS feed scan (no recursion, no limits)."""
        logger.info("Starting RSS scan: %s", url)
        self._cancel_scan()
        self._cancel_direct_scan()
        self._file_table.clear()
        self._file_table.setVisible(False)
        self._url_input.show_filters(False)
        self._download_controls.setVisible(False)
        self._bottom_spacer.setVisible(True)
        self._set_scan_button_scanning(True)
        self._url_input.set_status(tr("main_window.scanning"))
        self._url_input.hide_page_limit_warning()

        save_setting(LAST_URL, url)
        self._scan_url = url
        self._is_rss_scan = False
        self._direct_auto_download = False
        self._current_scan_mode = "rss"
        self._url_input.set_rss_mode(False)

        self._scanner = ScannerWorker(
            url=url,
            extensions=None,
            recursive=False,
            max_depth=1,
            delay=0.5,
            max_pages=1,
            restrict_to_base_path=True,
            max_files=None,
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

    def _cancel_direct_scan(self) -> None:
        if self._direct_scanner and self._direct_scanner.isRunning():
            self._direct_scanner.cancel()
            self._direct_scanner.wait(3000)
        self._direct_scanner = None

    def _start_direct_scan(self, url: str, auto_download: bool = False) -> None:
        """Start a direct directory index scan (no page/file limits)."""
        logger.info("Starting Direct scan: %s (auto_download=%s)", url, auto_download)
        self._cancel_scan()
        self._cancel_direct_scan()
        self._file_table.clear()
        self._file_table.setVisible(False)
        self._url_input.show_filters(False)
        self._download_controls.setVisible(False)
        self._bottom_spacer.setVisible(True)
        self._set_scan_button_scanning(True)
        self._url_input.set_status(tr("direct_scan.starting"))
        self._url_input.hide_page_limit_warning()

        save_setting(LAST_URL, url)
        self._scan_url = url
        self._is_rss_scan = False
        self._direct_auto_download = auto_download
        self._current_scan_mode = "direct"
        self._url_input.set_rss_mode(False)

        self._direct_scanner = DirectoryScannerWorker(url=url)
        self._direct_scanner.scan_progress.connect(self._url_input.set_status)
        self._direct_scanner.scan_detail.connect(self._url_input.set_scan_detail)
        self._direct_scanner.files_found.connect(self._on_files_found)
        self._direct_scanner.scan_error.connect(self._on_scan_error)
        self._direct_scanner.scan_finished.connect(self._on_scan_finished)
        self._direct_scanner.start()

    def _on_files_found(self, files: list) -> None:
        self._found_files = [f.to_dict() if hasattr(f, "to_dict") else f for f in files]
        logger.info("Scan results: %d files found", len(self._found_files))
        if self._found_files:
            ext_counts: dict[str, int] = {}
            for f in self._found_files:
                e = f.get("extension", "?")
                ext_counts[e] = ext_counts.get(e, 0) + 1
            logger.info("  Extensions breakdown: %s", ext_counts)

        if self._current_scan_mode == "direct" and self._direct_auto_download:
            logger.info("Auto-download mode: skipping preview, downloading all %d files", len(self._found_files))
            if not self._found_files:
                self._url_input.set_status(tr("main_window.no_files_found"))
                self._url_input.set_scanning(False)
                return
            self._dl_selected_files = list(self._found_files)
            self._total_dl_bytes = sum(max(f.get("size_hint", 0) or 0, 0) for f in self._found_files)
            self._completed_dl_bytes = 0
            self._start_download_direct(self._dir_edit.text())
            return

        self._file_table.set_files(
            self._found_files,
            base_url=self._scan_url,
            preserve_structure=self._tree_view_mode,
        )
        if self._scanner and self._scanner.is_rss_feed:
            self._is_rss_scan = True
            self._file_table.set_rss_mode(True)
            self._url_input.set_rss_mode(True)
        self._file_table.setVisible(True)
        self._download_controls.setVisible(True)
        self._bottom_spacer.setVisible(False)
        self._btn_download.setEnabled(len(self._found_files) > 0)
        self._url_input.show_tree_button(len(self._found_files) > 0)
        self._url_input.show_filters(True)
        # Apply current filter state to the table
        active_ext = self._url_input.get_active_extensions()
        if active_ext:
            self._file_table.filter_by_extensions(active_ext)
        # Refresh summary now that table is visible
        self._file_table.refresh_summary()

    def _on_scan_error(self, error: str) -> None:
        logger.error("Scan error: %s", error)
        self._url_input.set_status(tr("main_window.error_status", error=error))

    def _on_scan_finished(self) -> None:
        self._set_scan_button_scanning(False)
        # Check if the scanner detected an RSS/podcast feed
        if self._scanner and self._scanner.is_rss_feed:
            self._is_rss_scan = True
        if self._found_files:
            if self._is_rss_scan:
                self._url_input.set_status(
                    tr("scanner.rss_feed_detected", count=len(self._found_files))
                )
            else:
                self._url_input.set_status(tr("main_window.files_found", count=len(self._found_files)))
        elif not self._url_input._status_label.text().startswith(tr("common.error")):
            self._url_input.set_status(tr("main_window.no_files_found"))

    # ── Selection slot ────────────────────────────────────────────────

    def _on_scan_clicked(self) -> None:
        """Forward scan click to the URL input widget."""
        self._url_input._on_scan_clicked()

    def _set_scan_button_visible(self, visible: bool) -> None:
        """Show/hide the scan button in the destination bar."""
        self._btn_scan.setVisible(visible)
        if visible:
            self._btn_scan.setText(tr("common.scan"))
            self._btn_scan.setStyleSheet(DesignSystem.get_scan_button_style())
            icon_manager.set_button_icon(
                self._btn_scan, "magnify", color="#FFFFFF", size=18
            )
            self._btn_scan.setEnabled(True)
        self._url_input._btn_scan.setVisible(visible)
        self._url_input._btn_scan.setEnabled(visible)

    def _set_scan_button_scanning(self, scanning: bool) -> None:
        """Update scan button to reflect scanning state."""
        if scanning:
            self._btn_scan.setText(tr("url_input.cancel"))
            self._btn_scan.setStyleSheet(DesignSystem.get_danger_button_style())
            icon_manager.set_button_icon(
                self._btn_scan, "stop", color="#FFFFFF", size=18
            )
            self._btn_scan.setVisible(True)
            self._url_input._url_combo.setEnabled(False)
            self._url_input._btn_clear_history.setEnabled(False)
            self._url_input._mode_group.setEnabled(False)
            self._url_input._mode_label.setEnabled(False)
            self._url_input._options_stack.setEnabled(False)
            self._url_input._btn_tree.setEnabled(False)
            self._url_input._btn_view_toggle.setEnabled(False)
            for btn in self._url_input._filter_buttons.values():
                btn.setEnabled(False)
        else:
            self._btn_scan.setText(tr("common.scan"))
            self._btn_scan.setStyleSheet(DesignSystem.get_scan_button_style())
            icon_manager.set_button_icon(
                self._btn_scan, "magnify", color="#FFFFFF", size=18
            )
            self._btn_scan.setEnabled(True)
            self._btn_scan.setVisible(True)
            self._url_input._url_combo.setEnabled(True)
            self._url_input._btn_clear_history.setEnabled(True)
            self._url_input._mode_group.setEnabled(True)
            self._url_input._mode_label.setEnabled(True)
            self._url_input._options_stack.setEnabled(True)
            self._url_input._btn_tree.setEnabled(True)
            self._url_input._btn_view_toggle.setEnabled(True)
            for btn in self._url_input._filter_buttons.values():
                btn.setEnabled(True)
            self._url_input._scan_detail_label.setVisible(False)
            self._url_input._rec_row_widget.setVisible(False)

    def _on_selection_changed(self, selected: list) -> None:
        self._btn_download.setEnabled(len(selected) > 0)

    def _on_filter_changed(self, extensions: list[str]) -> None:
        """Apply file type filter to the table."""
        self._file_table.filter_by_extensions(extensions)

    def _on_duplicate_changed(self, index: int) -> None:
        save_setting(DUPLICATE_ACTION, self._duplicate_combo.itemData(index))

    def _on_rss_date_filter_changed(self, days) -> None:
        """Forward RSS date filter from URL input to the file table."""
        self._file_table.filter_rss_by_date(days)

    def _on_preserve_structure_changed(self, checked: bool) -> None:
        """Update file table preview when preserve structure is toggled."""
        if self._found_files:
            self._file_table.set_preserve_structure(checked)

    def _on_view_mode_changed(self, is_tree: bool) -> None:
        """Switch file table between tree (hierarchical) and flat list view."""
        self._tree_view_mode = is_tree
        if self._found_files:
            self._file_table.set_preserve_structure(is_tree)

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

        self._dl_selected_files = selected
        self._total_dl_bytes = sum(max(f.get("size_hint", 0) or 0, 0) for f in selected)
        self._completed_dl_bytes = 0

        self._cancel_download()

        # Switch file table to download mode
        self._file_table.start_download_mode()
        self._url_input.set_filters_enabled(False)
        self._url_input.show_filters(False)
        self._url_input.set_inputs_enabled(False)
        if hasattr(self, '_btn_browse'):
            self._btn_browse.setEnabled(False)
            self._dir_edit.setEnabled(False)
            self._preserve_structure_check.setEnabled(False)
            self._dup_label.setEnabled(False)
            self._duplicate_combo.setEnabled(False)

        # Setup overall progress
        self._overall_progress.setRange(0, len(selected))
        self._overall_progress.setValue(0)
        self._overall_progress.setVisible(True)
        self._btn_cancel_dl.setVisible(True)
        self._btn_download.setEnabled(False)
        self._btn_open_folder.setVisible(False)
        self._btn_new_scan.setVisible(False)
        self._btn_scan.setVisible(False)
        if self._total_dl_bytes > 0:
            self._download_summary_label.setText(
                tr("main_window.size_progress", completed="0 B", total=_fmt_size(self._total_dl_bytes))
            )
        else:
            self._download_summary_label.setText("")

        self._downloader = DownloadWorker(
            files=selected,
            output_dir=output_dir,
            base_url=self._scan_url,
            preserve_structure=self._preserve_structure_check.isChecked(),
        )
        self._downloader.file_progress.connect(self._file_table.update_download_progress)
        self._downloader.file_complete.connect(self._file_table.set_download_complete)
        self._downloader.file_complete.connect(self._on_dl_file_done)
        self._downloader.file_error.connect(self._file_table.set_download_error)
        self._downloader.file_skipped.connect(self._file_table.set_download_skipped)
        self._downloader.file_skipped.connect(self._on_dl_file_done)
        self._downloader.overall_progress.connect(self._on_overall_progress)
        self._downloader.all_complete.connect(self._on_all_complete)
        self._downloader.start()

    def _start_download_direct(self, output_dir: str) -> None:
        """Start direct download without preview table (auto-download mode)."""
        self._cancel_download()

        self._url_input.set_filters_enabled(False)
        self._url_input.set_inputs_enabled(False)
        self._btn_browse.setEnabled(False)
        self._dir_edit.setEnabled(False)

        self._overall_progress.setRange(0, len(self._dl_selected_files))
        self._overall_progress.setValue(0)
        self._overall_progress.setVisible(True)
        self._btn_cancel_dl.setVisible(True)
        self._download_controls.setVisible(True)
        self._btn_download.setVisible(False)
        self._btn_open_folder.setVisible(False)
        self._btn_new_scan.setVisible(False)
        self._btn_scan.setVisible(False)
        self._dup_label.setVisible(False)
        self._duplicate_combo.setVisible(False)
        self._preserve_structure_check.setVisible(False)

        if self._total_dl_bytes > 0:
            self._download_summary_label.setText(
                tr("main_window.size_progress", completed="0 B", total=_fmt_size(self._total_dl_bytes))
            )
        else:
            self._download_summary_label.setText("")

        self._downloader = DownloadWorker(
            files=self._dl_selected_files,
            output_dir=output_dir,
            base_url=self._scan_url,
            preserve_structure=True,
        )
        self._downloader.file_progress.connect(self._on_direct_file_progress)
        self._downloader.file_complete.connect(self._on_dl_file_done)
        self._downloader.file_error.connect(self._on_direct_file_error)
        self._downloader.file_skipped.connect(self._on_dl_file_done)
        self._downloader.overall_progress.connect(self._on_overall_progress)
        self._downloader.all_complete.connect(self._on_all_complete)
        self._downloader.start()

    def _on_direct_file_progress(self, index: int, percent: int, downloaded: int) -> None:
        """Update status during direct download (no table)."""
        if 0 <= index < len(self._dl_selected_files):
            filename = self._dl_selected_files[index].get("filename", "")
            self._url_input.set_status(
                tr("direct_scan.downloading_file",
                   current=index + 1,
                   total=len(self._dl_selected_files),
                   filename=filename[:50])
            )

    def _on_direct_file_error(self, index: int, error: str) -> None:
        """Log error during direct download."""
        if 0 <= index < len(self._dl_selected_files):
            filename = self._dl_selected_files[index].get("filename", "")
            logger.warning("Direct download error for %s: %s", filename, error)

    def _cancel_download(self) -> None:
        if self._downloader and self._downloader.isRunning():
            self._downloader.cancel()
            self._downloader.wait(5000)
        self._downloader = None
        # Restore UI state (safe to call even if not in download mode)
        self._file_table.exit_download_mode()
        self._url_input.set_filters_enabled(True)
        self._url_input.show_filters(True)
        self._url_input.set_inputs_enabled(True)
        self._btn_scan.setVisible(True)
        if hasattr(self, '_btn_browse'):
            self._btn_browse.setEnabled(True)
            self._dir_edit.setEnabled(True)
            self._preserve_structure_check.setEnabled(True)
            self._dup_label.setEnabled(True)
            self._duplicate_combo.setEnabled(True)
        self._overall_progress.setVisible(False)
        self._btn_cancel_dl.setVisible(False)
        self._btn_download.setEnabled(True)

    def _on_overall_progress(self, completed: int, total: int) -> None:
        self._overall_progress.setValue(completed)

    def _on_dl_file_done(self, index: int, _: str) -> None:
        """Accumulate downloaded bytes and refresh the size label."""
        if 0 <= index < len(self._dl_selected_files) and self._total_dl_bytes > 0:
            size = max(self._dl_selected_files[index].get("size_hint", 0) or 0, 0)
            self._completed_dl_bytes += size
            remaining = self._total_dl_bytes - self._completed_dl_bytes
            self._download_summary_label.setText(
                tr("main_window.size_progress", completed=_fmt_size(self._completed_dl_bytes), total=_fmt_size(self._total_dl_bytes))
                + (f"  —  {tr('main_window.remaining', size=_fmt_size(remaining))}" if remaining > 0 else "")
            )

    def _on_all_complete(self, success: int, errors: int, skipped: int) -> None:
        logger.info("Download complete: %d success, %d errors, %d skipped", success, errors, skipped)
        self._btn_cancel_dl.setVisible(False)
        self._btn_download.setEnabled(True)
        self._btn_download.setVisible(True)
        self._btn_open_folder.setVisible(True)
        self._btn_new_scan.setVisible(True)
        self._btn_scan.setVisible(True)
        self._overall_progress.setVisible(False)
        self._url_input.set_filters_enabled(True)
        self._url_input.show_filters(True)
        self._url_input.set_inputs_enabled(True)
        self._btn_browse.setEnabled(True)
        self._dir_edit.setEnabled(True)
        self._preserve_structure_check.setEnabled(True)
        self._preserve_structure_check.setVisible(True)
        self._dup_label.setEnabled(True)
        self._dup_label.setVisible(True)
        self._duplicate_combo.setEnabled(True)
        self._duplicate_combo.setVisible(True)

        if errors == 0 and skipped == 0:
            self._download_summary_label.setText(
                tr("main_window.success_download", success=success)
            )
            self._download_summary_label.setStyleSheet(
                f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
                f" color: {DesignSystem.COLOR_SUCCESS};"
                f" font-weight: {DesignSystem.FONT_WEIGHT_BOLD};"
                f" border: none; background: transparent;"
            )
        elif errors == 0 and skipped > 0:
            self._download_summary_label.setText(
                tr("main_window.success_download_with_skipped", success=success, skipped=skipped)
            )
            self._download_summary_label.setStyleSheet(
                f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
                f" color: {DesignSystem.COLOR_SUCCESS};"
                f" font-weight: {DesignSystem.FONT_WEIGHT_BOLD};"
                f" border: none; background: transparent;"
            )
        elif errors > 0 and skipped == 0:
            self._download_summary_label.setText(
                tr("main_window.download_with_errors", success=success, errors=errors)
            )
            self._download_summary_label.setStyleSheet(
                f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
                f" color: {DesignSystem.COLOR_WARNING_TEXT};"
                f" font-weight: {DesignSystem.FONT_WEIGHT_BOLD};"
                f" border: none; background: transparent;"
            )
        else:
            self._download_summary_label.setText(
                tr("main_window.download_with_errors_skipped", success=success, errors=errors, skipped=skipped)
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
        self._download_controls.setVisible(False)
        self._bottom_spacer.setVisible(True)
        self._btn_new_scan.setVisible(False)
        self._btn_open_folder.setVisible(False)
        self._url_input.show_tree_button(False)
        self._overall_progress.setVisible(False)
        self._download_summary_label.setText("")
        self._url_input.set_status("")
        self._url_input.show_filters(False)
        self._btn_scan.setVisible(False)
        self._url_input._url_combo.lineEdit().setFocus()

    # ── Helpers ───────────────────────────────────────────────────────

    def _browse_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self, tr("main_window.select_download_dir"), self._dir_edit.text(),
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
                text = tr("main_window.mb_free", free=f"{free / (1024 * 1024):.0f}")
            else:
                text = tr("main_window.gb_free", free=f"{free / (1024 * 1024 * 1024):.1f}")
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

    def _show_tree_analysis(self) -> None:
        from safetool_downloader_desktop.dialogs.tree_analysis_dialog import TreeAnalysisDialog
        from safetool_downloader_desktop.workers.scanner_worker import build_directory_tree_report

        report = build_directory_tree_report(self._scan_url, self._found_files)
        dlg = TreeAnalysisDialog(report=report, base_url=self._scan_url, parent=self)
        dlg.exec()

    # ── Cleanup ───────────────────────────────────────────────────────

    def closeEvent(self, event) -> None:
        self._cancel_scan()
        self._cancel_direct_scan()
        self._cancel_download()
        super().closeEvent(event)
