# This file is part of SafeTool Downloader, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""URL input widget — URL bar, scan button, file type filters, recursive controls."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from safetool_downloader_desktop.settings import (
    get_recursive_max_depth,
    is_recursive_enabled,
)
from safetool_downloader_desktop.styles.design_system import DesignSystem
from safetool_downloader_desktop.styles.icons import icon_manager
from safetool_downloader_desktop.workers.scanner_worker import FILE_EXTENSIONS


class UrlInputWidget(QWidget):
    """Widget for URL input, file type filtering, and recursive crawling controls.

    Signals:
        scan_requested(str, list, bool, int): (url, extensions, recursive, max_depth).
        scan_cancel_requested(): User clicked cancel during an active scan.
    """

    scan_requested = Signal(str, list, bool, int)
    scan_cancel_requested = Signal()
    filter_changed = Signal(list)

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

        # ── URL Card ──────────────────────────────────────────────────
        url_card = QFrame()
        url_card.setStyleSheet(DesignSystem.get_card_style())
        url_layout = QVBoxLayout(url_card)
        url_layout.setSpacing(DesignSystem.SPACE_12)

        # URL input + scan button
        input_row = QHBoxLayout()
        input_row.setSpacing(DesignSystem.SPACE_8)

        url_icon = QLabel()
        icon_manager.set_label_icon(
            url_icon, "web", color=DesignSystem.COLOR_PRIMARY, size=22
        )
        input_row.addWidget(url_icon)

        self._url_edit = QLineEdit()
        self._url_edit.setPlaceholderText("Enter website URL to scan for files...")
        self._url_edit.setStyleSheet(DesignSystem.get_url_input_style())
        self._url_edit.returnPressed.connect(self._on_scan_clicked)
        input_row.addWidget(self._url_edit, 1)

        self._btn_scan = QPushButton("Scan")
        self._btn_scan.setStyleSheet(DesignSystem.get_scan_button_style())
        icon_manager.set_button_icon(
            self._btn_scan, "magnify", color="#FFFFFF", size=18
        )
        self._btn_scan.clicked.connect(self._on_scan_clicked)
        input_row.addWidget(self._btn_scan)

        url_layout.addLayout(input_row)

        # ── Recursive controls ────────────────────────────────────────
        rec_row = QHBoxLayout()
        rec_row.setSpacing(DesignSystem.SPACE_16)

        self._rec_check = QCheckBox("Recursive scan")
        self._rec_check.setStyleSheet(DesignSystem.get_checkbox_style())
        self._rec_check.setChecked(is_recursive_enabled())
        self._rec_check.toggled.connect(self._on_recursive_toggled)
        rec_row.addWidget(self._rec_check)

        self._depth_label = QLabel("Max depth:")
        self._depth_label.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f" color: {DesignSystem.COLOR_TEXT_SECONDARY};"
            f" border: none; background: transparent;"
        )
        rec_row.addWidget(self._depth_label)

        self._depth_spin = QSpinBox()
        self._depth_spin.setRange(0, 5)
        self._depth_spin.setValue(get_recursive_max_depth())
        self._depth_spin.setStyleSheet(DesignSystem.get_spinbox_style())
        self._depth_spin.setFixedWidth(60)
        rec_row.addWidget(self._depth_spin)

        rec_row.addStretch()

        # Status label
        self._status_label = QLabel("")
        self._status_label.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f" color: {DesignSystem.COLOR_TEXT_SECONDARY};"
            f" border: none; background: transparent;"
        )
        rec_row.addWidget(self._status_label)

        url_layout.addLayout(rec_row)

        # Apply initial visibility
        self._on_recursive_toggled(self._rec_check.isChecked())

        # Scan detail label (shows current URL path during scanning)
        self._scan_detail_label = QLabel("")
        self._scan_detail_label.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_XS}px;"
            f" color: {DesignSystem.COLOR_TEXT_SECONDARY};"
            f" border: none; background: transparent;"
            f" padding-left: {DesignSystem.SPACE_4}px;"
        )
        self._scan_detail_label.setVisible(False)
        url_layout.addWidget(self._scan_detail_label)

        layout.addWidget(url_card)

        # ── File Type Filters (single line, hidden until scan completes) ──
        self._filter_row = QFrame()
        self._filter_row.setStyleSheet(DesignSystem.get_card_style())
        filter_layout = QHBoxLayout(self._filter_row)
        filter_layout.setContentsMargins(12, 8, 12, 8)
        filter_layout.setSpacing(DesignSystem.SPACE_6)

        filter_icon = QLabel()
        icon_manager.set_label_icon(
            filter_icon, "filter", color=DesignSystem.COLOR_TEXT_SECONDARY, size=16
        )
        filter_layout.addWidget(filter_icon)

        filter_title = QLabel("Filters:")
        filter_title.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f" font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};"
            f" color: {DesignSystem.COLOR_TEXT_SECONDARY};"
            f" border: none; background: transparent;"
        )
        filter_layout.addWidget(filter_title)

        # "All Files" chip
        btn_all = QPushButton("All")
        btn_all.setCheckable(True)
        btn_all.setChecked(True)
        btn_all.setStyleSheet(DesignSystem.get_filter_chip_style(active=True))
        btn_all.clicked.connect(lambda: self._on_filter_clicked("All"))
        filter_layout.addWidget(btn_all)
        self._filter_buttons["All"] = btn_all

        for category in FILE_EXTENSIONS:
            btn = QPushButton(category)
            btn.setCheckable(True)
            btn.setChecked(False)
            btn.setStyleSheet(DesignSystem.get_filter_chip_style(active=False))
            btn.clicked.connect(lambda checked, c=category: self._on_filter_clicked(c))
            filter_layout.addWidget(btn)
            self._filter_buttons[category] = btn

        filter_layout.addStretch()

        self._filter_row.setVisible(False)
        layout.addWidget(self._filter_row)

    # ── Slots ─────────────────────────────────────────────────────────

    def _on_recursive_toggled(self, checked: bool) -> None:
        self._depth_label.setVisible(checked)
        self._depth_spin.setVisible(checked)

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

    def _on_scan_clicked(self) -> None:
        if self._scanning:
            self.scan_cancel_requested.emit()
            return

        url = self._url_edit.text().strip()
        if not url:
            return
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
            self._url_edit.setText(url)

        extensions: list[str] = []

        recursive = self._rec_check.isChecked()
        max_depth = self._depth_spin.value()

        self.scan_requested.emit(url, extensions, recursive, max_depth)

    # ── Public API ────────────────────────────────────────────────────

    def set_scanning(self, scanning: bool) -> None:
        """Update UI to reflect scanning state."""
        self._scanning = scanning
        if scanning:
            self._btn_scan.setText("Cancel")
            self._btn_scan.setStyleSheet(DesignSystem.get_danger_button_style())
            icon_manager.set_button_icon(
                self._btn_scan, "stop", color="#FFFFFF", size=18
            )
            self._url_edit.setEnabled(False)
            self._rec_check.setEnabled(False)
            self._depth_spin.setEnabled(False)
            for btn in self._filter_buttons.values():
                btn.setEnabled(False)
        else:
            self._btn_scan.setText("Scan")
            self._btn_scan.setStyleSheet(DesignSystem.get_scan_button_style())
            icon_manager.set_button_icon(
                self._btn_scan, "magnify", color="#FFFFFF", size=18
            )
            self._url_edit.setEnabled(True)
            self._rec_check.setEnabled(True)
            self._depth_spin.setEnabled(True)
            for btn in self._filter_buttons.values():
                btn.setEnabled(True)
            self._scan_detail_label.setVisible(False)

    def set_scan_detail(self, text: str) -> None:
        """Show the current URL path being scanned."""
        if text:
            self._scan_detail_label.setText(f"\u21b3 {text}")
            self._scan_detail_label.setVisible(True)
        else:
            self._scan_detail_label.setVisible(False)

    def set_status(self, text: str) -> None:
        """Update the status label."""
        self._status_label.setText(text)

    def get_url(self) -> str:
        return self._url_edit.text().strip()

    def set_url(self, url: str) -> None:
        self._url_edit.setText(url)

    def show_filters(self, visible: bool) -> None:
        """Show or hide the filter chips row."""
        self._filter_row.setVisible(visible)

    def set_filters_enabled(self, enabled: bool) -> None:
        """Enable or disable all filter chips."""
        for btn in self._filter_buttons.values():
            btn.setEnabled(enabled)

    def get_active_extensions(self) -> list[str]:
        """Return the currently active file extensions for filtering."""
        if not self._active_filters:
            return []
        extensions: list[str] = []
        for cat in self._active_filters:
            extensions.extend(FILE_EXTENSIONS.get(cat, []))
        return extensions
