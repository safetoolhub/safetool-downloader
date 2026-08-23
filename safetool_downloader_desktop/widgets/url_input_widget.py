# This file is part of SafeTool Downloader, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""URL input widget — URL bar, scan button, file type filters, recursive controls."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractButton,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from safetool_downloader_desktop.settings import (
    get_recursive_delay,
    get_recursive_max_depth,
    get_recursive_max_pages,
    is_recursive_enabled,
    is_recursive_restrict_path_enabled,
    get_url_history,
    add_url_to_history,
    clear_url_history,
)
from safetool_downloader_desktop.styles.design_system import DesignSystem
from safetool_downloader_desktop.styles.icons import icon_manager
from safetool_downloader_desktop.workers.scanner_worker import FILE_EXTENSIONS
from safetool_downloader_desktop.i18n import tr


class UrlInputWidget(QWidget):
    """Widget for URL input, file type filtering, and recursive crawling controls.

    Signals:
        scan_requested(str, list, bool, int): (url, extensions, recursive, max_depth).
        scan_cancel_requested(): User clicked cancel during an active scan.
    """

    scan_requested = Signal(str, list, bool, int, bool, int, object, float)  # (url, exts, recursive, max_depth, restrict_path, max_pages, max_files, delay)
    scan_cancel_requested = Signal()
    rss_scan_requested = Signal(str)  # URL for RSS feed scan
    direct_scan_requested = Signal(str, bool)  # (URL, auto_download) for direct file server download
    filter_changed = Signal(list)
    settings_requested = Signal()
    tree_analysis_requested = Signal()
    rss_date_filter_changed = Signal(object)  # days: int | None
    view_mode_changed = Signal(bool)  # True = tree mode, False = flat list


    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._scanning = False
        self._filter_buttons: dict[str, QPushButton] = {}
        self._active_filters: set[str] = set()
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(DesignSystem.SPACE_12)

        # ── URL Input Container ───────────────────────────────────────
        url_container = QFrame()
        url_container.setStyleSheet("QFrame { background: transparent; border: none; padding: 0px; }")
        url_layout = QVBoxLayout(url_container)
        url_layout.setContentsMargins(0, 0, 0, 0)
        url_layout.setSpacing(DesignSystem.SPACE_12)

        # Mode selector row
        mode_row = QHBoxLayout()
        mode_row.setSpacing(DesignSystem.SPACE_12)

        self._mode_label = QLabel(tr("url_input.download_mode_label"))
        self._mode_label.setStyleSheet(
            f"QLabel {{"
            f"  font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f"  font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};"
            f"  color: {DesignSystem.COLOR_TEXT_SECONDARY};"
            f"  border: none; background: transparent;"
            f"}}"
        )
        mode_row.addWidget(self._mode_label)

        # Segmented Control container QFrame
        self._mode_group = QFrame()
        self._mode_group.setObjectName("modeSegmented")
        self._mode_group.setStyleSheet(
            f"QFrame#modeSegmented {{"
            f"  background-color: {DesignSystem.COLOR_SECONDARY_LIGHT};"
            f"  border: 1px solid {DesignSystem.COLOR_BORDER};"
            f"  border-radius: {DesignSystem.RADIUS_BASE}px;"
            f"  padding: 2px;"
            f"}}"
        )
        segmented_layout = QHBoxLayout(self._mode_group)
        segmented_layout.setContentsMargins(0, 0, 0, 0)
        segmented_layout.setSpacing(2)

        # Checkable buttons representing the modes
        self._radio_web = QPushButton(tr("scan_modes.web_button"))
        self._radio_rss = QPushButton(tr("scan_modes.rss_button"))
        self._radio_direct = QPushButton(tr("scan_modes.direct_button"))

        self._mode_btn_group = QButtonGroup(self)
        self._mode_btn_group.setExclusive(True)

        for btn in (self._radio_web, self._radio_rss, self._radio_direct):
            btn.setCheckable(True)
            self._mode_btn_group.addButton(btn)
            btn.setStyleSheet(
                f"QPushButton {{"
                f"  background-color: transparent;"
                f"  color: {DesignSystem.COLOR_TEXT_SECONDARY};"
                f"  border: none;"
                f"  border-radius: {DesignSystem.RADIUS_SM}px;"
                f"  padding: 6px 16px;"
                f"  font-size: {DesignSystem.FONT_SIZE_SM}px;"
                f"  font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};"
                f"  min-height: 24px;"
                f"}}"
                f"QPushButton:hover {{"
                f"  background-color: rgba(0, 0, 0, 0.05);"
                f"  color: {DesignSystem.COLOR_TEXT};"
                f"}}"
                f"QPushButton:checked {{"
                f"  background-color: {DesignSystem.COLOR_PRIMARY};"
                f"  color: {DesignSystem.COLOR_PRIMARY_TEXT};"
                f"  font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};"
                f"}}"
            )
            segmented_layout.addWidget(btn)

        self._radio_web.setChecked(True)
        self._radio_web.setToolTip(tr("scan_modes.web_tooltip"))
        self._radio_rss.setToolTip(tr("scan_modes.rss_tooltip"))
        self._radio_direct.setToolTip(tr("scan_modes.direct_tooltip"))

        self._mode_btn_group.buttonToggled.connect(self._on_mode_changed)

        mode_row.addWidget(self._mode_group)
        mode_row.addStretch()

        # 2. Tree analysis button (right side of mode row)
        self._btn_tree = QPushButton(tr("url_input.tree_analysis"))
        self._btn_tree.setStyleSheet(DesignSystem.get_secondary_button_style())
        icon_manager.set_button_icon(
            self._btn_tree, "folder-tree",
            color=DesignSystem.COLOR_TEXT_SECONDARY, size=16,
        )
        self._btn_tree.setVisible(False)
        self._btn_tree.clicked.connect(self.tree_analysis_requested.emit)
        mode_row.addWidget(self._btn_tree)

        # 3. Status summary card (counts) — right side of mode row
        self._status_card = QFrame()
        self._status_card.setStyleSheet(DesignSystem.get_crawl_status_style())
        status_layout = QHBoxLayout(self._status_card)
        status_layout.setContentsMargins(DesignSystem.SPACE_12, 2, DesignSystem.SPACE_12, 2)
        self._status_label = QLabel("")
        self._status_label.setStyleSheet("QLabel { border: none; background: transparent; color: inherit; }")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        status_layout.addWidget(self._status_label)
        self._status_card.setVisible(False)
        mode_row.addWidget(self._status_card)

        url_layout.addLayout(mode_row)

        # URL input row
        input_row = QHBoxLayout()
        input_row.setSpacing(DesignSystem.SPACE_12)

        self._url_combo = QComboBox()
        self._url_combo.setEditable(True)
        self._url_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self._url_combo.lineEdit().setPlaceholderText(tr("url_input.placeholder"))
        self._url_combo.setStyleSheet(DesignSystem.get_url_combo_style())
        self._url_combo.lineEdit().returnPressed.connect(self._on_scan_clicked)
        self._refresh_history_items()
        input_row.addWidget(self._url_combo, 1)

        self._btn_clear_history = QToolButton()
        self._btn_clear_history.setAutoRaise(True)
        self._btn_clear_history.setStyleSheet(
            "QToolButton { border: none; background: transparent; }"
        )
        icon_manager.set_button_icon(
            self._btn_clear_history, "close-circle",
            color=DesignSystem.COLOR_TEXT_SECONDARY, size=18,
        )
        self._btn_clear_history.setToolTip(tr("url_input.clear_history_tooltip"))
        self._btn_clear_history.clicked.connect(self._on_clear_history)
        self._btn_clear_history.setVisible(bool(get_url_history()))
        input_row.addWidget(self._btn_clear_history)

        # Scan button (hidden - now in destination bar of main window)
        self._btn_scan = QPushButton(tr("common.scan"))
        self._btn_scan.setStyleSheet(DesignSystem.get_scan_button_style())
        icon_manager.set_button_icon(
            self._btn_scan, "magnify", color="#FFFFFF", size=18
        )
        self._btn_scan.clicked.connect(self._on_scan_clicked)
        self._btn_scan.setVisible(False)
        input_row.addWidget(self._btn_scan)

        url_layout.addLayout(input_row)

        # ── Options stack (fixed height, switches between Web/Direct) ──
        self._options_stack = QStackedWidget()

        # Web options page
        self._web_options = QWidget()
        web_options_layout = QHBoxLayout(self._web_options)
        web_options_layout.setContentsMargins(0, 0, 0, 0)
        web_options_layout.setSpacing(DesignSystem.SPACE_16)

        # 1. Recursive Options (inlined neatly)
        self._rec_check = QCheckBox(tr("url_input.recursive_scan"))
        self._rec_check.setStyleSheet(DesignSystem.get_checkbox_style())
        self._rec_check.setChecked(is_recursive_enabled())
        self._rec_check.setToolTip(tr("url_input.recursive_tooltip"))
        self._rec_check.toggled.connect(self._on_recursive_toggled)
        web_options_layout.addWidget(self._rec_check)

        self._depth_label = QLabel(tr("url_input.depth"))
        self._depth_label.setStyleSheet(DesignSystem.get_settings_note_style())
        web_options_layout.addWidget(self._depth_label)

        self._depth_spin = QSpinBox()
        self._depth_spin.setRange(1, 20)
        self._depth_spin.setValue(max(1, get_recursive_max_depth()))
        self._depth_spin.setFixedWidth(60)
        self._depth_spin.setStyleSheet(DesignSystem.get_spinbox_style())
        self._depth_spin.setToolTip(tr("url_input.depth_tooltip"))
        web_options_layout.addWidget(self._depth_spin)

        self._pages_label = QLabel(tr("url_input.max_pages"))
        self._pages_label.setStyleSheet(DesignSystem.get_settings_note_style())
        self._pages_label.setToolTip(tr("url_input.max_pages_tooltip"))
        web_options_layout.addWidget(self._pages_label)

        self._pages_spin = QSpinBox()
        self._pages_spin.setRange(1, 1000)
        self._pages_spin.setValue(max(1, get_recursive_max_pages()))
        self._pages_spin.setFixedWidth(75)
        self._pages_spin.setStyleSheet(DesignSystem.get_spinbox_style())
        self._pages_spin.setToolTip(tr("url_input.max_pages_tooltip"))
        web_options_layout.addWidget(self._pages_spin)

        self._restrict_path_check = QCheckBox(tr("url_input.restrict_to_path"))
        self._restrict_path_check.setStyleSheet(DesignSystem.get_checkbox_style())
        self._restrict_path_check.setChecked(is_recursive_restrict_path_enabled())
        self._restrict_path_check.setToolTip(tr("url_input.restrict_to_path_tooltip"))
        web_options_layout.addWidget(self._restrict_path_check)

        # Separator line
        v_line = QFrame()
        v_line.setFrameShape(QFrame.VLine)
        v_line.setFrameShadow(QFrame.Plain)
        v_line.setStyleSheet(
            f"color: {DesignSystem.COLOR_BORDER_LIGHT}; border: 1px solid {DesignSystem.COLOR_BORDER_LIGHT}; height: 16px;"
        )
        web_options_layout.addWidget(v_line)

        # Max-files control
        self._max_files_label = QLabel(tr("url_input.max_files_label"))
        self._max_files_label.setStyleSheet(
            f"QLabel {{"
            f"  font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f"  color: {DesignSystem.COLOR_TEXT_SECONDARY};"
            f"  border: none; background: transparent;"
            f"}}"
        )
        self._max_files_label.setToolTip(tr("url_input.max_files_tooltip"))
        web_options_layout.addWidget(self._max_files_label)

        self._max_files_spin = QSpinBox()
        self._max_files_spin.setMinimum(0)
        self._max_files_spin.setMaximum(9999)
        self._max_files_spin.setValue(0)
        self._max_files_spin.setSpecialValueText("\u221e")
        self._max_files_spin.setFixedWidth(70)
        self._max_files_spin.setStyleSheet(DesignSystem.get_spinbox_style())
        self._max_files_spin.setToolTip(tr("url_input.max_files_tooltip"))
        web_options_layout.addWidget(self._max_files_spin)

        # Delay control
        delay_layout = QHBoxLayout()
        delay_layout.setSpacing(DesignSystem.SPACE_6)
        self._delay_label = QLabel(tr("url_input.delay_label"))
        self._delay_label.setStyleSheet(
            f"QLabel {{"
            f"  font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f"  color: {DesignSystem.COLOR_TEXT_SECONDARY};"
            f"  border: none; background: transparent;"
            f"}}"
        )
        self._delay_label.setToolTip(tr("url_input.delay_tooltip"))
        delay_layout.addWidget(self._delay_label)

        self._delay_spin = QDoubleSpinBox()
        self._delay_spin.setRange(0.0, 5.0)
        self._delay_spin.setSingleStep(0.1)
        self._delay_spin.setDecimals(1)
        self._delay_spin.setValue(get_recursive_delay())
        self._delay_spin.setFixedWidth(60)
        self._delay_spin.setStyleSheet(DesignSystem.get_spinbox_style())
        self._delay_spin.setToolTip(tr("url_input.delay_tooltip"))
        self._delay_spin.setSuffix("s")
        web_options_layout.addWidget(self._delay_spin)
        
        web_options_layout.addStretch()
        self._options_stack.addWidget(self._web_options)

        # Direct options page
        self._direct_options = QWidget()
        direct_options_layout = QHBoxLayout(self._direct_options)
        direct_options_layout.setContentsMargins(0, 0, 0, 0)
        direct_options_layout.setSpacing(DesignSystem.SPACE_12)

        self._auto_download_check = QCheckBox(tr("direct_scan.auto_download"))
        self._auto_download_check.setStyleSheet(DesignSystem.get_checkbox_style())
        self._auto_download_check.setToolTip(tr("direct_scan.auto_download_tooltip"))
        self._auto_download_check.setChecked(False)
        direct_options_layout.addWidget(self._auto_download_check)
        direct_options_layout.addStretch()
        self._options_stack.addWidget(self._direct_options)

        # RSS placeholder (empty widget, same height)
        rss_placeholder = QWidget()
        self._options_stack.addWidget(rss_placeholder)

        url_layout.addWidget(self._options_stack)

        # ── Scan detail row (compact, auto-hides when label is empty) ──
        rec_row = QHBoxLayout()
        rec_row.setSpacing(DesignSystem.SPACE_12)

        # Scan detail label (left-aligned text to avoid horizontal jumping)
        self._scan_detail_label = QLabel("")
        self._scan_detail_label.setStyleSheet(
            f"QLabel {{"
            f"  font-size: {DesignSystem.FONT_SIZE_XS}px;"
            f"  color: {DesignSystem.COLOR_TEXT_SECONDARY};"
            f"  border: none; background: transparent;"
            f"}}"
        )
        self._scan_detail_label.setVisible(False)
        rec_row.addWidget(self._scan_detail_label)
        rec_row.addStretch()

        self._rec_row_widget = QWidget()
        self._rec_row_widget.setLayout(rec_row)
        self._rec_row_widget.setVisible(False)
        url_layout.addWidget(self._rec_row_widget)

        # Apply initial mode state (Web mode is checked by default)
        self._on_mode_changed()
        self._on_recursive_toggled(self._rec_check.isChecked())

        # ── Page limit warning banner (hidden until limit is hit) ──────
        self._page_limit_banner = QFrame()
        self._page_limit_banner.setObjectName("pageLimitBanner")
        self._page_limit_banner.setStyleSheet(
            f"QFrame#pageLimitBanner {{"
            f"  background-color: {DesignSystem.COLOR_WARNING_BG};"
            f"  border: 1px solid {DesignSystem.COLOR_WARNING};"
            f"  border-radius: {DesignSystem.RADIUS_BASE}px;"
            f"  padding: 0px;"
            f"}}"
        )
        banner_layout = QHBoxLayout(self._page_limit_banner)
        banner_layout.setContentsMargins(
            DesignSystem.SPACE_10, DesignSystem.SPACE_6,
            DesignSystem.SPACE_10, DesignSystem.SPACE_6,
        )
        banner_layout.setSpacing(DesignSystem.SPACE_8)

        banner_icon = QLabel()
        icon_manager.set_label_icon(
            banner_icon, "alert-circle",
            color=DesignSystem.COLOR_WARNING_TEXT, size=16,
        )
        banner_layout.addWidget(banner_icon)

        self._page_limit_label = QLabel()
        self._page_limit_label.setStyleSheet(
            f"QLabel {{"
            f"  font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f"  color: {DesignSystem.COLOR_WARNING_TEXT};"
            f"  border: none; background: transparent;"
            f"}}"
        )
        self._page_limit_label.setWordWrap(True)
        banner_layout.addWidget(self._page_limit_label, 1)

        self._page_limit_banner.setVisible(False)
        url_layout.addWidget(self._page_limit_banner)

        layout.addWidget(url_container)

        # ── File Type Filters (single line, hidden until scan completes) ──
        self._filter_row = QFrame()
        self._filter_row.setStyleSheet(
            f"QFrame {{ background-color: transparent; border: none; padding: 0px; }}"
        )
        filter_layout = QHBoxLayout(self._filter_row)
        filter_layout.setContentsMargins(0, 0, 0, 0)
        filter_layout.setSpacing(DesignSystem.SPACE_4)

        # Filter info button (first)
        self._filter_info = QToolButton()
        self._filter_info.setAutoRaise(True)
        self._filter_info.setStyleSheet("QToolButton { border: none; background: transparent; }")
        icon_manager.set_button_icon(
            self._filter_info, "information", color=DesignSystem.COLOR_TEXT_SECONDARY, size=16
        )
        filter_tooltip = tr("url_input.filter_tooltip_header") + "\n"
        for cat, ext_list in FILE_EXTENSIONS.items():
            filter_tooltip += f"\u2022 {tr('categories.' + cat)}: {', '.join(ext_list)}\n"
        self._filter_info.setToolTip(filter_tooltip.strip())
        filter_layout.addWidget(self._filter_info)

        filter_title = QLabel(tr("common.filters"))
        filter_title.setStyleSheet(
            f"QLabel {{"
            f"  font-size: {DesignSystem.FONT_SIZE_XS}px;"
            f"  font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};"
            f"  color: {DesignSystem.COLOR_TEXT_SECONDARY};"
            f"  border: none; background: transparent;"
            f"}}"
        )
        filter_layout.addWidget(filter_title)

        # "All Files" chip
        btn_all = QPushButton(tr("common.all"))
        btn_all.setCheckable(True)
        btn_all.setChecked(True)
        btn_all.setStyleSheet(DesignSystem.get_filter_chip_style(active=True))
        btn_all.clicked.connect(lambda: self._on_filter_clicked("All"))
        filter_layout.addWidget(btn_all)
        self._filter_buttons["All"] = btn_all

        for category in FILE_EXTENSIONS:
            btn = QPushButton(tr("categories." + category))
            btn.setCheckable(True)
            btn.setChecked(False)
            btn.setStyleSheet(DesignSystem.get_filter_chip_style(active=False))
            btn.clicked.connect(lambda checked, c=category: self._on_filter_clicked(c))
            filter_layout.addWidget(btn)
            self._filter_buttons[category] = btn

        filter_layout.addStretch()

        # ── View mode toggle (Tree / List) — always visible when filter row is visible ──
        self._view_mode_sep = QFrame()
        self._view_mode_sep.setFrameShape(QFrame.VLine)
        self._view_mode_sep.setFrameShadow(QFrame.Plain)
        self._view_mode_sep.setStyleSheet(
            f"QFrame {{"
            f"  color: {DesignSystem.COLOR_BORDER_LIGHT};"
            f"  border: 1px solid {DesignSystem.COLOR_BORDER_LIGHT};"
            f"  max-width: 1px;"
            f"  border-width: 0 1px 0 0;"
            f"}}"
        )
        filter_layout.addWidget(self._view_mode_sep)

        self._btn_view_toggle = QPushButton(tr("url_input.view_tree"))
        self._btn_view_toggle.setCheckable(True)
        self._btn_view_toggle.setChecked(True)  # default: tree mode
        self._btn_view_toggle.setStyleSheet(DesignSystem.get_filter_chip_style(active=True))
        self._btn_view_toggle.clicked.connect(self._on_view_toggle_clicked)
        filter_layout.addWidget(self._btn_view_toggle)

        # ── RSS-only controls (period filter + N latest) — hidden until RSS mode ──
        self._rss_v_sep = QFrame()
        self._rss_v_sep.setFrameShape(QFrame.VLine)
        self._rss_v_sep.setFrameShadow(QFrame.Plain)
        self._rss_v_sep.setStyleSheet(
            f"QFrame {{"
            f"  color: {DesignSystem.COLOR_BORDER_LIGHT};"
            f"  border: 1px solid {DesignSystem.COLOR_BORDER_LIGHT};"
            f"  max-width: 1px;"
            f"  border-width: 0 1px 0 0;"
            f"}}"
        )
        self._rss_v_sep.setVisible(False)
        filter_layout.addWidget(self._rss_v_sep)

        _xs_lbl_style = (
            f"QLabel {{"
            f"  font-size: {DesignSystem.FONT_SIZE_XS}px;"
            f"  color: {DesignSystem.COLOR_TEXT_SECONDARY};"
            f"  border: none; background: transparent;"
            f"}}"
        )
        self._rss_period_label = QLabel(tr("file_table.rss_date_filter"))
        self._rss_period_label.setStyleSheet(_xs_lbl_style)
        self._rss_period_label.setVisible(False)
        filter_layout.addWidget(self._rss_period_label)

        self._rss_date_combo = QComboBox()
        self._rss_date_combo.addItem(tr("file_table.rss_date_all"),  None)
        self._rss_date_combo.addItem(tr("file_table.rss_date_1m"),   30)
        self._rss_date_combo.addItem(tr("file_table.rss_date_3m"),   90)
        self._rss_date_combo.addItem(tr("file_table.rss_date_6m"),   180)
        self._rss_date_combo.addItem(tr("file_table.rss_date_1y"),   365)
        self._rss_date_combo.currentIndexChanged.connect(self._on_rss_date_changed)
        self._rss_date_combo.setVisible(False)
        filter_layout.addWidget(self._rss_date_combo)

        self._filter_row.setVisible(False)

    # ── Slots ─────────────────────────────────────────────────────────

    def _refresh_history_items(self) -> None:
        """Repopulate the URL combo items from saved history."""
        current_text = self._url_combo.currentText()
        self._url_combo.blockSignals(True)
        self._url_combo.clear()
        for url in get_url_history():
            self._url_combo.addItem(url)
        self._url_combo.setCurrentText(current_text)
        self._url_combo.blockSignals(False)
        has_history = bool(get_url_history())
        if hasattr(self, "_btn_clear_history"):
            self._btn_clear_history.setVisible(has_history)

    def _on_clear_history(self) -> None:
        current_text = self._url_combo.currentText()
        clear_url_history()
        self._url_combo.blockSignals(True)
        self._url_combo.clear()
        self._url_combo.setCurrentText(current_text)
        self._url_combo.blockSignals(False)
        self._btn_clear_history.setVisible(False)

    def _on_recursive_toggled(self, checked: bool) -> None:
        self._depth_label.setEnabled(checked)
        self._depth_spin.setEnabled(checked)
        self._pages_label.setEnabled(checked)
        self._pages_spin.setEnabled(checked)
        self._restrict_path_check.setEnabled(checked)

    def _on_rss_date_changed(self, index: int) -> None:
        days = self._rss_date_combo.itemData(index)
        self.rss_date_filter_changed.emit(days)

    def _on_view_toggle_clicked(self, is_tree: bool) -> None:
        if is_tree:
            self._btn_view_toggle.setText(tr("url_input.view_tree"))
            self._btn_view_toggle.setStyleSheet(DesignSystem.get_filter_chip_style(active=True))
        else:
            self._btn_view_toggle.setText(tr("url_input.view_list"))
            self._btn_view_toggle.setStyleSheet(DesignSystem.get_filter_chip_style(active=False))
        self.view_mode_changed.emit(is_tree)


    def _on_filter_clicked(self, category: str) -> None:
        if category == "All":
            self._active_filters.clear()
            for name, btn in self._filter_buttons.items():
                if name == "All":
                    btn.setChecked(True)
                    btn.setStyleSheet(DesignSystem.get_filter_chip_style(active=True))
                else:
                    btn.setChecked(False)
                    btn.setStyleSheet(DesignSystem.get_filter_chip_style(active=False))
        else:
            self._filter_buttons["All"].setChecked(False)
            self._filter_buttons["All"].setStyleSheet(
                DesignSystem.get_filter_chip_style(active=False)
            )

            if category in self._active_filters:
                self._active_filters.discard(category)
            else:
                self._active_filters.add(category)

            for name, btn in self._filter_buttons.items():
                if name == "All":
                    continue
                active = name in self._active_filters
                btn.setChecked(active)
                btn.setStyleSheet(DesignSystem.get_filter_chip_style(active=active))

            if not self._active_filters:
                self._filter_buttons["All"].setChecked(True)
                self._filter_buttons["All"].setStyleSheet(
                    DesignSystem.get_filter_chip_style(active=True)
                )

        self.filter_changed.emit(self.get_active_extensions())

    def _on_mode_changed(self, button: QAbstractButton | None = None, checked: bool = True) -> None:
        """Show/hide options based on selected mode."""
        if button is not None and not checked:
            return
        mode = self._get_mode()
        if mode == "web":
            self._options_stack.setCurrentIndex(0)
        elif mode == "direct":
            self._options_stack.setCurrentIndex(1)
        else:
            self._options_stack.setCurrentIndex(2)

    def _get_mode(self) -> str:
        """Return current mode based on selected segmented button."""
        if self._radio_web.isChecked():
            return "web"
        elif self._radio_rss.isChecked():
            return "rss"
        elif self._radio_direct.isChecked():
            return "direct"
        return "web"

    def _on_scan_clicked(self) -> None:
        """Emit the correct signal based on the selected mode."""
        if self._scanning:
            self.scan_cancel_requested.emit()
            return

        url = self._url_combo.currentText().strip()
        if not url:
            return
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
            self._url_combo.setCurrentText(url)

        add_url_to_history(url)
        self._refresh_history_items()

        mode = self._get_mode()

        if mode == "web":
            extensions: list[str] = []
            recursive = self._rec_check.isChecked()
            max_depth = self._depth_spin.value()
            max_pages = self._pages_spin.value()
            restrict_path = self._restrict_path_check.isChecked() if recursive else True
            max_files = self.get_max_download_files()
            delay = self._delay_spin.value()
            self.scan_requested.emit(url, extensions, recursive, max_depth, restrict_path, max_pages, max_files, delay)
        elif mode == "rss":
            self.rss_scan_requested.emit(url)
        elif mode == "direct":
            auto_download = self._auto_download_check.isChecked()
            self.direct_scan_requested.emit(url, auto_download)

    # ── Public API ────────────────────────────────────────────────────

    def set_scanning(self, scanning: bool) -> None:
        """Update UI to reflect scanning state."""
        self._scanning = scanning
        if scanning:
            self._page_limit_banner.setVisible(False)
            self._btn_scan.setText(tr("url_input.cancel"))
            self._btn_scan.setStyleSheet(DesignSystem.get_danger_button_style())
            icon_manager.set_button_icon(
                self._btn_scan, "stop", color="#FFFFFF", size=18
            )
            self._url_combo.setEnabled(False)
            self._btn_clear_history.setEnabled(False)
            self._mode_group.setEnabled(False)
            self._mode_label.setEnabled(False)
            self._options_stack.setEnabled(False)
            self._btn_tree.setEnabled(False)
            self._btn_view_toggle.setEnabled(False)
            for btn in self._filter_buttons.values():
                btn.setEnabled(False)
        else:
            self._btn_scan.setText(tr("common.scan"))
            self._btn_scan.setStyleSheet(DesignSystem.get_scan_button_style())
            icon_manager.set_button_icon(
                self._btn_scan, "magnify", color="#FFFFFF", size=18
            )
            self._url_combo.setEnabled(True)
            self._btn_clear_history.setEnabled(True)
            self._mode_group.setEnabled(True)
            self._mode_label.setEnabled(True)
            self._options_stack.setEnabled(True)
            self._btn_tree.setEnabled(True)
            self._btn_view_toggle.setEnabled(True)
            for btn in self._filter_buttons.values():
                btn.setEnabled(True)
            self._scan_detail_label.setVisible(False)
            self._rec_row_widget.setVisible(False)

    def set_scan_detail(self, text: str) -> None:
        """Show the current URL path being scanned."""
        if text:
            self._scan_detail_label.setText(f"\u21b3 {text}")
            self._scan_detail_label.setVisible(True)
            self._rec_row_widget.setVisible(True)
        else:
            self._scan_detail_label.setVisible(False)
            self._rec_row_widget.setVisible(False)

    def set_status(self, text: str) -> None:
        """Update the status summary count card."""
        if text:
            self._status_label.setText(text)
            self._status_card.setVisible(True)
        else:
            self._status_card.setVisible(False)

    def get_url(self) -> str:
        return self._url_combo.currentText().strip()

    def set_url(self, url: str) -> None:
        self._url_combo.setCurrentText(url)

    def show_filters(self, visible: bool) -> None:
        """Show or hide the filter chips row."""
        self._filter_row.setVisible(visible)

    def set_inputs_enabled(self, enabled: bool) -> None:
        """Enable or disable the main URL input controls."""
        self._url_combo.setEnabled(enabled)
        self._btn_scan.setEnabled(enabled)
        self._mode_group.setEnabled(enabled)
        self._mode_label.setEnabled(enabled)
        self._options_stack.setEnabled(enabled)
        self._btn_scan.setVisible(enabled)

    def set_filters_enabled(self, enabled: bool) -> None:
        """Enable or disable all filter chips."""
        for btn in self._filter_buttons.values():
            btn.setEnabled(enabled)
        self._rss_date_combo.setEnabled(enabled)
        self._btn_view_toggle.setEnabled(enabled)

    def get_active_extensions(self) -> list[str]:
        """Return the currently active file extensions for filtering."""
        if not self._active_filters:
            return []
        extensions: list[str] = []
        for cat in self._active_filters:
            extensions.extend(FILE_EXTENSIONS.get(cat, []))
        return extensions

    def show_tree_button(self, visible: bool) -> None:
        """Show or hide the Tree Analysis button."""
        self._btn_tree.setVisible(visible)

    def set_rss_mode(self, is_rss: bool) -> None:
        """Show or hide RSS-specific filter controls in the filter row."""
        for widget in (
            self._rss_v_sep,
            self._rss_period_label,
            self._rss_date_combo,
        ):
            widget.setVisible(is_rss)
        if not is_rss:
            # Reset period selector so next RSS scan starts with "All"
            self._rss_date_combo.setCurrentIndex(0)

    def show_page_limit_warning(self, limit: int) -> None:
        """Show the page-limit warning banner with the given limit value."""
        self._page_limit_label.setText(
            tr("url_input.page_limit_warning", limit=limit)
        )
        self._page_limit_banner.setVisible(True)

    def hide_page_limit_warning(self) -> None:
        """Hide the page-limit warning banner."""
        self._page_limit_banner.setVisible(False)

    def get_max_download_files(self) -> int | None:
        """Return the max-files-to-download limit, or None if unlimited."""
        val = self._max_files_spin.value()
        return None if val == 0 else val
