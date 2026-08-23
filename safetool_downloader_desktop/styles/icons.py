# This file is part of SafeTool Downloader, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Icon Manager — Centralized icon management with QtAwesome.

Provides a unified interface for Material Design icons in SafeTool Downloader.

Usage:
    from safetool_downloader_desktop.styles.icons import icon_manager

    icon_manager.set_button_icon(button, 'download', color='#2563eb', size=20)
    icon_manager.set_label_icon(label, 'web', size=16)
    icon = icon_manager.get_icon('folder-open', color='#2563eb')
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import qtawesome as qta
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QGuiApplication, QIcon, QPixmap
from PySide6.QtWidgets import QLabel, QPushButton, QToolButton


class IconManager:
    """Centralized icon manager using QtAwesome MDI6 icons."""

    ICON_MAP = {
        # Core
        "cog": "mdi6.cog-outline",
        "information": "mdi6.information-outline",
        "information-outline": "mdi6.information-outline",
        "close-circle": "mdi6.close-circle-outline",
        "check-circle": "mdi6.check-circle-outline",
        "arrow-left": "mdi6.arrow-left",
        "arrow-right": "mdi6.arrow-right",
        "close": "mdi6.close",

        # Download / Web
        "download": "mdi6.download",
        "download-multiple": "mdi6.download-multiple",
        "web": "mdi6.web",
        "rss": "mdi6.rss",
        "link": "mdi6.link-variant",
        "folder-open": "mdi6.folder-open-outline",
        "folder-download": "mdi6.folder-arrow-down",
        "folder-tree": "mdi6.file-tree-outline",
        "refresh": "mdi6.refresh",
        "cancel": "mdi6.cancel",
        "stop": "mdi6.stop-circle-outline",
        "magnify": "mdi6.magnify",
        "image": "mdi6.image-outline",
        "video": "mdi6.video-outline",
        "archive": "mdi6.archive-outline",

        # File types
        "file-pdf": "mdi6.file-pdf-box",
        "file-document": "mdi6.file-document-outline",
        "file-document-multiple": "mdi6.file-document-multiple-outline",
        "file-image": "mdi6.file-image-outline",
        "file-music": "mdi6.file-music-outline",
        "file-video": "mdi6.file-video-outline",
        "file-code": "mdi6.file-code-outline",
        "file-archive": "mdi6.zip-box-outline",
        "file-executable": "mdi6.application-cog-outline",
        "file-disk-image": "mdi6.disc",
        "file-unknown": "mdi6.file-question-outline",
        "file-text": "mdi6.text-box-outline",

        # Actions
        "select-all": "mdi6.select-all",
        "select-none": "mdi6.selection-off",
        "select-invert": "mdi6.select-inverse",
        "filter": "mdi6.filter-outline",
        "check-bold": "mdi6.check-bold",
        "eye": "mdi6.eye-outline",
        "eye-off": "mdi6.eye-off-outline",

        # Status
        "progress-clock": "mdi6.progress-clock",
        "alert-circle": "mdi6.alert-circle-outline",
        "check": "mdi6.check",
        "loading": "mdi6.loading",

        # Settings / About
        "settings": "mdi6.cog-outline",
        "wifi-off": "mdi6.wifi-off",
        "shield": "mdi6.shield-outline",
        "shield-check": "mdi6.shield-check-outline",
        "open-in-new": "mdi6.open-in-new",

        # Recursive crawling
        "sitemap": "mdi6.sitemap-outline",
        "spider-web": "mdi6.spider-web",
        "layers": "mdi6.layers-outline",
    }

    def __init__(self) -> None:
        self._cache: Dict[str, QIcon] = {}

    def get_icon(
        self,
        name: str,
        color: Optional[str] = None,
        size: Optional[int] = None,
        scale_factor: float = 1.0,
    ) -> QIcon:
        """Get a Material Design icon by logical name."""
        if name not in self.ICON_MAP:
            raise ValueError(
                f"Icon '{name}' not found. "
                f"Available: {', '.join(sorted(self.ICON_MAP.keys()))}"
            )

        cache_key = f"{name}_{color}_{size}_{scale_factor}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        icon_name = self.ICON_MAP[name]
        options: Dict[str, Any] = {}
        if color:
            options["color"] = color
        if scale_factor != 1.0:
            options["scale_factor"] = scale_factor

        icon = qta.icon(icon_name, **options)
        self._cache[cache_key] = icon
        return icon

    def set_button_icon(
        self,
        button: QPushButton | QToolButton,
        icon_name: str,
        color: Optional[str] = None,
        size: int = 16,
    ) -> None:
        """Apply icon to a QPushButton or QToolButton."""
        icon = self.get_icon(icon_name, color=color)
        button.setIcon(icon)
        button.setIconSize(QSize(size, size))

    def set_label_icon(
        self,
        label: QLabel,
        icon_name: str,
        color: Optional[str] = None,
        size: int = 16,
    ) -> None:
        """Apply icon to a QLabel via pixmap."""
        icon = self.get_icon(icon_name, color=color)

        try:
            screen = (
                label.screen()
                if hasattr(label, "screen")
                else QGuiApplication.primaryScreen()
            )
            dpr = float(screen.devicePixelRatio()) if screen is not None else 1.0
        except Exception:
            dpr = 1.0

        physical_size = QSize(max(1, int(size * dpr)), max(1, int(size * dpr)))
        pixmap = icon.pixmap(physical_size)

        if pixmap.isNull():
            pixmap = icon.pixmap(QSize(size, size))

        if not pixmap.isNull():
            try:
                logical_pixmap = pixmap.scaled(
                    QSize(size, size),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                logical_pixmap.setDevicePixelRatio(1.0)
                label.setPixmap(logical_pixmap)
            except Exception:
                label.setPixmap(pixmap)
        else:
            fallback = QPixmap(QSize(size, size))
            fallback.fill(QColor(0, 0, 0, 0))
            label.setPixmap(fallback)


# Global instance
icon_manager = IconManager()
