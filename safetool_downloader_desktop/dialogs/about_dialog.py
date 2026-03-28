# This file is part of SafeTool Downloader, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""About dialog — application info, workflow, and license."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from config import (
    APP_AUTHOR,
    APP_CONTACT,
    APP_DESCRIPTION,
    APP_NAME,
    APP_VERSION,
    APP_VERSION_SUFFIX,
    APP_WEBSITE,
    get_full_version,
)
from safetool_downloader_desktop.dialogs.base_dialog import BaseDialog
from safetool_downloader_desktop.styles.design_system import DesignSystem
from safetool_downloader_desktop.styles.icons import icon_manager


class AboutDialog(BaseDialog):
    """About dialog with welcome and info tabs."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"About {APP_NAME}")
        self.setMinimumSize(720, 640)
        self.resize(740, 660)
        self.setModal(True)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = self._create_header()
        layout.addWidget(header)

        # Tab widget
        tabs = QTabWidget()
        tabs.setTabPosition(QTabWidget.TabPosition.West)
        tabs.setStyleSheet(DesignSystem.get_tutorial_tab_widget_style())

        tabs.addTab(self._create_welcome_tab(), "Welcome")
        tabs.addTab(self._create_info_tab(), "Info")

        layout.addWidget(tabs, 1)

        # Footer
        footer = self._create_footer()
        layout.addWidget(footer)

    # ── Header ────────────────────────────────────────────────────────

    def _create_header(self) -> QFrame:
        header = QFrame()
        header.setStyleSheet(
            f"QFrame {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0,"
            f" stop:0 {DesignSystem.COLOR_PRIMARY},"
            f" stop:1 {DesignSystem.COLOR_PRIMARY_HOVER});"
            f" padding: {DesignSystem.SPACE_20}px; }}"
        )

        layout = QHBoxLayout(header)
        layout.setSpacing(DesignSystem.SPACE_16)

        # Icon
        icon_label = QLabel()
        icon_path = Path(__file__).parent.parent.parent / "assets" / "icon.png"
        if icon_path.exists():
            pixmap = QPixmap(str(icon_path)).scaled(
                40, 40,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            icon_label.setPixmap(pixmap)
        else:
            icon_manager.set_label_icon(icon_label, "download", color="#FFFFFF", size=40)
        layout.addWidget(icon_label)

        # Title + version
        text_layout = QVBoxLayout()
        text_layout.setSpacing(DesignSystem.SPACE_4)

        title = QLabel(APP_NAME)
        title.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_XL}px;"
            f" font-weight: {DesignSystem.FONT_WEIGHT_BOLD};"
            f" color: white; border: none; background: transparent;"
        )
        text_layout.addWidget(title)

        version_row = QHBoxLayout()
        version_row.setSpacing(DesignSystem.SPACE_8)

        version_badge = QLabel(f"v{get_full_version()}")
        version_badge.setStyleSheet(
            f"QLabel {{ background-color: rgba(255,255,255,0.2);"
            f" color: white; border-radius: {DesignSystem.RADIUS_SM}px;"
            f" padding: 2px 8px;"
            f" font-size: {DesignSystem.FONT_SIZE_XS}px;"
            f" font-weight: {DesignSystem.FONT_WEIGHT_BOLD}; }}"
        )
        version_row.addWidget(version_badge)

        desc = QLabel(APP_DESCRIPTION)
        desc.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f" color: rgba(255,255,255,0.85);"
            f" border: none; background: transparent;"
        )
        version_row.addWidget(desc)
        version_row.addStretch()

        text_layout.addLayout(version_row)
        layout.addLayout(text_layout, 1)

        return header

    # ── Welcome Tab ───────────────────────────────────────────────────

    def _create_welcome_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(DesignSystem.get_tutorial_scroll_area_style())

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(DesignSystem.SPACE_16)
        layout.setContentsMargins(
            DesignSystem.SPACE_24,
            DesignSystem.SPACE_24,
            DesignSystem.SPACE_24,
            DesignSystem.SPACE_24,
        )

        # Description
        desc = QLabel(
            f"{APP_NAME} scans web pages and lets you preview, filter, "
            f"and download files by type. Supports recursive crawling to "
            f"find files across linked pages."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_BASE}px;"
            f" color: {DesignSystem.COLOR_TEXT};"
            f" border: none; background: transparent;"
            f" line-height: 1.5;"
        )
        layout.addWidget(desc)

        # Workflow section
        section_title = QLabel("How it works")
        section_title.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_LG}px;"
            f" font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};"
            f" color: {DesignSystem.COLOR_TEXT};"
            f" border: none; background: transparent;"
            f" padding-bottom: {DesignSystem.SPACE_8}px;"
        )
        layout.addWidget(section_title)

        steps = [
            ("1", "Enter URL", "Paste the website URL you want to scan for files."),
            ("2", "Scan & Filter", "The app scans the page (and subpages if recursive) and shows all found files. Filter by type."),
            ("3", "Select Files", "Check the files you want to download. Use Select All or filter by category."),
            ("4", "Download", "Choose destination folder and download. Track progress per file and overall."),
        ]
        for num, title, desc_text in steps:
            step = self._create_step_card(num, title, desc_text)
            layout.addWidget(step)

        # Features
        features_title = QLabel("Features")
        features_title.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_LG}px;"
            f" font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};"
            f" color: {DesignSystem.COLOR_TEXT};"
            f" border: none; background: transparent;"
            f" padding-top: {DesignSystem.SPACE_8}px;"
            f" padding-bottom: {DesignSystem.SPACE_8}px;"
        )
        layout.addWidget(features_title)

        features = [
            ("filter", "File type filters — PDF, images, audio, video, documents, archives"),
            ("sitemap", "Recursive crawling — follow links to find files across pages"),
            ("download-multiple", "Batch download — multiple files with progress tracking"),
            ("folder-download", "Custom destination — choose where to save files"),
        ]
        for icon_name, text in features:
            feat = self._create_feature_row(icon_name, text)
            layout.addWidget(feat)

        layout.addStretch()
        scroll.setWidget(content)
        return scroll

    # ── Info Tab ──────────────────────────────────────────────────────

    def _create_info_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(DesignSystem.get_tutorial_scroll_area_style())

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(DesignSystem.SPACE_16)
        layout.setContentsMargins(
            DesignSystem.SPACE_24,
            DesignSystem.SPACE_24,
            DesignSystem.SPACE_24,
            DesignSystem.SPACE_24,
        )

        # Developer info
        dev_title = QLabel("Developer")
        dev_title.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_LG}px;"
            f" font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};"
            f" color: {DesignSystem.COLOR_TEXT};"
            f" border: none; background: transparent;"
        )
        layout.addWidget(dev_title)

        dev_card = QFrame()
        dev_card.setStyleSheet(DesignSystem.get_about_info_card_style())
        dev_grid = QGridLayout(dev_card)
        dev_grid.setSpacing(DesignSystem.SPACE_8)

        info_items = [
            ("Organisation", APP_AUTHOR),
            ("Contact", f'<a href="mailto:{APP_CONTACT}">{APP_CONTACT}</a>'),
            ("Website", f'<a href="{APP_WEBSITE}">{APP_WEBSITE}</a>'),
            ("Version", get_full_version()),
            ("License", "GPLv3"),
        ]
        for row, (label, value) in enumerate(info_items):
            lbl = QLabel(label)
            lbl.setStyleSheet(DesignSystem.get_about_info_label_style())
            dev_grid.addWidget(lbl, row, 0)

            val = QLabel(value)
            val.setStyleSheet(DesignSystem.get_about_info_value_style())
            val.setOpenExternalLinks(True)
            val.setTextFormat(Qt.TextFormat.RichText)
            dev_grid.addWidget(val, row, 1)

        layout.addWidget(dev_card)

        # Values
        values_title = QLabel("Values")
        values_title.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_LG}px;"
            f" font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};"
            f" color: {DesignSystem.COLOR_TEXT};"
            f" border: none; background: transparent;"
            f" padding-top: {DesignSystem.SPACE_8}px;"
        )
        layout.addWidget(values_title)

        values = [
            ("shield", "Privacy First", "No tracking, no telemetry, no cloud."),
            ("wifi-off", "Offline Ready", "Works without internet after download."),
            ("file-code", "Open Source", "Licensed under GPLv3. Inspect every line."),
        ]
        for icon_name, title, desc in values:
            val_card = self._create_value_card(icon_name, title, desc)
            layout.addWidget(val_card)

        # License
        license_title = QLabel("License")
        license_title.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_LG}px;"
            f" font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};"
            f" color: {DesignSystem.COLOR_TEXT};"
            f" border: none; background: transparent;"
            f" padding-top: {DesignSystem.SPACE_8}px;"
        )
        layout.addWidget(license_title)

        license_text = QTextEdit()
        license_text.setReadOnly(True)
        license_text.setMaximumHeight(200)
        license_text.setStyleSheet(
            f"QTextEdit {{ background-color: {DesignSystem.COLOR_BACKGROUND};"
            f" border: 1px solid {DesignSystem.COLOR_BORDER};"
            f" border-radius: {DesignSystem.RADIUS_MD}px;"
            f" padding: {DesignSystem.SPACE_12}px;"
            f" font-family: {DesignSystem.FONT_FAMILY_MONO};"
            f" font-size: {DesignSystem.FONT_SIZE_XS}px;"
            f" color: {DesignSystem.COLOR_TEXT}; }}"
        )

        license_path = Path(__file__).parent.parent.parent / "LICENSE"
        if license_path.exists():
            license_text.setPlainText(license_path.read_text(encoding="utf-8"))
        else:
            license_text.setPlainText("GPLv3 — See https://www.gnu.org/licenses/gpl-3.0.txt")

        layout.addWidget(license_text)
        layout.addStretch()
        scroll.setWidget(content)
        return scroll

    # ── Footer ────────────────────────────────────────────────────────

    def _create_footer(self) -> QFrame:
        footer = QFrame()
        footer.setStyleSheet(
            f"QFrame {{ background-color: {DesignSystem.COLOR_SURFACE};"
            f" border-top: 1px solid {DesignSystem.COLOR_BORDER_LIGHT};"
            f" padding: {DesignSystem.SPACE_12}px {DesignSystem.SPACE_24}px; }}"
        )
        layout = QHBoxLayout(footer)
        layout.addStretch()

        btn_close = QPushButton("Close")
        btn_close.setStyleSheet(DesignSystem.get_primary_button_style())
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

        return footer

    # ── Helpers ───────────────────────────────────────────────────────

    def _create_step_card(self, number: str, title: str, desc: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background-color: {DesignSystem.COLOR_BACKGROUND};"
            f" border: none; border-radius: {DesignSystem.RADIUS_LG}px; }}"
        )
        layout = QHBoxLayout(card)
        layout.setSpacing(DesignSystem.SPACE_12)
        layout.setContentsMargins(
            DesignSystem.SPACE_16,
            DesignSystem.SPACE_12,
            DesignSystem.SPACE_16,
            DesignSystem.SPACE_12,
        )

        # Number badge
        num_label = QLabel(number)
        num_label.setFixedSize(28, 28)
        num_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        num_label.setStyleSheet(
            f"QLabel {{ background-color: {DesignSystem.COLOR_PRIMARY};"
            f" color: white;"
            f" font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f" font-weight: {DesignSystem.FONT_WEIGHT_BOLD};"
            f" border-radius: 14px; }}"
        )
        layout.addWidget(num_label)

        # Text
        text_layout = QVBoxLayout()
        text_layout.setSpacing(DesignSystem.SPACE_2)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(
            f"color: {DesignSystem.COLOR_TEXT};"
            f" font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f" font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};"
            f" border: none; background: transparent;"
        )
        text_layout.addWidget(title_lbl)

        desc_lbl = QLabel(desc)
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet(
            f"color: {DesignSystem.COLOR_TEXT_SECONDARY};"
            f" font-size: {DesignSystem.FONT_SIZE_XS}px;"
            f" border: none; background: transparent;"
        )
        text_layout.addWidget(desc_lbl)

        layout.addLayout(text_layout, 1)
        return card

    def _create_feature_row(self, icon_name: str, text: str) -> QFrame:
        row = QFrame()
        row.setStyleSheet(
            f"QFrame {{ background: transparent; border: none; }}"
        )
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, DesignSystem.SPACE_4, 0, DesignSystem.SPACE_4)
        layout.setSpacing(DesignSystem.SPACE_12)

        icon_lbl = QLabel()
        icon_manager.set_label_icon(
            icon_lbl, icon_name, color=DesignSystem.COLOR_PRIMARY, size=18
        )
        layout.addWidget(icon_lbl)

        text_lbl = QLabel(text)
        text_lbl.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f" color: {DesignSystem.COLOR_TEXT};"
            f" border: none; background: transparent;"
        )
        layout.addWidget(text_lbl, 1)

        return row

    def _create_value_card(self, icon_name: str, title: str, desc: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background: transparent; border: none; }}"
        )
        layout = QHBoxLayout(card)
        layout.setContentsMargins(0, DesignSystem.SPACE_4, 0, DesignSystem.SPACE_4)
        layout.setSpacing(DesignSystem.SPACE_12)

        icon_lbl = QLabel()
        icon_manager.set_label_icon(
            icon_lbl, icon_name, color=DesignSystem.COLOR_SUCCESS, size=20
        )
        layout.addWidget(icon_lbl)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(DesignSystem.SPACE_2)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(
            f"color: {DesignSystem.COLOR_TEXT};"
            f" font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f" font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};"
            f" border: none; background: transparent;"
        )
        text_layout.addWidget(title_lbl)

        desc_lbl = QLabel(desc)
        desc_lbl.setStyleSheet(
            f"color: {DesignSystem.COLOR_TEXT_SECONDARY};"
            f" font-size: {DesignSystem.FONT_SIZE_XS}px;"
            f" border: none; background: transparent;"
        )
        text_layout.addWidget(desc_lbl)

        layout.addLayout(text_layout, 1)
        return card
