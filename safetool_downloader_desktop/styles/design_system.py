# This file is part of SafeTool Downloader, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Design System for SafeTool Downloader Desktop.

Centralized design system providing consistent CSS tokens and reusable
style methods. Adapted from SafeTool PDF design system for PySide6.

Existe un fallo en Linux por el cual en los tooltips se sorbreescribe la caja CSS de fondo que se 
intenta dibujar, reemplazándola por el color predeterminado genérico del sistema (el grisáceo `Window`), 
por un grave fallo del renderizador QSS en algunos entornos (muy probablemente en combinación con Wayland 
o tu gestor de ventanas actual)-
Solución definitiva: por ello, siempre que se implementen tooltips hay que eliminar completamente las 
reglas CSS del tooltip (`QToolTip { ... }`) de `DesignSystem.py` e indicarle a la aplicación 
que NO intente dibujarlo de esa manera. En su lugar, hay que configurar el entorno profundo con `QPalette` 
para forzar `ToolTipBase` a `#000000` y `ToolTipText` a `#FFFFFF`, quitar el CSS que choca y falla, 
y entonces la aplicación dibujará los tooltips 100% de forma nativa a través del sistema gráfico usando 
la configuración de paleta que impusimos.

¡IMPORTANTE!: Nunca usar texto enriquecido ni etiquetas HTML (`<b>`, `<p>`, `<br>`) en `.setToolTip()`.
Dado que Qt renderiza el HTML usando QTextDocument, esto anula la variable ToolTipBase volviendo al
bug original del fondo gris. Usar siempre texto plano con saltos de línea (`\n`).

¡MUY IMPORTANTE!: Si aplicas un estilo inline a un widget padre (`setStyleSheet(...)`), SIEMPRE
debes restringirlo a la clase (ej. `"QToolButton { border: none; }"`). Si lo dejas libre 
(`"border: none;"`), Qt aplicará ese reseteo a todos los hijos generados, incluyendo el `QToolTip`,
rompiendo la recuperación de color blanco del texto.

Esto asegura que sea el propio motor de la plataforma (libre de bugs del CSS render y QTextDocument) 
el que dibuje un tooltip negro liso y natural con texto blanco.



"""

from __future__ import annotations


class DesignSystem:
    """Centralized design system with reusable tokens and styles."""

    # ==================== COLORS ====================

    COLOR_BACKGROUND = "#F8F9FA"
    COLOR_SURFACE = "#FFFFFF"
    COLOR_TEXT = "#212529"
    COLOR_TEXT_SECONDARY = "#6C757D"
    COLOR_PRIMARY = "#0D6EFD"
    COLOR_PRIMARY_HOVER = "#0B5ED7"
    COLOR_PRIMARY_ACTIVE = "#0A58CA"
    COLOR_PRIMARY_LIGHT = "#E7F1FF"
    COLOR_PRIMARY_SUBTLE = "rgba(13, 110, 253, 0.04)"
    COLOR_PRIMARY_LIGHTER = "rgba(13, 110, 253, 0.08)"
    COLOR_TRANS_SURFACE = "rgba(255, 255, 255, 0.85)"
    COLOR_SHADOW = "rgba(0, 0, 0, 0.1)"
    COLOR_PRIMARY_TEXT = "#FFFFFF"
    COLOR_SECONDARY = "#6C757D"
    COLOR_SECONDARY_HOVER = "#5C636A"
    COLOR_SECONDARY_LIGHT = "#E9ECEF"
    COLOR_SUCCESS = "#198754"
    COLOR_SUCCESS_BG = "#D1E7DD"
    COLOR_SUCCESS_SOFT_BG = "#E6F4EA"
    COLOR_WARNING = "#FFC107"
    COLOR_WARNING_BG = "#FFF3CD"
    COLOR_WARNING_TEXT = "#664D03"
    COLOR_DANGER = "#DC3545"
    COLOR_DANGER_HOVER = "#BB2D3B"
    COLOR_DANGER_BG = "#F8D7DA"
    COLOR_INFO = "#0DCAF0"
    COLOR_INFO_BG = "#CFF4FC"
    COLOR_INFO_TEXT = "#055160"
    COLOR_BORDER = "#DEE2E6"
    COLOR_BORDER_LIGHT = "#E9ECEF"
    COLOR_CARD_BORDER = "#DEE2E6"

    # ==================== TYPOGRAPHY ====================

    FONT_FAMILY_BASE = "'Segoe UI', 'Roboto', 'Helvetica Neue', sans-serif"
    FONT_FAMILY_MONO = "'Consolas', 'Monaco', monospace"
    FONT_SIZE_XS = 11
    FONT_SIZE_SM = 13
    FONT_SIZE_BASE = 14
    FONT_SIZE_MD = 16
    FONT_SIZE_LG = 18
    FONT_SIZE_XL = 24
    FONT_SIZE_2XL = 32
    FONT_WEIGHT_NORMAL = 400
    FONT_WEIGHT_MEDIUM = 500
    FONT_WEIGHT_SEMIBOLD = 600
    FONT_WEIGHT_BOLD = 700

    # ==================== SPACING ====================

    SPACE_2 = 2
    SPACE_4 = 4
    SPACE_6 = 6
    SPACE_8 = 8
    SPACE_10 = 10
    SPACE_12 = 12
    SPACE_16 = 16
    SPACE_20 = 20
    SPACE_24 = 24
    SPACE_32 = 32
    SPACE_40 = 40
    SPACE_48 = 48

    # ==================== BORDER RADIUS ====================

    RADIUS_SM = 4
    RADIUS_BASE = 6
    RADIUS_MD = 8
    RADIUS_LG = 12
    RADIUS_XL = 16
    RADIUS_FULL = 9999

    # ==================== DIMENSIONS ====================

    WINDOW_MIN_WIDTH = 1050
    WINDOW_MIN_HEIGHT = 780
    HEADER_HEIGHT = 50

    # ==================== HELPERS ====================

    @staticmethod
    def _get_button_disabled_style() -> str:
        return f"""
            QPushButton:disabled {{
                background-color: {DesignSystem.COLOR_SECONDARY_LIGHT};
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
                border: 1px solid {DesignSystem.COLOR_BORDER};
            }}
        """

    # ==================== GLOBAL STYLESHEET ====================

    @staticmethod
    def get_stylesheet() -> str:
        return f"""
            * {{ font-family: {DesignSystem.FONT_FAMILY_BASE}; }}
            QMainWindow {{ background-color: {DesignSystem.COLOR_BACKGROUND}; }}
            
            /* Tooltips are now fully driven by QPalette in app.py to avoid 
               Linux/Wayland compositor background-clipping bugs */
        """

    # ==================== HEADER ====================

    @staticmethod
    def get_header_style() -> str:
        return f"""
            QFrame#headerCard {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {DesignSystem.COLOR_SURFACE},
                    stop:1 {DesignSystem.COLOR_BACKGROUND});
                border: 1px solid {DesignSystem.COLOR_BORDER_LIGHT};
                border-radius: {DesignSystem.RADIUS_LG}px;
                padding: {DesignSystem.SPACE_12}px {DesignSystem.SPACE_20}px;
            }}
        """

    @staticmethod
    def get_header_title_style() -> str:
        return (
            f"font-size: {DesignSystem.FONT_SIZE_XL}px;"
            f" font-weight: {DesignSystem.FONT_WEIGHT_BOLD};"
            f" color: {DesignSystem.COLOR_TEXT};"
        )

    @staticmethod
    def get_header_icon_container_style() -> str:
        return (
            f"background-color: {DesignSystem.COLOR_PRIMARY_LIGHT};"
            f" border-radius: {DesignSystem.RADIUS_MD}px;"
            f" border: 1px solid {DesignSystem.COLOR_BORDER_LIGHT};"
        )

    @staticmethod
    def get_header_brand_label_style() -> str:
        return (
            f"font-size: {DesignSystem.FONT_SIZE_XS}px;"
            f" font-weight: {DesignSystem.FONT_WEIGHT_BOLD};"
            f" color: {DesignSystem.COLOR_PRIMARY};"
            f" text-transform: uppercase; letter-spacing: 1px;"
            f" border: none; background: transparent;"
        )

    # ==================== MAIN BUTTONS ====================

    @staticmethod
    def get_primary_button_style() -> str:
        return f"""
            QPushButton {{
                background-color: {DesignSystem.COLOR_PRIMARY};
                color: {DesignSystem.COLOR_PRIMARY_TEXT};
                border: none; border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: {DesignSystem.SPACE_12}px {DesignSystem.SPACE_24}px;
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
                font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
                min-height: 36px;
            }}
            QPushButton:hover {{ background-color: {DesignSystem.COLOR_PRIMARY_HOVER}; }}
            QPushButton:pressed {{ background-color: {DesignSystem.COLOR_PRIMARY_ACTIVE}; }}
        """ + DesignSystem._get_button_disabled_style()

    @staticmethod
    def get_secondary_button_style() -> str:
        return f"""
            QPushButton {{
                background-color: {DesignSystem.COLOR_SURFACE};
                color: {DesignSystem.COLOR_TEXT};
                border: 1px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: {DesignSystem.SPACE_12}px {DesignSystem.SPACE_24}px;
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
                font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
                min-height: 36px;
            }}
            QPushButton:hover {{
                background-color: {DesignSystem.COLOR_SECONDARY_LIGHT};
                border-color: {DesignSystem.COLOR_TEXT_SECONDARY};
            }}
        """ + DesignSystem._get_button_disabled_style()

    @staticmethod
    def get_danger_button_style() -> str:
        return f"""
            QPushButton {{
                background-color: {DesignSystem.COLOR_DANGER};
                color: {DesignSystem.COLOR_PRIMARY_TEXT};
                border: none; border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: {DesignSystem.SPACE_12}px {DesignSystem.SPACE_24}px;
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
                font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
                min-height: 36px;
            }}
            QPushButton:hover {{ background-color: {DesignSystem.COLOR_DANGER_HOVER}; }}
        """ + DesignSystem._get_button_disabled_style()

    @staticmethod
    def get_icon_button_style() -> str:
        return (
            f"QToolButton {{ background: transparent; border: none;"
            f" border-radius: {DesignSystem.RADIUS_BASE}px; padding: 4px; }}"
            f" QToolButton:hover {{ background-color: rgba(0, 0, 0, 0.05); }}"
            f" QToolButton:pressed {{ background-color: rgba(0, 0, 0, 0.1); }}"
        )

    # ==================== CARDS ====================

    @staticmethod
    def get_card_style() -> str:
        return (
            f"QFrame {{ background-color: {DesignSystem.COLOR_SURFACE};"
            f" border: 1px solid {DesignSystem.COLOR_CARD_BORDER};"
            f" border-radius: {DesignSystem.RADIUS_LG}px; padding: 16px; }}"
        )

    # ==================== URL INPUT BAR ====================

    @staticmethod
    def get_url_input_style() -> str:
        return f"""
            QLineEdit {{
                border: 2px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_MD}px;
                padding: 10px 14px;
                font-size: {DesignSystem.FONT_SIZE_MD}px;
                color: {DesignSystem.COLOR_TEXT};
                background-color: {DesignSystem.COLOR_SURFACE};
            }}
            QLineEdit:focus {{
                border-color: {DesignSystem.COLOR_PRIMARY};
            }}
            QLineEdit:hover {{
                border-color: {DesignSystem.COLOR_PRIMARY_HOVER};
            }}
        """

    @staticmethod
    def get_url_combo_style() -> str:
        """Style for the editable URL history QComboBox."""
        return (
            f"QComboBox {{"
            f" border: 2px solid {DesignSystem.COLOR_BORDER};"
            f" border-radius: {DesignSystem.RADIUS_MD}px;"
            f" padding: 2px 2px 2px 12px;"
            f" font-size: {DesignSystem.FONT_SIZE_MD}px;"
            f" color: {DesignSystem.COLOR_TEXT};"
            f" background-color: {DesignSystem.COLOR_SURFACE};"
            f" min-height: 40px;"
            f"}}"
            f" QComboBox:hover {{ border-color: {DesignSystem.COLOR_PRIMARY_HOVER}; }}"
            f" QComboBox QLineEdit {{"
            f" border: none; background: transparent; padding: 0; margin: 0;"
            f" font-size: {DesignSystem.FONT_SIZE_MD}px;"
            f" color: {DesignSystem.COLOR_TEXT};"
            f"}}"
            f" QComboBox::drop-down {{ border: none; width: 28px; }}"
            f" QComboBox::down-arrow {{"
            f" image: none;"
            f" width: 0px; height: 0px;"
            f" border-left: 5px solid transparent;"
            f" border-right: 5px solid transparent;"
            f" border-top: 6px solid {DesignSystem.COLOR_TEXT_SECONDARY};"
            f" margin-right: 10px;"
            f"}}"
            f" QComboBox QAbstractItemView {{"
            f" border: 1px solid {DesignSystem.COLOR_BORDER};"
            f" background-color: {DesignSystem.COLOR_SURFACE};"
            f" color: {DesignSystem.COLOR_TEXT};"
            f" selection-background-color: {DesignSystem.COLOR_PRIMARY_SUBTLE};"
            f" selection-color: {DesignSystem.COLOR_TEXT};"
            f" font-size: {DesignSystem.FONT_SIZE_BASE}px;"
            f" outline: none;"
            f"}}"
        )

    @staticmethod
    def get_scan_button_style() -> str:
        return f"""
            QPushButton {{
                background-color: {DesignSystem.COLOR_PRIMARY};
                color: {DesignSystem.COLOR_PRIMARY_TEXT};
                border: none;
                border-radius: {DesignSystem.RADIUS_MD}px;
                padding: 10px 24px;
                font-size: {DesignSystem.FONT_SIZE_MD}px;
                font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
                min-height: 40px;
                min-width: 120px;
            }}
            QPushButton:hover {{ background-color: {DesignSystem.COLOR_PRIMARY_HOVER}; }}
            QPushButton:pressed {{ background-color: {DesignSystem.COLOR_PRIMARY_ACTIVE}; }}
        """ + DesignSystem._get_button_disabled_style()

    # ==================== FILE TYPE FILTER CHIPS ====================

    @staticmethod
    def get_filter_chip_style(active: bool = False) -> str:
        if active:
            return f"""
                QPushButton {{
                    background-color: {DesignSystem.COLOR_PRIMARY};
                    color: {DesignSystem.COLOR_PRIMARY_TEXT};
                    border: 1px solid {DesignSystem.COLOR_PRIMARY};
                    border-radius: {DesignSystem.RADIUS_FULL}px;
                    padding: 3px 12px;
                    font-size: {DesignSystem.FONT_SIZE_XS}px;
                    font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
                }}
                QPushButton:hover {{
                    background-color: {DesignSystem.COLOR_PRIMARY_HOVER};
                }}
            """
        return f"""
            QPushButton {{
                background-color: {DesignSystem.COLOR_SURFACE};
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
                border: 1px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_FULL}px;
                padding: 3px 12px;
                font-size: {DesignSystem.FONT_SIZE_XS}px;
                font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
            }}
            QPushButton:hover {{
                background-color: {DesignSystem.COLOR_PRIMARY_LIGHT};
                border-color: {DesignSystem.COLOR_PRIMARY};
                color: {DesignSystem.COLOR_PRIMARY};
            }}
        """

    # ==================== FILE PREVIEW TABLE ====================

    @staticmethod
    def get_table_container_style() -> str:
        return (
            f"QFrame {{ background-color: {DesignSystem.COLOR_SURFACE};"
            f" border: 1px solid {DesignSystem.COLOR_BORDER};"
            f" border-radius: {DesignSystem.RADIUS_LG}px; }}"
        )

    @staticmethod
    def get_table_header_style() -> str:
        return (
            f"QFrame {{ background-color: {DesignSystem.COLOR_BACKGROUND};"
            f" border-bottom: 2px solid {DesignSystem.COLOR_BORDER};"
            f" border-top-left-radius: {DesignSystem.RADIUS_LG}px;"
            f" border-top-right-radius: {DesignSystem.RADIUS_LG}px; }}"
        )

    @staticmethod
    def get_table_header_cell_style() -> str:
        return (
            f"font-size: {DesignSystem.FONT_SIZE_XS}px;"
            f" font-weight: {DesignSystem.FONT_WEIGHT_BOLD};"
            f" color: {DesignSystem.COLOR_TEXT_SECONDARY};"
            f" text-transform: uppercase; letter-spacing: 0.5px;"
            f" border: none; background: transparent;"
        )

    @staticmethod
    def get_table_row_style(even: bool = True) -> str:
        bg = DesignSystem.COLOR_SURFACE if even else DesignSystem.COLOR_BACKGROUND
        return (
            f"QFrame {{ background-color: {bg};"
            f" border-bottom: 1px solid {DesignSystem.COLOR_BORDER_LIGHT}; }}"
        )

    @staticmethod
    def get_table_row_text_style() -> str:
        return (
            f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f" color: {DesignSystem.COLOR_TEXT};"
            f" border: none; background: transparent;"
        )

    @staticmethod
    def get_table_summary_style() -> str:
        return (
            f"QFrame {{ background-color: {DesignSystem.COLOR_PRIMARY_LIGHT};"
            f" border-top: 2px solid {DesignSystem.COLOR_PRIMARY};"
            f" border-bottom-left-radius: {DesignSystem.RADIUS_LG}px;"
            f" border-bottom-right-radius: {DesignSystem.RADIUS_LG}px; }}"
        )

    # ==================== DOWNLOAD PROGRESS ====================

    @staticmethod
    def get_progressbar_style() -> str:
        return (
            f"QProgressBar {{ border: none;"
            f" border-radius: {DesignSystem.RADIUS_SM}px;"
            f" background-color: {DesignSystem.COLOR_SECONDARY_LIGHT};"
            f" text-align: center; height: 8px; }}"
            f" QProgressBar::chunk {{ background: qlineargradient("
            f"x1:0, y1:0, x2:1, y2:0,"
            f" stop:0 {DesignSystem.COLOR_PRIMARY},"
            f" stop:1 {DesignSystem.COLOR_PRIMARY_HOVER});"
            f" border-radius: {DesignSystem.RADIUS_SM}px; }}"
        )

    @staticmethod
    def get_progress_row_style(status: str = "waiting") -> str:
        if status == "complete":
            bg = DesignSystem.COLOR_SUCCESS_SOFT_BG
        elif status == "error":
            bg = DesignSystem.COLOR_DANGER_BG
        elif status == "downloading":
            bg = DesignSystem.COLOR_PRIMARY_LIGHT
        elif status == "skipped":
            bg = DesignSystem.COLOR_BACKGROUND
        else:
            bg = DesignSystem.COLOR_SURFACE
        return (
            f"QFrame {{ background-color: {bg};"
            f" border-bottom: 1px solid {DesignSystem.COLOR_BORDER_LIGHT}; }}"
        )

    # ==================== FORMS ====================

    @staticmethod
    def get_line_edit_style() -> str:
        return (
            f"QLineEdit {{ border: 1px solid {DesignSystem.COLOR_BORDER};"
            f" border-radius: {DesignSystem.RADIUS_BASE}px; padding: 8px;"
            f" font-size: {DesignSystem.FONT_SIZE_BASE}px;"
            f" color: {DesignSystem.COLOR_TEXT};"
            f" background-color: {DesignSystem.COLOR_SURFACE}; }}"
            f" QLineEdit:focus {{ border-color: {DesignSystem.COLOR_PRIMARY}; }}"
        )

    @staticmethod
    def get_combobox_style() -> str:
        return (
            f"QComboBox {{ border: 1px solid {DesignSystem.COLOR_BORDER};"
            f" border-radius: {DesignSystem.RADIUS_BASE}px; padding: 6px 10px;"
            f" background-color: {DesignSystem.COLOR_SURFACE};"
            f" color: {DesignSystem.COLOR_TEXT};"
            f" font-size: {DesignSystem.FONT_SIZE_BASE}px; min-height: 36px; }}"
            f" QComboBox:hover {{ border-color: {DesignSystem.COLOR_PRIMARY}; }}"
            f" QComboBox::drop-down {{ border: none; width: 30px; }}"
            f" QComboBox::down-arrow {{ image: none;"
            f" border-left: 5px solid transparent;"
            f" border-right: 5px solid transparent;"
            f" border-top: 5px solid {DesignSystem.COLOR_TEXT_SECONDARY};"
            f" margin-right: 10px; }}"
        )

    @staticmethod
    def get_spinbox_style() -> str:
        return (
            f"QAbstractSpinBox {{ border: 1px solid {DesignSystem.COLOR_BORDER};"
            f" border-radius: {DesignSystem.RADIUS_BASE}px; padding: 6px 8px;"
            f" background-color: {DesignSystem.COLOR_SURFACE};"
            f" color: {DesignSystem.COLOR_TEXT};"
            f" font-size: {DesignSystem.FONT_SIZE_BASE}px; min-height: 36px; }}"
            f" QAbstractSpinBox:hover {{ border-color: {DesignSystem.COLOR_PRIMARY}; }}"
            f" QAbstractSpinBox::up-button {{ subcontrol-origin: border;"
            f" subcontrol-position: top right; width: 20px;"
            f" border-left: 1px solid {DesignSystem.COLOR_BORDER};"
            f" border-bottom: 1px solid {DesignSystem.COLOR_BORDER};"
            f" border-top-right-radius: {DesignSystem.RADIUS_BASE}px;"
            f" background-color: {DesignSystem.COLOR_BACKGROUND}; }}"
            f" QAbstractSpinBox::up-button:hover {{ background-color: {DesignSystem.COLOR_SECONDARY_LIGHT}; }}"
            f" QAbstractSpinBox::down-button {{ subcontrol-origin: border;"
            f" subcontrol-position: bottom right; width: 20px;"
            f" border-left: 1px solid {DesignSystem.COLOR_BORDER};"
            f" border-top: none;"
            f" border-bottom-right-radius: {DesignSystem.RADIUS_BASE}px;"
            f" background-color: {DesignSystem.COLOR_BACKGROUND}; }}"
            f" QAbstractSpinBox::down-button:hover {{ background-color: {DesignSystem.COLOR_SECONDARY_LIGHT}; }}"
            f" QAbstractSpinBox::up-arrow {{ image: none;"
            f" border-left: 4px solid transparent; border-right: 4px solid transparent;"
            f" border-bottom: 5px solid {DesignSystem.COLOR_TEXT_SECONDARY};"
            f" width: 0px; height: 0px; }}"
            f" QAbstractSpinBox::up-arrow:hover {{ border-bottom-color: {DesignSystem.COLOR_TEXT}; }}"
            f" QAbstractSpinBox::up-arrow:pressed {{ border-bottom-color: {DesignSystem.COLOR_TEXT}; }}"
            f" QAbstractSpinBox::down-arrow {{ image: none;"
            f" border-left: 4px solid transparent; border-right: 4px solid transparent;"
            f" border-top: 5px solid {DesignSystem.COLOR_TEXT_SECONDARY};"
            f" width: 0px; height: 0px; }}"
            f" QAbstractSpinBox::down-arrow:hover {{ border-top-color: {DesignSystem.COLOR_TEXT}; }}"
            f" QAbstractSpinBox::down-arrow:pressed {{ border-top-color: {DesignSystem.COLOR_TEXT}; }}"
        )

    @staticmethod
    def get_checkbox_style() -> str:
        return (
            f"QCheckBox {{ font-size: {DesignSystem.FONT_SIZE_BASE}px;"
            f" color: {DesignSystem.COLOR_TEXT}; spacing: 8px; background: transparent; }}"
            f" QCheckBox:disabled {{ color: {DesignSystem.COLOR_TEXT_SECONDARY}; }}"
            f" QCheckBox::indicator {{ width: 18px; height: 18px;"
            f" border: 2px solid {DesignSystem.COLOR_BORDER};"
            f" border-radius: 4px;"
            f" background-color: {DesignSystem.COLOR_SURFACE}; }}"
            f" QCheckBox::indicator:checked {{"
            f" background-color: {DesignSystem.COLOR_PRIMARY};"
            f" border-color: {DesignSystem.COLOR_PRIMARY}; }}"
            f" QCheckBox::indicator:hover {{"
            f" border-color: {DesignSystem.COLOR_PRIMARY}; }}"
            f" QCheckBox::indicator:disabled {{"
            f" background-color: {DesignSystem.COLOR_BORDER_LIGHT};"
            f" border-color: {DesignSystem.COLOR_BORDER}; }}"
        )

    @staticmethod
    def get_slider_style() -> str:
        return f"""
            QSlider::groove:horizontal {{
                border: 1px solid {DesignSystem.COLOR_BORDER};
                height: 6px;
                background: {DesignSystem.COLOR_SECONDARY_LIGHT};
                margin: 2px 0;
                border-radius: 3px;
            }}
            QSlider::groove:horizontal:disabled {{
                background: {DesignSystem.COLOR_BORDER_LIGHT};
                border-color: {DesignSystem.COLOR_BORDER_LIGHT};
            }}
            QSlider::handle:horizontal {{
                background: {DesignSystem.COLOR_PRIMARY};
                border: none;
                width: 16px;
                height: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }}
            QSlider::handle:horizontal:hover {{
                background: {DesignSystem.COLOR_PRIMARY_HOVER};
            }}
            QSlider::handle:horizontal:disabled {{
                background: {DesignSystem.COLOR_BORDER};
            }}
            QSlider::sub-page:horizontal {{
                background: {DesignSystem.COLOR_PRIMARY};
                border-radius: 3px;
            }}
            QSlider::sub-page:horizontal:disabled {{
                background: {DesignSystem.COLOR_BORDER};
                border-radius: 3px;
            }}
            QSlider::add-page:horizontal {{
                background: {DesignSystem.COLOR_BORDER_LIGHT};
                border-radius: 3px;
            }}
        """

    # ==================== SCROLL AREA ====================

    @staticmethod
    def get_scroll_area_style() -> str:
        return (
            f"QScrollArea {{ border: none; background-color: transparent; }}"
            f" QScrollBar:vertical {{ border: none;"
            f" background-color: {DesignSystem.COLOR_BACKGROUND};"
            f" width: 8px; border-radius: 4px; }}"
            f" QScrollBar::handle:vertical {{"
            f" background-color: {DesignSystem.COLOR_BORDER};"
            f" border-radius: 4px; min-height: 30px; }}"
            f" QScrollBar::handle:vertical:hover {{"
            f" background-color: {DesignSystem.COLOR_TEXT_SECONDARY}; }}"
            f" QScrollBar::add-line:vertical,"
            f" QScrollBar::sub-line:vertical {{ height: 0; }}"
        )

    # ==================== SETTINGS DIALOG ====================

    @staticmethod
    def get_settings_section_style() -> str:
        return (
            f"QFrame {{ background-color: {DesignSystem.COLOR_SURFACE};"
            f" border: 1px solid {DesignSystem.COLOR_CARD_BORDER};"
            f" border-radius: {DesignSystem.RADIUS_LG}px; padding: 16px; }}"
        )

    @staticmethod
    def get_settings_title_style() -> str:
        return (
            f"font-size: {DesignSystem.FONT_SIZE_MD}px;"
            f" font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};"
            f" color: {DesignSystem.COLOR_TEXT};"
            f" border: none; background: transparent;"
        )

    @staticmethod
    def get_settings_label_style() -> str:
        return (
            f"font-size: {DesignSystem.FONT_SIZE_BASE}px;"
            f" color: {DesignSystem.COLOR_TEXT};"
            f" border: none; background: transparent;"
        )

    @staticmethod
    def get_settings_note_style() -> str:
        return (
            f"QLabel {{ font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f" color: {DesignSystem.COLOR_TEXT_SECONDARY};"
            f" border: none; background: transparent; }}"
        )

    # ==================== ALERTS ====================

    @staticmethod
    def get_info_alert_style() -> str:
        return (
            f"QFrame {{ background-color: {DesignSystem.COLOR_INFO_BG};"
            f" color: {DesignSystem.COLOR_INFO_TEXT};"
            f" border: 1px solid {DesignSystem.COLOR_INFO};"
            f" border-radius: {DesignSystem.RADIUS_MD}px; }}"
            f" QLabel {{ font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f" color: {DesignSystem.COLOR_INFO_TEXT};"
            f" border: none; background: transparent; }}"
        )

    @staticmethod
    def get_warning_alert_style() -> str:
        return (
            f"QFrame {{ background-color: {DesignSystem.COLOR_WARNING_BG};"
            f" color: {DesignSystem.COLOR_WARNING_TEXT};"
            f" border: 1px solid {DesignSystem.COLOR_WARNING};"
            f" border-radius: {DesignSystem.RADIUS_MD}px; }}"
            f" QLabel {{ font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f" color: {DesignSystem.COLOR_WARNING_TEXT};"
            f" border: none; background: transparent; }}"
        )

    @staticmethod
    def get_success_alert_style() -> str:
        return (
            f"QFrame {{ background-color: {DesignSystem.COLOR_SUCCESS_BG};"
            f" color: {DesignSystem.COLOR_SUCCESS};"
            f" border: 1px solid {DesignSystem.COLOR_SUCCESS};"
            f" border-radius: {DesignSystem.RADIUS_MD}px; }}"
            f" QLabel {{ font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f" color: {DesignSystem.COLOR_SUCCESS};"
            f" border: none; background: transparent; }}"
        )

    # ==================== ABOUT / TUTORIAL DIALOG ====================

    @staticmethod
    def get_tutorial_tab_widget_style() -> str:
        return f"""
            QTabWidget::pane {{
                border: none;
                background-color: {DesignSystem.COLOR_SURFACE};
            }}
            QTabWidget::tab-bar {{ alignment: left; }}
            QTabBar {{ background-color: {DesignSystem.COLOR_BACKGROUND}; }}
            QTabBar::tab {{
                background-color: transparent;
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
                padding: {DesignSystem.SPACE_10}px {DesignSystem.SPACE_12}px;
                border: none;
                border-left: 3px solid transparent;
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
                min-width: 100px; text-align: left;
            }}
            QTabBar::tab:selected {{
                background-color: {DesignSystem.COLOR_PRIMARY_LIGHT};
                color: {DesignSystem.COLOR_PRIMARY};
                border-left: 3px solid {DesignSystem.COLOR_PRIMARY};
                font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
            }}
            QTabBar::tab:hover:!selected {{
                background-color: {DesignSystem.COLOR_SECONDARY_LIGHT};
                color: {DesignSystem.COLOR_TEXT};
            }}
        """

    @staticmethod
    def get_tutorial_scroll_area_style() -> str:
        return f"""
            QScrollArea {{ border: none; background-color: transparent; }}
            QScrollArea > QWidget > QWidget {{ background-color: transparent; }}
            QScrollBar:vertical {{
                border: none; background-color: {DesignSystem.COLOR_BACKGROUND};
                width: 8px; border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {DesignSystem.COLOR_BORDER};
                border-radius: 4px; min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {DesignSystem.COLOR_TEXT_SECONDARY};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """

    @staticmethod
    def get_about_info_card_style() -> str:
        return f"""
            QFrame {{
                background-color: {DesignSystem.COLOR_BACKGROUND};
                border: none;
                border-radius: {DesignSystem.RADIUS_MD}px;
                padding: {DesignSystem.SPACE_2}px;
            }}
            QLabel {{ background-color: transparent; }}
        """

    @staticmethod
    def get_about_info_label_style() -> str:
        return f"color: {DesignSystem.COLOR_TEXT_SECONDARY}; font-size: {DesignSystem.FONT_SIZE_XS}px;"

    @staticmethod
    def get_about_info_value_style() -> str:
        return (
            f"color: {DesignSystem.COLOR_TEXT};"
            f" font-size: {DesignSystem.FONT_SIZE_XS}px;"
            f" font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};"
        )

    @staticmethod
    def get_tutorial_section_header_style() -> str:
        return f"""
            font-size: {DesignSystem.FONT_SIZE_LG}px;
            font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
            color: {DesignSystem.COLOR_TEXT};
            padding-bottom: {DesignSystem.SPACE_8}px;
        """

    @staticmethod
    def get_tutorial_card_title_style() -> str:
        return f"""
            color: {DesignSystem.COLOR_TEXT};
            font-size: {DesignSystem.FONT_SIZE_SM}px;
            font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
        """

    @staticmethod
    def get_about_formats_text_style() -> str:
        return f"color: {DesignSystem.COLOR_TEXT}; font-size: {DesignSystem.FONT_SIZE_XS}px;"


    # ==================== RECURSIVE CRAWL STATUS ====================

    @staticmethod
    def get_crawl_status_style() -> str:
        return (
            f"QFrame {{ background-color: {DesignSystem.COLOR_INFO_BG};"
            f" border: 1px solid {DesignSystem.COLOR_INFO};"
            f" border-radius: {DesignSystem.RADIUS_MD}px;"
            f" padding: {DesignSystem.SPACE_8}px {DesignSystem.SPACE_12}px; }}"
            f" QLabel {{ color: {DesignSystem.COLOR_INFO_TEXT};"
            f" font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f" border: none; background: transparent; }}"
        )
