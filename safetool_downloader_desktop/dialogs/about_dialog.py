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
from safetool_downloader_desktop.i18n import tr


class AboutDialog(BaseDialog):
    """About dialog with welcome and info tabs."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("about_dialog.title", app_name=APP_NAME))
        self.setMinimumSize(900, 720)
        self.resize(920, 740)
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

        tabs.addTab(self._create_welcome_tab(), tr("about_dialog.welcome_tab"))
        tabs.addTab(self._create_info_tab(), tr("about_dialog.info_tab"))

        layout.addWidget(tabs, 1)

        # Footer
        footer = self._create_footer()
        layout.addWidget(footer)

    # ── Header ────────────────────────────────────────────────────────

    def _create_header(self) -> QFrame:
        """Creates the header with gradient and logo."""
        header = QFrame()
        header.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {DesignSystem.COLOR_PRIMARY}, stop:1 {DesignSystem.COLOR_PRIMARY_HOVER});
            }}
        """)
        
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(24, 12, 24, 12)
        
        # Left side: Title and version
        left_layout = QVBoxLayout()
        left_layout.setSpacing(2)
        
        title = QLabel(APP_NAME)
        title.setStyleSheet(f"""
            color: white;
            font-size: {DesignSystem.FONT_SIZE_XL}px;
            font-weight: {DesignSystem.FONT_WEIGHT_BOLD};
        """)
        title.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        left_layout.addWidget(title)
        
        version_str = get_full_version()
        version_lbl = QLabel(tr("common.version", version=version_str))
        version_lbl.setStyleSheet(f"""
            color: rgba(255, 255, 255, 0.9);
            font-size: {DesignSystem.FONT_SIZE_SM}px;
        """)
        version_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        left_layout.addWidget(version_lbl)
        
        header_layout.addLayout(left_layout)
        header_layout.addStretch()
        
        # Right side: Privacy badge
        privacy_badge = QLabel(tr("about_dialog.privacy_badge"))
        privacy_badge.setToolTip(tr("about_dialog.privacy_tooltip"))
        privacy_badge.setStyleSheet(f"""
            QLabel {{
                background-color: rgba(255, 255, 255, 0.2);
                color: white;
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
                padding: {DesignSystem.SPACE_6}px {DesignSystem.SPACE_16}px;
                border-radius: {DesignSystem.RADIUS_FULL}px;
            }}
        """)
        privacy_badge.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        header_layout.addWidget(privacy_badge)
        
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
        desc = QLabel(tr("about_dialog.description", app_name=APP_NAME))
        desc.setWordWrap(True)
        desc.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_BASE}px;"
            f" color: {DesignSystem.COLOR_TEXT};"
            f" border: none; background: transparent;"
            f" line-height: 1.5;"
        )
        layout.addWidget(desc)

        # Workflow section
        section_title = QLabel(tr("about_dialog.how_it_works"))
        section_title.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_LG}px;"
            f" font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};"
            f" color: {DesignSystem.COLOR_TEXT};"
            f" border: none; background: transparent;"
            f" padding-bottom: {DesignSystem.SPACE_8}px;"
        )
        layout.addWidget(section_title)

        steps = [
            ("1", tr("about_dialog.step1_title"), tr("about_dialog.step1_desc")),
            ("2", tr("about_dialog.step2_title"), tr("about_dialog.step2_desc")),
            ("3", tr("about_dialog.step3_title"), tr("about_dialog.step3_desc")),
            ("4", tr("about_dialog.step4_title"), tr("about_dialog.step4_desc")),
        ]
        for num, title, desc_text in steps:
            step = self._create_step_card(num, title, desc_text)
            layout.addWidget(step)

        # Features
        features_title = QLabel(tr("about_dialog.features_title"))
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
            ("filter", tr("about_dialog.feature_filters")),
            ("shield-check", tr("about_dialog.feature_privacy")),
            ("sitemap", tr("about_dialog.feature_recursive")),
            ("download-multiple", tr("about_dialog.feature_batch")),
            ("folder-download", tr("about_dialog.feature_destination")),
        ]
        for icon_name, text in features:
            feat = self._create_feature_row(icon_name, text)
            layout.addWidget(feat)

        layout.addStretch()
        scroll.setWidget(content)
        return scroll

    # ── Info Tab ──────────────────────────────────────────────────────

    def _create_info_tab(self) -> QWidget:
        """Creates the technical information tab with optimized, aligned design."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(DesignSystem.SPACE_24, DesignSystem.SPACE_16, DesignSystem.SPACE_24, DesignSystem.SPACE_16)
        layout.setSpacing(DesignSystem.SPACE_16)
        
        # === TITLE ===
        title = QLabel(tr("about_dialog.info_title"))
        title.setStyleSheet(DesignSystem.get_tutorial_section_header_style())
        title.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        layout.addWidget(title)
        
        # === DEVELOPER HERO (Clean, no boxes) ===
        dev_hero = self._create_developer_hero()
        layout.addWidget(dev_hero)

        # === ALIGNED INFO ROW (App Info + Formats) ===
        info_row = QWidget()
        info_row_layout = QHBoxLayout(info_row)
        info_row_layout.setContentsMargins(0, 0, 0, 0)
        info_row_layout.setSpacing(DesignSystem.SPACE_12)

        # Card 1: App Info
        app_card = self._create_info_card(tr("about_dialog.app_info"), [
            (tr("about_dialog.application"), APP_NAME),
            (tr("common.version_label"), get_full_version()),
            (tr("about_dialog.platforms"), "Linux, Windows, macOS"),
        ])
        info_row_layout.addWidget(app_card, 1)
        
        # Card 2: Formats
        formats_card = self._create_formats_card()
        info_row_layout.addWidget(formats_card, 1)
        
        layout.addWidget(info_row)
        
        # === VALUES FOOTER (100% Offline, No Tracking...) ===
        values_footer = self._create_values_footer()
        layout.addWidget(values_footer)

        # Trust Footer (Centered)
        trust_footer = QLabel(tr("about_dialog.trust_footer"))
        trust_footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        trust_footer.setStyleSheet(f"""
            color: {DesignSystem.COLOR_SUCCESS};
            font-size: {DesignSystem.FONT_SIZE_SM}px;
            font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
            margin-bottom: {DesignSystem.SPACE_8}px;
        """)
        trust_footer.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        layout.addWidget(trust_footer)

        # === LICENSE SECTION (At the bottom) ===
        license_container = QWidget()
        license_layout = QVBoxLayout(license_container)
        license_layout.setContentsMargins(0, DesignSystem.SPACE_12, 0, 0)
        license_layout.setSpacing(DesignSystem.SPACE_6)

        license_title = QLabel(tr("about_dialog.license"))
        license_title.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_XS}px;
            font-weight: {DesignSystem.FONT_WEIGHT_BOLD};
            color: {DesignSystem.COLOR_TEXT_SECONDARY};
            text-transform: uppercase;
        """)
        license_layout.addWidget(license_title)

        try:
            import sys
            if hasattr(sys, '_MEIPASS'):
                license_path = Path(sys._MEIPASS) / "LICENSE"
            else:
                license_path = Path(__file__).resolve().parent.parent.parent / "LICENSE"
            with open(license_path, "r", encoding="utf-8") as f:
                license_text = f.read()
        except Exception:
            license_text = "GPLv3 — See https://www.gnu.org/licenses/gpl-3.0.txt"

        license_edit = QTextEdit()
        license_edit.setReadOnly(True)
        license_edit.setPlainText(license_text)
        license_edit.setMaximumHeight(200)
        license_edit.setStyleSheet(
            f"QTextEdit {{"
            f"  font-size: {DesignSystem.FONT_SIZE_XS}px;"
            f"  font-family: {DesignSystem.FONT_FAMILY_MONO};"
            f"  color: {DesignSystem.COLOR_TEXT_SECONDARY};"
            f"  background-color: {DesignSystem.COLOR_BACKGROUND};"
            f"  border: 1px solid {DesignSystem.COLOR_BORDER_LIGHT};"
            f"  border-radius: {DesignSystem.RADIUS_SM}px;"
            f"  padding: {DesignSystem.SPACE_8}px;"
            f"}}"
        )
        license_layout.addWidget(license_edit)
        layout.addWidget(license_container)

        layout.addStretch()
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(DesignSystem.get_tutorial_scroll_area_style())
        scroll.setWidget(container)
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

        btn_close = QPushButton(tr("common.close"))
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

    def _create_developer_hero(self) -> QFrame:
        """Crea la sección del desarrollador resaltando la marca safetoolhub.org (limpio)."""
        outer_frame = QFrame()
        outer_frame.setStyleSheet("background: transparent; border: none;")
        
        outer_layout = QHBoxLayout(outer_frame)
        outer_layout.setSpacing(DesignSystem.SPACE_24)
        outer_layout.setContentsMargins(DesignSystem.SPACE_4, DesignSystem.SPACE_12, DesignSystem.SPACE_4, DesignSystem.SPACE_12)
        
        # Lado izquierdo: Desarrollado por
        dev_info_layout = QVBoxLayout()
        dev_info_layout.setSpacing(DesignSystem.SPACE_2)
        
        developed_by_label = QLabel(tr("about_dialog.developed_by"))
        developed_by_label.setStyleSheet(f"""
            color: {DesignSystem.COLOR_TEXT_SECONDARY};
            font-size: {DesignSystem.FONT_SIZE_SM}px;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            font-weight: {DesignSystem.FONT_WEIGHT_BOLD};
        """)
        dev_info_layout.addWidget(developed_by_label)
        
        org_link_name = QLabel(f'<a href="{APP_WEBSITE}" style="text-decoration: none; color: {DesignSystem.COLOR_PRIMARY};">safetoolhub.org</a>')
        org_link_name.setStyleSheet(f"""
            font-size: 36px;
            font-weight: {DesignSystem.FONT_WEIGHT_BOLD};
        """)
        org_link_name.setOpenExternalLinks(True)
        org_link_name.setCursor(Qt.CursorShape.PointingHandCursor)
        dev_info_layout.addWidget(org_link_name)
        
        tagline = QLabel(tr("about_dialog.tagline"))
        tagline.setStyleSheet(f"color: {DesignSystem.COLOR_TEXT}; font-size: {DesignSystem.FONT_SIZE_BASE}px; font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};")
        dev_info_layout.addWidget(tagline)
        
        outer_layout.addLayout(dev_info_layout)
        
        outer_layout.addStretch()

        # Lado derecho: Contacto (Limpio)
        contact_card = QWidget()
        contact_card.setStyleSheet("background: transparent; border: none;")
        contact_layout = QVBoxLayout(contact_card)
        contact_layout.setContentsMargins(0, 0, 0, 0)
        contact_layout.setSpacing(0)
        
        contact_title = QLabel(tr("about_dialog.contact"))
        contact_title.setStyleSheet(f"font-weight: {DesignSystem.FONT_WEIGHT_BOLD}; color: {DesignSystem.COLOR_TEXT_SECONDARY}; font-size: {DesignSystem.FONT_SIZE_XS}px; text-transform: uppercase; margin-bottom: -2px;")
        contact_layout.addWidget(contact_title, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)
        
        email_link = f'<a href="mailto:{APP_CONTACT}" style="color: {DesignSystem.COLOR_PRIMARY}; text-decoration: none;">{APP_CONTACT}</a>'
        email_label = QLabel(email_link)
        email_label.setOpenExternalLinks(True)
        email_label.setStyleSheet(f"font-size: {DesignSystem.FONT_SIZE_SM}px; font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};")
        email_label.setCursor(Qt.CursorShape.PointingHandCursor)
        contact_layout.addWidget(email_label, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        
        outer_layout.addWidget(contact_card, 0, Qt.AlignmentFlag.AlignVCenter)
        
        return outer_frame

    def _create_info_card(self, title: str, items: list) -> QFrame:
        """Crea una card de información con items."""
        frame = QFrame()
        frame.setStyleSheet(DesignSystem.get_about_info_card_style())
        
        layout = QVBoxLayout(frame)
        layout.setSpacing(DesignSystem.SPACE_2)
        layout.setContentsMargins(DesignSystem.SPACE_10, DesignSystem.SPACE_8, DesignSystem.SPACE_10, DesignSystem.SPACE_8)
        
        title_label = QLabel(title)
        title_label.setStyleSheet(DesignSystem.get_tutorial_card_title_style())
        title_label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        layout.addWidget(title_label)
        
        for label, value in items:
            row = QHBoxLayout()
            row.setSpacing(6)
            
            lbl = QLabel(f"{label}:")
            lbl.setStyleSheet(DesignSystem.get_about_info_label_style())
            lbl.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
            row.addWidget(lbl)
            
            val = QLabel(value)
            val.setStyleSheet(DesignSystem.get_about_info_value_style())
            val.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
            row.addWidget(val)
            row.addStretch()
            
            layout.addLayout(row)
        
        return frame

    def _create_formats_card(self) -> QFrame:
        """Crea la card de formatos soportados."""
        frame = QFrame()
        frame.setStyleSheet(DesignSystem.get_about_info_card_style())
        
        layout = QVBoxLayout(frame)
        layout.setSpacing(DesignSystem.SPACE_2)
        layout.setContentsMargins(DesignSystem.SPACE_10, DesignSystem.SPACE_8, DesignSystem.SPACE_10, DesignSystem.SPACE_8)
        
        title_label = QLabel(tr("about_dialog.supported_types"))
        title_label.setStyleSheet(DesignSystem.get_tutorial_card_title_style())
        title_label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        layout.addWidget(title_label)
        
        formats = [
            ("image", tr("about_dialog.images"), "JPG, PNG, WEBP, GIF"),
            ("video", tr("about_dialog.media"), "MP4, MP3, WAV, MKV"),
            ("file-text", tr("about_dialog.docs"), "PDF, DOCX, TXT"),
            ("archive", tr("about_dialog.archives"), "ZIP, RAR, 7Z"),
        ]
        
        for icon_name, fmt_title, fmt_list in formats:
            row = QHBoxLayout()
            row.setSpacing(6)
            
            icon_label = QLabel()
            icon_manager.set_label_icon(icon_label, icon_name, color=DesignSystem.COLOR_PRIMARY, size=14)
            row.addWidget(icon_label)
            
            text = QLabel(f"<b>{fmt_title}:</b> {fmt_list}")
            text.setStyleSheet(DesignSystem.get_about_formats_text_style())
            text.setWordWrap(True)
            text.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
            row.addWidget(text, 1)
            
            layout.addLayout(row)
        
        return frame

    def _create_values_footer(self) -> QFrame:
        """Crea la fila de valores (footer) sin bordes técnicos y con iconos alineados."""
        frame = QFrame()
        frame.setStyleSheet("background: transparent; border: none;")
        
        layout = QHBoxLayout(frame)
        layout.setSpacing(DesignSystem.SPACE_24)
        layout.setContentsMargins(0, DesignSystem.SPACE_16, 0, DesignSystem.SPACE_8)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        value_items = [
            ("wifi-off", tr("about_dialog.offline"), tr("about_dialog.offline_desc")),
            ("eye-off", tr("about_dialog.no_tracking"), tr("about_dialog.no_tracking_desc")),
            ("shield", tr("about_dialog.open_source"), tr("about_dialog.open_source_desc")),
        ]
        
        for icon_name, title, desc in value_items:
            item_widget = QWidget()
            item_layout = QHBoxLayout(item_widget)
            item_layout.setContentsMargins(0, 0, 0, 0)
            item_layout.setSpacing(DesignSystem.SPACE_12)
            
            icon_label = QLabel()
            icon_manager.set_label_icon(icon_label, icon_name, color=DesignSystem.COLOR_PRIMARY, size=24)
            item_layout.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignVCenter)
            
            text_layout = QVBoxLayout()
            text_layout.setSpacing(0)
            text_layout.setContentsMargins(0, 0, 0, 0)
            
            title_label = QLabel(title)
            title_label.setStyleSheet(f"font-weight: {DesignSystem.FONT_WEIGHT_BOLD}; color: {DesignSystem.COLOR_TEXT}; font-size: {DesignSystem.FONT_SIZE_SM}px; line-height: 100%;")
            text_layout.addWidget(title_label)
            
            desc_label = QLabel(desc)
            desc_label.setStyleSheet(f"color: {DesignSystem.COLOR_TEXT_SECONDARY}; font-size: {DesignSystem.FONT_SIZE_XS}px; line-height: 100%;")
            text_layout.addWidget(desc_label)
            
            item_layout.addLayout(text_layout)
            layout.addWidget(item_widget)
            
        return frame
