# This file is part of SafeTool Downloader, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Application entry point — creates QApplication, applies styling, launches MainWindow."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QPalette
from PySide6.QtWidgets import QApplication

from safetool_downloader_desktop.styles.design_system import DesignSystem


def _create_light_palette() -> QPalette:
    """Create a light palette matching the DesignSystem tokens."""
    p = QPalette()
    p.setColor(QPalette.ColorRole.Window, QColor(DesignSystem.COLOR_BACKGROUND))
    p.setColor(QPalette.ColorRole.WindowText, QColor(DesignSystem.COLOR_TEXT))
    p.setColor(QPalette.ColorRole.Base, QColor(DesignSystem.COLOR_SURFACE))
    p.setColor(QPalette.ColorRole.AlternateBase, QColor(DesignSystem.COLOR_BACKGROUND))
    p.setColor(QPalette.ColorRole.Text, QColor(DesignSystem.COLOR_TEXT))
    p.setColor(QPalette.ColorRole.Button, QColor(DesignSystem.COLOR_SURFACE))
    p.setColor(QPalette.ColorRole.ButtonText, QColor(DesignSystem.COLOR_TEXT))
    p.setColor(QPalette.ColorRole.Highlight, QColor(DesignSystem.COLOR_PRIMARY))
    p.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
    # Tooltips: force black background and white text for all states to fix Linux/Wayland issues
    for group in [QPalette.ColorGroup.Active, QPalette.ColorGroup.Inactive, QPalette.ColorGroup.Disabled]:
        p.setColor(group, QPalette.ColorRole.ToolTipBase, QColor("#000000"))
        p.setColor(group, QPalette.ColorRole.ToolTipText, QColor("#FFFFFF"))
    return p


def main() -> int:
    # Configure logging before anything else
    from safetool_downloader_desktop.logging_config import setup_logging

    setup_logging()

    # Initialize i18n before any UI is created
    from safetool_downloader_desktop.i18n import init_i18n
    from safetool_downloader_desktop.settings import get_language

    init_i18n(get_language())

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setPalette(_create_light_palette())
    app.setStyleSheet(DesignSystem.get_stylesheet())

    # Set application icon
    icon_path = Path(__file__).parent.parent / "assets" / "icon.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    from safetool_downloader_desktop.main_window import MainWindow

    window = MainWindow()
    window.showMaximized()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
