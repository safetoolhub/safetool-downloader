# This file is part of SafeTool Downloader, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Settings dialog — configure download directory, concurrency, crawling, etc."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QSpinBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from safetool_downloader_desktop.dialogs.base_dialog import BaseDialog
from safetool_downloader_desktop.settings import (
    CONCURRENT_DOWNLOADS,
    ENABLE_LOGGING,
    LANGUAGE,
    LAST_OUTPUT_DIR,
    PRESERVE_STRUCTURE,
    RECURSIVE_DELAY,
    RECURSIVE_ENABLED,
    RECURSIVE_MAX_DEPTH,
    RECURSIVE_MAX_PAGES,
    RECURSIVE_RESTRICT_PATH,
    get_concurrent_downloads,
    get_output_dir,
    get_recursive_delay,
    get_recursive_max_depth,
    get_recursive_max_pages,
    is_preserve_structure_enabled,
    is_recursive_enabled,
    is_recursive_restrict_path_enabled,
    load_setting,
    save_setting,
)
from safetool_downloader_desktop.styles.design_system import DesignSystem
from safetool_downloader_desktop.styles.icons import icon_manager
from safetool_downloader_desktop.i18n import tr, SUPPORTED_LANGUAGES, get_current_language


class SettingsDialog(BaseDialog):
    """Application settings dialog."""

    settings_saved = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("settings_dialog.title"))
        self.setMinimumWidth(850)
        self.resize(950, 400)
        self.setModal(True)
        self._build_ui()
        self._load_values()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(DesignSystem.SPACE_20)
        layout.setContentsMargins(
            DesignSystem.SPACE_24,
            DesignSystem.SPACE_24,
            DesignSystem.SPACE_24,
            DesignSystem.SPACE_24,
        )

        # ── Main Content Area (Two Columns) ───────────────────────────
        content_row = QHBoxLayout()
        content_row.setSpacing(DesignSystem.SPACE_32)

        # ── LEFT COLUMN ───────────────────────────────────────────────
        left_col = QVBoxLayout()
        left_col.setSpacing(DesignSystem.SPACE_16)

        # 1. Download Section
        dl_section = self._create_section(tr("settings_dialog.download_section"))
        dl_layout = dl_section.layout()

        dir_label = QLabel(tr("settings_dialog.default_dir"))
        dir_label.setStyleSheet(DesignSystem.get_settings_label_style())
        dl_layout.addWidget(dir_label)

        dir_row = QHBoxLayout()
        self._dir_edit = QLineEdit()
        self._dir_edit.setStyleSheet(DesignSystem.get_line_edit_style())
        self._dir_edit.setReadOnly(True)
        dir_row.addWidget(self._dir_edit, 1)

        btn_browse = QPushButton(tr("settings_dialog.browse"))
        btn_browse.setStyleSheet(DesignSystem.get_secondary_button_style())
        btn_browse.clicked.connect(self._browse_dir)
        dir_row.addWidget(btn_browse)
        dl_layout.addLayout(dir_row)

        conc_row = QHBoxLayout()
        conc_label = QLabel(tr("settings_dialog.max_concurrent"))
        conc_label.setStyleSheet(DesignSystem.get_settings_label_style())
        conc_row.addWidget(conc_label)
        conc_row.addStretch()
        self._conc_spin = QSpinBox()
        self._conc_spin.setRange(1, 10)
        self._conc_spin.setStyleSheet(DesignSystem.get_spinbox_style())
        self._conc_spin.setFixedWidth(80)
        conc_row.addWidget(self._conc_spin)
        dl_layout.addLayout(conc_row)

        self._preserve_structure_cb = QCheckBox(tr("settings_dialog.preserve_structure"))
        self._preserve_structure_cb.setStyleSheet(DesignSystem.get_checkbox_style())
        dl_layout.addWidget(self._preserve_structure_cb)

        left_col.addWidget(dl_section)

        # 2. Debugging Section
        dbg_section = self._create_section(tr("settings_dialog.debugging_section"))
        dbg_layout = dbg_section.layout()
        self._logging_cb = QCheckBox(tr("settings_dialog.enable_logging"))
        self._logging_cb.setStyleSheet(DesignSystem.get_checkbox_style())
        dbg_layout.addWidget(self._logging_cb)

        left_col.addWidget(dbg_section)

        # 3. Language Section
        lang_section = self._create_section(tr("settings_dialog.language_section"))
        lang_layout = lang_section.layout()

        lang_row = QHBoxLayout()
        lang_label = QLabel(tr("settings_dialog.language_label"))
        lang_label.setStyleSheet(DesignSystem.get_settings_label_style())
        lang_row.addWidget(lang_label)
        lang_row.addStretch()
        self._lang_combo = QComboBox()
        self._lang_combo.setStyleSheet(DesignSystem.get_combobox_style() if hasattr(DesignSystem, 'get_combobox_style') else "")
        for code, name in SUPPORTED_LANGUAGES.items():
            self._lang_combo.addItem(name, code)
        lang_row.addWidget(self._lang_combo)
        lang_layout.addLayout(lang_row)

        lang_note = QLabel(tr("settings_dialog.language_restart"))
        lang_note.setStyleSheet(DesignSystem.get_settings_note_style())
        lang_note.setWordWrap(True)
        lang_layout.addWidget(lang_note)

        left_col.addWidget(lang_section)

        left_col.addStretch()
        content_row.addLayout(left_col, 3)

        # ── RIGHT COLUMN ──────────────────────────────────────────────
        right_col = QVBoxLayout()
        right_col.setSpacing(DesignSystem.SPACE_16)

        # 3. Recursive Crawling Section
        rec_section = self._create_section(tr("settings_dialog.recursive_section"))
        rec_layout = rec_section.layout()

        rec_header = QHBoxLayout()
        self._btn_info = QToolButton()
        self._btn_info.setStyleSheet(DesignSystem.get_icon_button_style())
        icon_manager.set_button_icon(
            self._btn_info, "information", color=DesignSystem.COLOR_TEXT_SECONDARY, size=18
        )
        self._btn_info.clicked.connect(self._show_info_dialog)
        rec_header.addWidget(self._btn_info)

        header_label = QLabel(tr("settings_dialog.scanner_behavior"))
        header_label.setStyleSheet(DesignSystem.get_settings_title_style())
        rec_header.addWidget(header_label)
        rec_header.addStretch()
        rec_layout.addLayout(rec_header)

        self._rec_group = QFrame()
        self._rec_group.setObjectName("recursiveGroup")
        self._rec_group.setStyleSheet(
            f"QFrame#recursiveGroup {{ background-color: {DesignSystem.COLOR_PRIMARY_SUBTLE};"
            f" border: 1px solid {DesignSystem.COLOR_PRIMARY_LIGHTER};"
            f" border-radius: {DesignSystem.RADIUS_BASE}px; padding: 12px; }}"
        )
        rec_group_layout = QVBoxLayout(self._rec_group)
        rec_group_layout.setSpacing(DesignSystem.SPACE_12)

        self._rec_enabled = QCheckBox(tr("settings_dialog.enable_recursive"))
        self._rec_enabled.setStyleSheet(DesignSystem.get_checkbox_style())
        self._rec_enabled.toggled.connect(self._on_recursive_toggled)
        rec_group_layout.addWidget(self._rec_enabled)

        self._rec_restrict_path = QCheckBox(tr("settings_dialog.restrict_to_base"))
        self._rec_restrict_path.setStyleSheet(DesignSystem.get_checkbox_style())
        rec_group_layout.addWidget(self._rec_restrict_path)

        depth_row = QHBoxLayout()
        self._depth_label = QLabel(tr("settings_dialog.max_depth"))
        self._depth_label.setStyleSheet(DesignSystem.get_settings_label_style())
        depth_row.addWidget(self._depth_label)
        depth_row.addStretch()
        self._depth_spin = QSpinBox()
        self._depth_spin.setRange(1, 20)
        self._depth_spin.setStyleSheet(DesignSystem.get_spinbox_style())
        self._depth_spin.setFixedWidth(80)
        depth_row.addWidget(self._depth_spin)
        rec_group_layout.addLayout(depth_row)
        rec_layout.addWidget(self._rec_group)

        # Limits and Delay
        delay_row = QHBoxLayout()
        delay_label = QLabel(tr("settings_dialog.request_delay"))
        delay_label.setStyleSheet(DesignSystem.get_settings_label_style())
        delay_row.addWidget(delay_label)
        delay_row.addStretch()
        self._delay_spin = QDoubleSpinBox()
        self._delay_spin.setRange(0.0, 5.0)
        self._delay_spin.setStyleSheet(DesignSystem.get_spinbox_style())
        self._delay_spin.setFixedWidth(70)
        delay_row.addWidget(self._delay_spin)
        rec_layout.addLayout(delay_row)

        pages_row = QHBoxLayout()
        pages_label = QLabel(tr("settings_dialog.max_pages"))
        pages_label.setStyleSheet(DesignSystem.get_settings_label_style())
        pages_row.addWidget(pages_label)
        pages_row.addStretch()
        self._pages_spin = QSpinBox()
        self._pages_spin.setRange(1, 1000)
        self._pages_spin.setStyleSheet(DesignSystem.get_spinbox_style())
        self._pages_spin.setFixedWidth(80)
        pages_row.addWidget(self._pages_spin)
        rec_layout.addLayout(pages_row)

        right_col.addWidget(rec_section)
        right_col.addStretch()
        content_row.addLayout(right_col, 4)

        layout.addLayout(content_row)

        # ── Buttons ───────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_cancel = QPushButton(tr("settings_dialog.cancel"))
        btn_cancel.setStyleSheet(DesignSystem.get_secondary_button_style())
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        self._btn_save = QPushButton(tr("settings_dialog.save_settings"))
        self._btn_save.setStyleSheet(DesignSystem.get_primary_button_style())
        self._btn_save.setMinimumWidth(120)
        self._btn_save.clicked.connect(self._save)
        btn_row.addWidget(self._btn_save)

        layout.addLayout(btn_row)

    def _create_section(self, title: str) -> QFrame:
        section = QFrame()
        section.setStyleSheet(DesignSystem.get_settings_section_style())
        layout = QVBoxLayout(section)
        layout.setSpacing(DesignSystem.SPACE_12)

        lbl = QLabel(title)
        lbl.setStyleSheet(DesignSystem.get_settings_title_style())
        layout.addWidget(lbl)

        return section


    def _on_recursive_toggled(self, checked: bool) -> None:
        self._rec_restrict_path.setEnabled(checked)
        self._depth_label.setEnabled(checked)
        self._depth_spin.setEnabled(checked)
        self._preserve_structure_cb.setEnabled(checked)

    def _show_info_dialog(self) -> None:
        from PySide6.QtWidgets import QMessageBox

        msg = QMessageBox(self)
        msg.setWindowTitle(tr("settings_dialog.scan_options_title"))
        msg.setIcon(QMessageBox.Information)
        msg.setText(tr("settings_dialog.scan_options_text"))
        msg.exec()

    def _load_values(self) -> None:
        self._dir_edit.setText(get_output_dir())
        self._conc_spin.setValue(get_concurrent_downloads())
        self._preserve_structure_cb.setChecked(is_preserve_structure_enabled())
        self._rec_enabled.setChecked(is_recursive_enabled())
        self._rec_restrict_path.setChecked(is_recursive_restrict_path_enabled())
        self._depth_spin.setValue(max(1, get_recursive_max_depth()))

        # Sync visual state
        is_rec = self._rec_enabled.isChecked()
        self._on_recursive_toggled(is_rec)

        self._delay_spin.setValue(get_recursive_delay())
        self._pages_spin.setValue(get_recursive_max_pages())
        self._logging_cb.setChecked(
            str(load_setting(ENABLE_LOGGING, False)).lower() in ("true", "1", "yes")
        )

        current_lang = get_current_language()
        for i in range(self._lang_combo.count()):
            if self._lang_combo.itemData(i) == current_lang:
                self._lang_combo.setCurrentIndex(i)
                break

    def _browse_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self,
            tr("settings_dialog.select_download_dir"),
            self._dir_edit.text(),
        )
        if path:
            self._dir_edit.setText(path)

    def _save(self) -> None:
        save_setting(LAST_OUTPUT_DIR, self._dir_edit.text())
        save_setting(CONCURRENT_DOWNLOADS, self._conc_spin.value())
        save_setting(PRESERVE_STRUCTURE, self._preserve_structure_cb.isChecked())
        save_setting(RECURSIVE_ENABLED, self._rec_enabled.isChecked())
        save_setting(RECURSIVE_RESTRICT_PATH, self._rec_restrict_path.isChecked())
        save_setting(RECURSIVE_MAX_DEPTH, self._depth_spin.value())
        save_setting(RECURSIVE_DELAY, self._delay_spin.value())
        save_setting(RECURSIVE_MAX_PAGES, self._pages_spin.value())
        save_setting(ENABLE_LOGGING, self._logging_cb.isChecked())
        save_setting(LANGUAGE, self._lang_combo.currentData())
        self.settings_saved.emit()
        self.accept()
