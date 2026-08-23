# This file is part of SafeTool Downloader, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Tree Analysis dialog — shows the directory tree of a completed scan."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from safetool_downloader_desktop.dialogs.base_dialog import BaseDialog
from safetool_downloader_desktop.styles.design_system import DesignSystem
from safetool_downloader_desktop.styles.icons import icon_manager
from safetool_downloader_desktop.i18n import tr


class TreeAnalysisDialog(BaseDialog):
    """Modal dialog that displays the scan directory tree with file-type counts.

    Parameters
    ----------
    report:
        Pre-built text report from ``build_directory_tree_report()``.
    base_url:
        The root URL that was scanned (used for the default save filename).
    """

    def __init__(self, report: str, base_url: str, parent=None) -> None:
        super().__init__(parent)
        self._report = report
        self._base_url = base_url
        self.setWindowTitle(tr("tree_dialog.title"))
        self.setMinimumSize(760, 520)
        self.resize(960, 640)
        self.setModal(True)
        self._build_ui()

    # ── UI construction ───────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(DesignSystem.SPACE_16)
        layout.setContentsMargins(
            DesignSystem.SPACE_24,
            DesignSystem.SPACE_20,
            DesignSystem.SPACE_24,
            DesignSystem.SPACE_20,
        )

        # ── Header ────────────────────────────────────────────────────
        header_row = QHBoxLayout()
        header_row.setSpacing(DesignSystem.SPACE_8)

        icon_lbl = QLabel()
        icon_manager.set_label_icon(
            icon_lbl, "folder-tree",
            color=DesignSystem.COLOR_PRIMARY, size=22,
        )
        header_row.addWidget(icon_lbl)

        title_lbl = QLabel(tr("tree_dialog.title"))
        title_lbl.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_LG}px;"
            f" font-weight: {DesignSystem.FONT_WEIGHT_BOLD};"
            f" color: {DesignSystem.COLOR_TEXT};"
            f" border: none; background: transparent;"
        )
        header_row.addWidget(title_lbl)
        header_row.addStretch()

        hint_lbl = QLabel(tr("tree_dialog.hint"))
        hint_lbl.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f" color: {DesignSystem.COLOR_TEXT_SECONDARY};"
            f" border: none; background: transparent;"
        )
        hint_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        header_row.addWidget(hint_lbl)
        layout.addLayout(header_row)

        # ── Text area ─────────────────────────────────────────────────
        self._text = QPlainTextEdit()
        self._text.setReadOnly(True)
        mono = QFont()
        mono.setFamilies(["Cascadia Code", "JetBrains Mono", "Fira Code",
                          "Consolas", "Courier New", "Monospace"])
        mono.setPointSize(10)
        self._text.setFont(mono)
        self._text.setStyleSheet(
            f"QPlainTextEdit {{"
            f"  background-color: {DesignSystem.COLOR_SURFACE};"
            f"  color: {DesignSystem.COLOR_TEXT};"
            f"  border: 1px solid {DesignSystem.COLOR_BORDER_LIGHT};"
            f"  border-radius: {DesignSystem.RADIUS_BASE}px;"
            f"  padding: 8px;"
            f"}}"
        )
        self._text.setPlainText(self._report)
        layout.addWidget(self._text, 1)

        # ── Button row ────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(DesignSystem.SPACE_8)

        btn_save = QPushButton(tr("tree_dialog.save_to_file"))
        btn_save.setStyleSheet(DesignSystem.get_secondary_button_style())
        icon_manager.set_button_icon(
            btn_save, "download",
            color=DesignSystem.COLOR_TEXT_SECONDARY, size=16,
        )
        btn_save.clicked.connect(self._save_to_file)
        btn_row.addWidget(btn_save)

        btn_row.addStretch()

        btn_close = QPushButton(tr("common.close"))
        btn_close.setStyleSheet(DesignSystem.get_primary_button_style())
        btn_close.setMinimumWidth(90)
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)

        layout.addLayout(btn_row)

    # ── Actions ───────────────────────────────────────────────────────

    def _save_to_file(self) -> None:
        from urllib.parse import urlparse
        url_path = urlparse(self._base_url).path.strip("/").replace("/", "_") or "scan"
        default_name = f"tree_analysis_{url_path}.txt"
        path, _ = QFileDialog.getSaveFileName(
            self,
            tr("tree_dialog.save_dialog_title"),
            str(Path.home() / "Downloads" / default_name),
            tr("tree_dialog.save_filter"),
        )
        if path:
            Path(path).write_text(self._report, encoding="utf-8")
