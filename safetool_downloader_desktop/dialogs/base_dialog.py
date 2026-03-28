# This file is part of SafeTool Downloader, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Base dialog with common styling applied."""

from __future__ import annotations

from PySide6.QtWidgets import QDialog, QWidget

from safetool_downloader_desktop.styles.design_system import DesignSystem


class BaseDialog(QDialog):
    """Base dialog class that applies global stylesheet and background."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(
            DesignSystem.get_stylesheet()
            + f"\nQDialog {{ background-color: {DesignSystem.COLOR_BACKGROUND}; }}"
        )
