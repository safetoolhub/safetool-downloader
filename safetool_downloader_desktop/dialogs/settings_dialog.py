# This file is part of SafeTool Downloader, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Settings dialog — configure download directory, concurrency, crawling, etc."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from safetool_downloader_desktop.dialogs.base_dialog import BaseDialog
from safetool_downloader_desktop.settings import (
    CONCURRENT_DOWNLOADS,
    ENABLE_LOGGING,
    LAST_OUTPUT_DIR,
    RECURSIVE_DELAY,
    RECURSIVE_ENABLED,
    RECURSIVE_MAX_DEPTH,
    RECURSIVE_MAX_PAGES,
    get_concurrent_downloads,
    get_output_dir,
    get_recursive_delay,
    get_recursive_max_depth,
    get_recursive_max_pages,
    is_recursive_enabled,
    load_setting,
    save_setting,
)
from safetool_downloader_desktop.styles.design_system import DesignSystem
from safetool_downloader_desktop.styles.icons import icon_manager


class SettingsDialog(BaseDialog):
    """Application settings dialog."""

    settings_saved = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(500)
        self.setModal(True)
        self._build_ui()
        self._load_values()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(DesignSystem.SPACE_16)
        layout.setContentsMargins(
            DesignSystem.SPACE_24,
            DesignSystem.SPACE_24,
            DesignSystem.SPACE_24,
            DesignSystem.SPACE_24,
        )

        # ── Title ─────────────────────────────────────────────────────
        title = QLabel("Settings")
        title.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_XL}px;"
            f" font-weight: {DesignSystem.FONT_WEIGHT_BOLD};"
            f" color: {DesignSystem.COLOR_TEXT};"
            f" border: none; background: transparent;"
        )
        layout.addWidget(title)

        # ── Download Section ──────────────────────────────────────────
        dl_section = self._create_section("Download")
        dl_layout = dl_section.layout()

        # Output directory
        dir_label = QLabel("Default download directory:")
        dir_label.setStyleSheet(DesignSystem.get_settings_label_style())
        dl_layout.addWidget(dir_label)

        dir_row = QHBoxLayout()
        self._dir_edit = QLineEdit()
        self._dir_edit.setStyleSheet(DesignSystem.get_line_edit_style())
        self._dir_edit.setReadOnly(True)
        dir_row.addWidget(self._dir_edit, 1)

        btn_browse = QPushButton("Browse...")
        btn_browse.setStyleSheet(DesignSystem.get_secondary_button_style())
        btn_browse.clicked.connect(self._browse_dir)
        dir_row.addWidget(btn_browse)
        dl_layout.addLayout(dir_row)

        # Concurrent downloads
        conc_row = QHBoxLayout()
        conc_label = QLabel("Max concurrent downloads:")
        conc_label.setStyleSheet(DesignSystem.get_settings_label_style())
        conc_row.addWidget(conc_label)
        conc_row.addStretch()
        self._conc_spin = QSpinBox()
        self._conc_spin.setRange(1, 10)
        self._conc_spin.setStyleSheet(DesignSystem.get_spinbox_style())
        self._conc_spin.setFixedWidth(80)
        conc_row.addWidget(self._conc_spin)
        dl_layout.addLayout(conc_row)

        layout.addWidget(dl_section)

        # ── Recursive Crawling Section ────────────────────────────────
        rec_section = self._create_section("Recursive Crawling")
        rec_layout = rec_section.layout()

        self._rec_enabled = QCheckBox("Enable recursive scanning by default")
        self._rec_enabled.setStyleSheet(DesignSystem.get_checkbox_style())
        rec_layout.addWidget(self._rec_enabled)

        # Max depth
        depth_row = QHBoxLayout()
        depth_label = QLabel("Default max depth:")
        depth_label.setStyleSheet(DesignSystem.get_settings_label_style())
        depth_row.addWidget(depth_label)
        depth_row.addStretch()
        self._depth_spin = QSpinBox()
        self._depth_spin.setRange(0, 5)
        self._depth_spin.setStyleSheet(DesignSystem.get_spinbox_style())
        self._depth_spin.setFixedWidth(80)
        depth_row.addWidget(self._depth_spin)
        rec_layout.addLayout(depth_row)

        # Request delay
        delay_row = QHBoxLayout()
        delay_label = QLabel("Delay between requests (seconds):")
        delay_label.setStyleSheet(DesignSystem.get_settings_label_style())
        delay_row.addWidget(delay_label)
        delay_row.addStretch()
        self._delay_spin = QDoubleSpinBox()
        self._delay_spin.setRange(0.0, 5.0)
        self._delay_spin.setSingleStep(0.1)
        self._delay_spin.setDecimals(1)
        self._delay_spin.setStyleSheet(DesignSystem.get_spinbox_style())
        self._delay_spin.setFixedWidth(80)
        delay_row.addWidget(self._delay_spin)
        rec_layout.addLayout(delay_row)

        # Max pages
        pages_row = QHBoxLayout()
        pages_label = QLabel("Max pages to scan:")
        pages_label.setStyleSheet(DesignSystem.get_settings_label_style())
        pages_row.addWidget(pages_label)
        pages_row.addStretch()
        self._pages_spin = QSpinBox()
        self._pages_spin.setRange(1, 1000)
        self._pages_spin.setStyleSheet(DesignSystem.get_spinbox_style())
        self._pages_spin.setFixedWidth(100)
        pages_row.addWidget(self._pages_spin)
        rec_layout.addLayout(pages_row)

        note = QLabel(
            "Recursive scanning follows links on the same domain to find files "
            "across multiple pages. Higher depth and page limits increase scan time."
        )
        note.setWordWrap(True)
        note.setStyleSheet(DesignSystem.get_settings_note_style())
        rec_layout.addWidget(note)

        layout.addWidget(rec_section)

        # ── Debugging Section ─────────────────────────────────────────
        dbg_section = self._create_section("Debugging")
        dbg_layout = dbg_section.layout()

        self._logging_cb = QCheckBox("Enable logging (saves to ~/logs/)")
        self._logging_cb.setStyleSheet(DesignSystem.get_checkbox_style())
        dbg_layout.addWidget(self._logging_cb)

        layout.addWidget(dbg_section)

        # ── Buttons ───────────────────────────────────────────────────
        layout.addStretch()
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setStyleSheet(DesignSystem.get_secondary_button_style())
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        self._btn_save = QPushButton("Save")
        self._btn_save.setStyleSheet(DesignSystem.get_primary_button_style())
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

    def _load_values(self) -> None:
        self._dir_edit.setText(get_output_dir())
        self._conc_spin.setValue(get_concurrent_downloads())
        self._rec_enabled.setChecked(is_recursive_enabled())
        self._depth_spin.setValue(get_recursive_max_depth())
        self._delay_spin.setValue(get_recursive_delay())
        self._pages_spin.setValue(get_recursive_max_pages())
        self._logging_cb.setChecked(
            str(load_setting(ENABLE_LOGGING, False)).lower() in ("true", "1", "yes")
        )

    def _browse_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self,
            "Select Download Directory",
            self._dir_edit.text(),
        )
        if path:
            self._dir_edit.setText(path)

    def _save(self) -> None:
        save_setting(LAST_OUTPUT_DIR, self._dir_edit.text())
        save_setting(CONCURRENT_DOWNLOADS, self._conc_spin.value())
        save_setting(RECURSIVE_ENABLED, self._rec_enabled.isChecked())
        save_setting(RECURSIVE_MAX_DEPTH, self._depth_spin.value())
        save_setting(RECURSIVE_DELAY, self._delay_spin.value())
        save_setting(RECURSIVE_MAX_PAGES, self._pages_spin.value())
        save_setting(ENABLE_LOGGING, self._logging_cb.isChecked())
        self.settings_saved.emit()
        self.accept()
