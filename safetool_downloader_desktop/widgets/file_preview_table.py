# This file is part of SafeTool Downloader, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""File preview table — shows found files in a hierarchal tree with checkboxes, and download progress."""

from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse, unquote

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from safetool_downloader_desktop.styles.design_system import DesignSystem
from safetool_downloader_desktop.styles.icons import icon_manager
from safetool_downloader_desktop.i18n import tr

# Map extensions to icon names
_EXT_ICON_MAP: dict[str, str] = {
    ".pdf": "file-pdf",
    ".jpg": "file-image", ".jpeg": "file-image", ".png": "file-image",
    ".gif": "file-image", ".webp": "file-image", ".svg": "file-image",
    ".bmp": "file-image", ".ico": "file-image", ".tiff": "file-image",
    ".mp3": "file-music", ".wav": "file-music", ".flac": "file-music",
    ".ogg": "file-music", ".aac": "file-music", ".wma": "file-music",
    ".m4a": "file-music",
    ".mp4": "file-video", ".avi": "file-video", ".mkv": "file-video",
    ".webm": "file-video", ".mov": "file-video", ".wmv": "file-video",
    ".flv": "file-video", ".m4v": "file-video",
    ".doc": "file-document", ".docx": "file-document",
    ".xls": "file-document", ".xlsx": "file-document",
    ".ppt": "file-document", ".pptx": "file-document",
    ".odt": "file-document", ".ods": "file-document",
    ".odp": "file-document", ".rtf": "file-document",
    ".txt": "file-document", ".csv": "file-document",
    ".zip": "file-archive", ".rar": "file-archive", ".7z": "file-archive",
    ".tar": "file-archive", ".gz": "file-archive", ".bz2": "file-archive",
    ".xz": "file-archive", ".tar.gz": "file-archive", ".tar.bz2": "file-archive",
    ".py": "file-code", ".js": "file-code", ".html": "file-code",
    ".css": "file-code", ".json": "file-code", ".xml": "file-code",
    ".yaml": "file-code", ".yml": "file-code", ".sh": "file-code",
    ".bat": "file-code",
    ".exe": "file-executable", ".msi": "file-executable",
    ".dmg": "file-executable", ".pkg": "file-executable",
    ".deb": "file-executable", ".rpm": "file-executable",
    ".appimage": "file-executable", ".apk": "file-executable",
    ".run": "file-executable", ".bin": "file-executable",
    ".iso": "file-disk-image", ".img": "file-disk-image",
    ".ova": "file-disk-image", ".ovf": "file-disk-image",
    ".vmdk": "file-disk-image", ".vdi": "file-disk-image",
    ".vhd": "file-disk-image", ".vhdx": "file-disk-image",
    ".qcow2": "file-disk-image",
}


def _format_size(size_bytes: int, approx: bool = False) -> str:
    """Format byte size to human-readable string.

    When *approx* is True a ``~`` prefix is prepended to signal that the value
    was declared by the source (e.g. RSS ``<enclosure length>``) and may differ
    from the actual downloaded size (CDN transcoding, redirects, etc.).
    """
    if size_bytes < 0:
        return "—"
    if size_bytes < 1024:
        s = f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        s = f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        s = f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        s = f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
    return f"~{s}" if approx else s


def _compute_relative_dir(file_url: str, base_url: str) -> str:
    """Compute relative directory path from base_url for structured display.

    Mirrors ``download_worker._resolve_output_path`` so the tree preview
    matches the actual filesystem layout.  Returns empty string for files
    outside base_url (e.g. CDN-hosted podcast files on a different domain).
    """
    parsed_url = urlparse(file_url)
    parsed_base = urlparse(base_url)

    file_path = unquote(parsed_url.path)
    base_path = unquote(parsed_base.path)
    if not base_path.endswith("/"):
        base_path += "/"

    if not file_path.startswith(base_path):
        return ""

    rel = file_path[len(base_path):]
    parts = [p for p in rel.split("/") if p]
    if len(parts) > 1:
        return "/".join(parts[:-1])  # directory components only
    return ""


# Column indices for the QTreeWidget
_COL_NAME = 0
_COL_TYPE = 1
_COL_SIZE = 2
_COL_STATUS = 3  # download progress — hidden until download mode
_COL_DATE = 4    # RSS pub_date — hidden until RSS mode
_COL_DURATION = 5  # RSS duration — hidden until RSS mode


def _parse_duration_secs(duration_str: str) -> int:
    """Convert a duration string (HH:MM:SS, MM:SS, or integer seconds) to seconds.

    Returns -1 when the string is empty or cannot be parsed (so unknown
    durations sort uniformly to one end rather than raising an error).
    """
    if not duration_str:
        return -1
    if ":" in duration_str:
        parts = duration_str.split(":")
        try:
            if len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            if len(parts) == 2:
                return int(parts[0]) * 60 + int(parts[1])
        except (ValueError, IndexError):
            return -1
        return -1
    try:
        return int(duration_str)
    except ValueError:
        return -1


class _SortableTreeItem(QTreeWidgetItem):
    """QTreeWidgetItem with numeric-aware comparison for size and duration columns.

    Qt calls ``__lt__`` during sort.  Calling ``treeWidget().sortColumn()``
    inside ``__lt__`` triggers a PySide6 recursion bug, so the active sort
    column is stored in a class-level variable and kept in sync by
    ``FilePreviewTable._on_sort_indicator_changed()``.
    """

    _sort_col: int = -1  # updated by FilePreviewTable via sortIndicatorChanged

    def __lt__(self, other: QTreeWidgetItem) -> bool:  # noqa: D105
        col = _SortableTreeItem._sort_col
        if col == _COL_SIZE:
            my_val = self.data(_COL_SIZE, Qt.ItemDataRole.UserRole)
            other_val = other.data(_COL_SIZE, Qt.ItemDataRole.UserRole)
            if my_val is not None and other_val is not None:
                return int(my_val) < int(other_val)
        elif col == _COL_DURATION:
            my_val = self.data(_COL_DURATION, Qt.ItemDataRole.UserRole)
            other_val = other.data(_COL_DURATION, Qt.ItemDataRole.UserRole)
            if my_val is not None and other_val is not None:
                return int(my_val) < int(other_val)
        # Default: plain text comparison — safe, does not re-trigger sort
        safe_col = max(col, 0)
        return self.text(safe_col) < other.text(safe_col)


def _format_duration(duration_str: str) -> str:
    """Normalise an itunes:duration value for compact display.

    Handles ``HH:MM:SS``, ``MM:SS``, and plain-integer seconds.
    """
    if not duration_str:
        return ""
    if ":" in duration_str:
        return duration_str
    try:
        secs = int(duration_str)
        h = secs // 3600
        m = (secs % 3600) // 60
        s = secs % 60
        if h > 0:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m}:{s:02d}"
    except ValueError:
        return duration_str


def _parse_rss_date(date_str: str) -> datetime | None:
    """Parse an RFC 2822 or ISO-8601 date string; returns None on failure."""
    if not date_str:
        return None
    try:
        return parsedate_to_datetime(date_str)
    except Exception:
        pass
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except Exception:
        return None


def _format_rss_date(date_str: str) -> str:
    """Format an RSS date string as ``YYYY-MM-DD`` for compact display."""
    dt = _parse_rss_date(date_str)
    if dt is None:
        return date_str[:20] if len(date_str) > 20 else date_str
    return dt.strftime("%Y-%m-%d")


class _DownloadProgressWidget(QWidget):
    """Widget to show download progress inside the QTreeWidget."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 0, 8, 0)
        self._progress = QProgressBar()
        self._progress.setFixedHeight(8)
        self._progress.setTextVisible(False)
        self._progress.setStyleSheet(DesignSystem.get_progressbar_style())
        
        self._status = QLabel(tr("file_table.waiting"))
        self._status.setFixedWidth(120)
        self._status.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        self._status.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_XS}px;"
            f" color: {DesignSystem.COLOR_TEXT_SECONDARY};"
        )
        
        layout.addWidget(self._progress, 1)
        layout.addWidget(self._status)

    def set_progress(self, percent: int, downloaded: int) -> None:
        if percent >= 0:
            self._progress.setRange(0, 100)
            self._progress.setValue(percent)
            self._status.setText(f"{_format_size(downloaded)} ({percent}%)")
        else:
            self._progress.setRange(0, 0)
            self._status.setText(f"{_format_size(downloaded)}")

    def set_complete(self) -> None:
        self._progress.setRange(0, 100)
        self._progress.setValue(100)
        self._status.setText(tr("file_table.complete"))
        self._status.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_XS}px;"
            f" color: {DesignSystem.COLOR_SUCCESS}; font-weight: bold;"
        )
        
    def set_skipped(self) -> None:
        self._progress.setRange(0, 100)
        self._progress.setValue(100)
        self._status.setText(tr("file_table.skipped"))
        self._status.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_XS}px;"
            f" color: {DesignSystem.COLOR_TEXT_SECONDARY}; font-weight: bold;"
        )
        
    def set_error(self, message: str) -> None:
        _HTTP_ERROR_LABELS: dict[str, str] = {
            "401": "file_table.error_401",
            "403": "file_table.error_403",
            "404": "file_table.error_404",
            "410": "file_table.error_410",
            "429": "file_table.error_429",
            "500": "file_table.error_500",
            "502": "file_table.error_502",
            "503": "file_table.error_503",
        }
        label_key = "file_table.error"
        tooltip = message
        if message.startswith("HTTP_"):
            parts = message.split(":", 1)
            code = parts[0][len("HTTP_"):]
            label_key = _HTTP_ERROR_LABELS.get(code, "file_table.error")
            tooltip = parts[1].strip() if len(parts) > 1 else message
        self._progress.setValue(0)
        self._status.setText(tr(label_key))
        self._status.setToolTip(tooltip)
        self._status.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_XS}px;"
            f" color: {DesignSystem.COLOR_DANGER}; font-weight: bold;"
        )


class FilePreviewTable(QWidget):
    """Table displaying found files in a hierarchy with selection controls and download progress.

    Signals:
        selection_changed(list): List of selected file info dicts.
    """

    selection_changed = Signal(list)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._all_files: list[dict] = []
        self._scan_base_url: str = ""
        self._preserve_structure: bool = True
        self._active_filter_extensions: list[str] = []
        self._download_mode = False
        self._rss_mode = False
        self._rss_date_filter_days: int | None = None
        
        # Maps file items so we can update them inside the tree
        self._file_items: list[tuple[QTreeWidgetItem, dict]] = []
        self._selected_indices: list[QTreeWidgetItem] = []
        
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Container card
        self._container = QFrame()
        self._container.setStyleSheet(DesignSystem.get_table_container_style())
        container_layout = QVBoxLayout(self._container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        # ── Tree ──────────────────────────────────────────────────────
        self._tree = QTreeWidget()
        self._tree.setHeaderLabels([
            tr("file_table.col_file_folder"),
            tr("file_table.col_type"),
            tr("file_table.col_size"),
            tr("file_table.col_status"),
            tr("file_table.col_date"),
            tr("file_table.col_duration"),
        ])
        self._tree.setColumnWidth(_COL_NAME, 360)
        self._tree.setColumnWidth(_COL_TYPE, 80)
        self._tree.setColumnWidth(_COL_SIZE, 100)
        self._tree.hideColumn(_COL_STATUS)    # Hide status until download
        self._tree.hideColumn(_COL_DATE)      # Hide date until RSS mode
        self._tree.hideColumn(_COL_DURATION)  # Hide duration until RSS mode
        self._tree.setAlternatingRowColors(True)
        
        self._tree.setStyleSheet(
            f"QTreeWidget {{"
            f"  background-color: {DesignSystem.COLOR_SURFACE};"
            f"  border: none;"
            f"  font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f"  color: {DesignSystem.COLOR_TEXT};"
            f"  outline: none;"
            f"}}"
            f"QTreeWidget::item {{"
            f"  height: 28px;"
            f"  padding: 2px;"
            f"}}"
            f"QTreeWidget::item:selected {{"
            f"  background-color: {DesignSystem.COLOR_SECONDARY_LIGHT};"
            f"  color: {DesignSystem.COLOR_TEXT};"
            f"}}"
            f"QHeaderView::section {{"
            f"  background-color: {DesignSystem.COLOR_SECONDARY_LIGHT};"
            f"  color: {DesignSystem.COLOR_TEXT_SECONDARY};"
            f"  padding: 8px 12px;"
            f"  border: none;"
            f"  border-bottom: 2px solid {DesignSystem.COLOR_BORDER_LIGHT};"
            f"  font-weight: {DesignSystem.FONT_WEIGHT_BOLD};"
            f"  font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f"  text-align: left;"
            f"}}"
        )
        
        # Status header stays centered visually as its content (progress bar) usually is.
        self._tree.headerItem().setTextAlignment(_COL_STATUS, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)

        
        # Connect before setSortingEnabled so _on_sort_indicator_changed fires
        # before Qt's internal _q_sort slot, keeping _SortableTreeItem._sort_col
        # up to date before any __lt__ comparisons begin.
        self._tree.header().sortIndicatorChanged.connect(self._on_sort_indicator_changed)
        self._tree.setSortingEnabled(True)
        self._tree.itemChanged.connect(self._on_item_changed)
        self._tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._show_context_menu)
        container_layout.addWidget(self._tree, 1)

        # ── Summary bar ───────────────────────────────────────────────
        self._summary = QFrame()
        self._summary.setStyleSheet(DesignSystem.get_table_summary_style())
        summary_outer = QVBoxLayout(self._summary)
        summary_outer.setContentsMargins(16, 8, 16, 8)
        summary_outer.setSpacing(DesignSystem.SPACE_8)

        # Row 1: summary label + action buttons
        summary_layout = QHBoxLayout()
        summary_layout.setSpacing(DesignSystem.SPACE_12)

        self._summary_label = QLabel(tr("file_table.no_files_found"))
        self._summary_label.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f" font-weight: {DesignSystem.FONT_WEIGHT_BOLD};"
            f" color: {DesignSystem.COLOR_TEXT};"
            f" border: none; background: transparent;"
        )
        summary_layout.addWidget(self._summary_label)
        summary_layout.addStretch()

        # RSS: Export CSV button (hidden until RSS mode)
        self._btn_export_csv = QPushButton(tr("file_table.rss_export_csv"))
        self._btn_export_csv.setStyleSheet(DesignSystem.get_secondary_button_style())
        self._btn_export_csv.clicked.connect(self._export_csv)
        self._btn_export_csv.setVisible(False)
        summary_layout.addWidget(self._btn_export_csv)

        # RSS: Select N latest controls (hidden until RSS mode)
        _lbl_style = (
            f"font-size: {DesignSystem.FONT_SIZE_XS}px;"
            f" color: {DesignSystem.COLOR_TEXT_SECONDARY};"
            f" border: none; background: transparent;"
        )
        self._rss_n_label = QLabel(tr("file_table.rss_select_n"))
        self._rss_n_label.setStyleSheet(_lbl_style)
        self._rss_n_label.setVisible(False)
        summary_layout.addWidget(self._rss_n_label)

        self._rss_n_spinbox = QSpinBox()
        self._rss_n_spinbox.setRange(1, 9999)
        self._rss_n_spinbox.setValue(10)
        self._rss_n_spinbox.setFixedWidth(60)
        self._rss_n_spinbox.setStyleSheet(
            f"QSpinBox {{"
            f"  font-size: {DesignSystem.FONT_SIZE_XS}px;"
            f"  border: 1px solid {DesignSystem.COLOR_BORDER_LIGHT};"
            f"  border-radius: 4px;"
            f"  padding: 2px 4px;"
            f"  background: {DesignSystem.COLOR_SURFACE};"
            f"  color: {DesignSystem.COLOR_TEXT};"
            f"}}"
        )
        self._rss_n_spinbox.setVisible(False)
        summary_layout.addWidget(self._rss_n_spinbox)

        self._rss_n_btn = QPushButton(tr("file_table.rss_apply_n"))
        self._rss_n_btn.setStyleSheet(DesignSystem.get_secondary_button_style())
        self._rss_n_btn.clicked.connect(lambda: self._select_n_latest(self._rss_n_spinbox.value()))
        self._rss_n_btn.setVisible(False)
        summary_layout.addWidget(self._rss_n_btn)

        # Action buttons
        btn_all = QPushButton(tr("file_table.select_all"))
        btn_all.setStyleSheet(DesignSystem.get_secondary_button_style())
        btn_all.clicked.connect(lambda: self._set_all_checked(True))
        summary_layout.addWidget(btn_all)

        btn_none = QPushButton(tr("file_table.deselect_all"))
        btn_none.setStyleSheet(DesignSystem.get_secondary_button_style())
        btn_none.clicked.connect(lambda: self._set_all_checked(False))
        summary_layout.addWidget(btn_none)

        summary_outer.addLayout(summary_layout)

        container_layout.addWidget(self._summary)
        layout.addWidget(self._container)

    # ── Public API ────────────────────────────────────────────────────

    def set_files(self, files: list[dict], base_url: str = "", preserve_structure: bool = True) -> None:
        """Populate the table with found files.

        Args:
            files: List of file info dicts from the scanner.
            base_url: The original scan URL (used to compute relative paths).
            preserve_structure: Whether to show directory hierarchy or flat list.
        """
        self._all_files = files
        self._scan_base_url = base_url
        self._preserve_structure = preserve_structure
        self._download_mode = False
        # Reset RSS mode on each new scan
        self._rss_mode = False
        self._rss_date_filter_days = None
        self._tree.hideColumn(_COL_DATE)
        self._tree.hideColumn(_COL_DURATION)
        self._btn_export_csv.setVisible(False)
        self._rss_n_label.setVisible(False)
        self._rss_n_spinbox.setVisible(False)
        self._rss_n_btn.setVisible(False)
        self._tree.setColumnWidth(_COL_NAME, 360)
        # Reset sort to discovery order for each fresh scan; setSortIndicator
        # emits sortIndicatorChanged which updates _SortableTreeItem._sort_col.
        self._tree.header().setSortIndicator(-1, Qt.SortOrder.AscendingOrder)
        self._rebuild_tree()

    def set_preserve_structure(self, preserve: bool) -> None:
        """Toggle between flat and structured file view, preserving checked state."""
        if preserve == self._preserve_structure:
            return
        # Save checked state by file index
        checked_indices: set[int] = set()
        for item, _ in self._file_items:
            idx = item.data(0, Qt.ItemDataRole.UserRole)
            if idx is not None and item.checkState(0) == Qt.CheckState.Checked:
                checked_indices.add(idx)
        self._preserve_structure = preserve
        self._rebuild_tree(checked_indices)
        # Reapply active extension filter
        if self._active_filter_extensions:
            self.filter_by_extensions(self._active_filter_extensions)

    def _rebuild_tree(self, checked_indices: set[int] | None = None) -> None:
        """Build/rebuild the tree from stored file list.

        Args:
            checked_indices: File indices to check. ``None`` = check all.
        """
        files = self._all_files
        self._tree.setSortingEnabled(False)  # prevent auto-sort during item insertion
        self._tree.clear()
        self._file_items.clear()
        self._selected_indices.clear()
        self._tree.hideColumn(3)
        self._summary.setVisible(True)

        folders: dict[str, QTreeWidgetItem] = {}

        self._tree.blockSignals(True)

        for idx, file_info in enumerate(files):
            # Compute relative directory for structured display
            if self._preserve_structure and self._scan_base_url:
                rel_dir = _compute_relative_dir(file_info.get("url", ""), self._scan_base_url)
            else:
                rel_dir = ""

            parent_item = self._tree.invisibleRootItem()
            if rel_dir:
                parts = [p for p in rel_dir.split("/") if p]
                current_path = ""
                for part in parts:
                    current_path += "/" + part
                    if current_path not in folders:
                        folder_item = _SortableTreeItem()
                        folder_item.setText(0, " " + part)  # padding
                        folder_item.setIcon(0, icon_manager.get_icon("folder-tree", color=DesignSystem.COLOR_PRIMARY))
                        folder_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsSelectable)
                        folder_item.setCheckState(0, Qt.CheckState.Checked)
                        
                        # Apply folder styling (bold)
                        font = folder_item.font(0)
                        font.setBold(True)
                        folder_item.setFont(0, font)

                        parent_item.addChild(folder_item)
                        folders[current_path] = folder_item
                    parent_item = folders[current_path]

            file_item = _SortableTreeItem(parent_item)
            file_item.setText(0, " " + file_info.get("filename", "unknown"))
            ext = file_info.get("extension", "")
            icon_name = _EXT_ICON_MAP.get(ext, "file-unknown")
            file_item.setIcon(0, icon_manager.get_icon(icon_name, color=DesignSystem.COLOR_PRIMARY))
            
            # Type and Size
            file_item.setText(_COL_TYPE, ext.upper().lstrip(".") if ext else "?")
            raw_size = file_info.get("size_hint", -1)
            file_item.setText(_COL_SIZE, _format_size(
                raw_size,
                approx=file_info.get("size_hint_approx", False),
            ))
            # Store raw byte count so _SortableTreeItem can sort numerically
            file_item.setData(_COL_SIZE, Qt.ItemDataRole.UserRole, raw_size)

            # RSS metadata columns (populated even when hidden)
            meta = file_info.get("meta") or {}
            if meta.get("rss_date"):
                file_item.setText(_COL_DATE, _format_rss_date(meta["rss_date"]))
                file_item.setForeground(_COL_DATE, Qt.GlobalColor.gray)
            rss_duration_raw = meta.get("rss_duration", "")
            if rss_duration_raw:
                file_item.setText(_COL_DURATION, _format_duration(rss_duration_raw))
                file_item.setForeground(_COL_DURATION, Qt.GlobalColor.gray)
            # Store duration in seconds so _SortableTreeItem can sort numerically
            file_item.setData(_COL_DURATION, Qt.ItemDataRole.UserRole, _parse_duration_secs(rss_duration_raw))
            
            # Styling for secondary columns
            file_item.setForeground(_COL_TYPE, Qt.GlobalColor.gray)
            file_item.setForeground(_COL_SIZE, Qt.GlobalColor.gray)
            
            file_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsSelectable)

            # Restore or default checked state
            if checked_indices is None or idx in checked_indices:
                file_item.setCheckState(0, Qt.CheckState.Checked)
            else:
                file_item.setCheckState(0, Qt.CheckState.Unchecked)
            
            # Set UserRole to identify as a 'file' (vs folder)
            file_item.setData(0, Qt.ItemDataRole.UserRole, idx)
            self._file_items.append((file_item, file_info))

        self._tree.expandAll()
        self._tree.blockSignals(False)

        # Sync folder check states when there are folders
        if folders:
            self._sync_tree_check_states()

        self._tree.setSortingEnabled(True)  # re-enable; re-sorts if indicator is active
        self._update_summary()

    def get_selected_files(self) -> list[dict]:
        """Return list of selected file info dicts (filtered + checked only)."""
        return [
            file_info
            for item, file_info in self._file_items
            if not item.isHidden() and item.checkState(0) == Qt.CheckState.Checked
        ]

    def clear(self) -> None:
        """Remove all items."""
        self._tree.clear()
        self._file_items.clear()
        self._all_files.clear()
        self._download_mode = False
        self._update_summary()

    def refresh_summary(self) -> None:
        """Re-compute and display the summary (call after table becomes visible)."""
        self._update_summary()

    def filter_by_extensions(self, extensions: list[str]) -> None:
        """Show/hide rows based on file extensions. Empty = show all."""
        self._active_filter_extensions = extensions
        self._reapply_visibility()

    def filter_rss_by_date(self, days: int | None) -> None:
        """Show/hide RSS episodes by publication age.

        *days* is the maximum age in days (e.g. 30 for last month).
        Pass ``None`` to remove the date filter.
        """
        self._rss_date_filter_days = days
        self._reapply_visibility()

    def set_rss_mode(self, is_rss: bool) -> None:
        """Switch the table into (or out of) RSS/podcast display mode.

        In RSS mode, the Date and Duration columns become visible and the
        RSS-specific filter controls are shown in the summary bar.
        """
        self._rss_mode = is_rss
        if is_rss:
            self._tree.showColumn(_COL_DATE)
            self._tree.showColumn(_COL_DURATION)
            self._tree.setColumnWidth(_COL_NAME, 260)
            self._tree.setColumnWidth(_COL_DATE, 90)
            self._tree.setColumnWidth(_COL_DURATION, 70)
            self._btn_export_csv.setVisible(True)
            self._rss_n_label.setVisible(True)
            self._rss_n_spinbox.setVisible(True)
            self._rss_n_btn.setVisible(True)
            self._rss_date_filter_days = None
        else:
            self._tree.hideColumn(_COL_DATE)
            self._tree.hideColumn(_COL_DURATION)
            self._tree.setColumnWidth(_COL_NAME, 360)
            self._btn_export_csv.setVisible(False)
            self._rss_n_label.setVisible(False)
            self._rss_n_spinbox.setVisible(False)
            self._rss_n_btn.setVisible(False)
            self._rss_date_filter_days = None

    def _reapply_visibility(self) -> None:
        """Apply both extension filter and RSS date filter to all items."""
        ext_set = set(self._active_filter_extensions) if self._active_filter_extensions else None

        cutoff: datetime | None = None
        if self._rss_date_filter_days is not None:
            cutoff = datetime.now(tz=timezone.utc) - timedelta(days=self._rss_date_filter_days)

        self._tree.blockSignals(True)

        for item, file_info in self._file_items:
            ext_ok = ext_set is None or file_info.get("extension", "") in ext_set
            date_ok = self._item_passes_date_filter(file_info, cutoff)
            item.setHidden(not (ext_ok and date_ok))

        # Update folder visibility recursively
        def update_folder(node: QTreeWidgetItem) -> bool:
            has_visible = False
            for i in range(node.childCount()):
                child = node.child(i)
                if child.data(0, Qt.ItemDataRole.UserRole) is None:
                    child_visible = update_folder(child)
                    child.setHidden(not child_visible)
                    if child_visible:
                        has_visible = True
                else:
                    if not child.isHidden():
                        has_visible = True
            return has_visible

        root = self._tree.invisibleRootItem()
        for i in range(root.childCount()):
            child = root.child(i)
            if child.data(0, Qt.ItemDataRole.UserRole) is None:
                is_visible = update_folder(child)
                child.setHidden(not is_visible)

        self._sync_tree_check_states()
        self._tree.blockSignals(False)
        self._update_summary()

    @staticmethod
    def _item_passes_date_filter(file_info: dict, cutoff: datetime | None) -> bool:
        """Return True if *file_info* should be shown given *cutoff* date."""
        if cutoff is None:
            return True
        meta = file_info.get("meta") or {}
        date_str = meta.get("rss_date", "")
        if not date_str:
            return True  # no date info → always include
        dt = _parse_rss_date(date_str)
        if dt is None:
            return True  # unparseable → include
        if dt.tzinfo is None:
            # Make offset-naive cutoff for comparison
            return dt >= cutoff.replace(tzinfo=None)
        return dt >= cutoff

    def _select_n_latest(self, n: int) -> None:
        """Uncheck all visible items and check the *n* most-recent episodes."""
        if n <= 0:
            return

        visible_items = [
            (item, info)
            for item, info in self._file_items
            if not item.isHidden()
        ]

        def _sort_key(x: tuple) -> datetime:
            meta = x[1].get("meta") or {}
            dt = _parse_rss_date(meta.get("rss_date", ""))
            if dt is None:
                return datetime.min.replace(tzinfo=timezone.utc)
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt

        visible_items.sort(key=_sort_key, reverse=True)

        self._tree.blockSignals(True)
        for i, (item, _) in enumerate(visible_items):
            item.setCheckState(0, Qt.CheckState.Checked if i < n else Qt.CheckState.Unchecked)
        self._sync_tree_check_states()
        self._tree.blockSignals(False)
        self._update_summary()

    def _export_csv(self) -> None:
        """Export visible episodes with full metadata to a CSV file."""
        path, _ = QFileDialog.getSaveFileName(
            self,
            tr("file_table.rss_csv_save_title"),
            "",
            tr("file_table.rss_csv_filter"),
        )
        if not path:
            return

        with open(path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(["Title", "Date", "Duration", "Size", "URL", "Description"])
            for item, file_info in self._file_items:
                if item.isHidden():
                    continue
                meta = file_info.get("meta") or {}
                writer.writerow([
                    meta.get("rss_title", file_info.get("filename", "")),
                    meta.get("rss_date", ""),
                    meta.get("rss_duration", ""),
                    _format_size(
                        file_info.get("size_hint", -1),
                        approx=file_info.get("size_hint_approx", False),
                    ),
                    file_info.get("url", ""),
                    meta.get("rss_description", ""),
                ])

    # ── Download mode API ─────────────────────────────────────────────

    def start_download_mode(self) -> None:
        """Switch table to download progress mode — only show selected rows."""
        self._download_mode = True
        self._selected_indices = []
        self._summary.setVisible(False)
        self._tree.setSortingEnabled(False)  # order must stay stable during download
        self._tree.showColumn(_COL_STATUS)
        # Hide RSS metadata columns during download to keep the view clean
        if self._rss_mode:
            self._tree.hideColumn(_COL_DATE)
            self._tree.hideColumn(_COL_DURATION)

        self._tree.blockSignals(True)
        
        # Hide unselected and setup progress widgets for selected
        for item, file_info in self._file_items:
            if not item.isHidden() and item.checkState(0) == Qt.CheckState.Checked:
                pw = _DownloadProgressWidget()
                self._tree.setItemWidget(item, _COL_STATUS, pw)
                self._selected_indices.append(item)
                item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable) # disable checkable
            else:
                item.setHidden(True)
                item.setCheckState(0, Qt.CheckState.Unchecked)

        # Update folder visibility to hide empty ones
        def hide_empty_folders(node: QTreeWidgetItem) -> bool:
            has_visible = False
            for i in range(node.childCount()):
                child = node.child(i)
                if child.data(0, Qt.ItemDataRole.UserRole) is None:
                    child_visible = hide_empty_folders(child)
                    if not child_visible:
                        child.setHidden(True)
                    else:
                        has_visible = True
                else:
                    if not child.isHidden():
                        has_visible = True
            return has_visible

        root = self._tree.invisibleRootItem()
        for i in range(root.childCount()):
            child = root.child(i)
            if child.data(0, Qt.ItemDataRole.UserRole) is None:
                is_visible = hide_empty_folders(child)
                child.setHidden(not is_visible)
                # Keep folder uncheckable during download
                child.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)

        self._tree.expandAll()
        self._tree.blockSignals(False)

    def _get_progress_widget(self, index: int) -> _DownloadProgressWidget | None:
        if 0 <= index < len(self._selected_indices):
            item = self._selected_indices[index]
            widget = self._tree.itemWidget(item, _COL_STATUS)
            if isinstance(widget, _DownloadProgressWidget):
                return widget
        return None

    def update_download_progress(self, index: int, percent: int, downloaded: int) -> None:
        """Update progress for file at download-order index."""
        pw = self._get_progress_widget(index)
        if pw:
            pw.set_progress(percent, downloaded)

    def set_download_complete(self, index: int, path: str) -> None:
        pw = self._get_progress_widget(index)
        if pw:
            pw.set_complete()

    def set_download_skipped(self, index: int, path: str) -> None:
        pw = self._get_progress_widget(index)
        if pw:
            pw.set_skipped()

    def set_download_error(self, index: int, error: str) -> None:
        pw = self._get_progress_widget(index)
        if pw:
            pw.set_error(error)

    def exit_download_mode(self) -> None:
        """Restore table to preview/selection mode (called on cancel)."""
        if not self._download_mode:
            return
        self._download_mode = False
        self._summary.setVisible(True)
        self._tree.hideColumn(_COL_STATUS)
        # Restore RSS metadata columns if in RSS mode
        if self._rss_mode:
            self._tree.showColumn(_COL_DATE)
            self._tree.showColumn(_COL_DURATION)
        
        self._tree.blockSignals(True)
        # Restore flags and clean widgets
        for item, _ in self._file_items:
            self._tree.removeItemWidget(item, _COL_STATUS)
            item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsSelectable)
            
        def restore_folders(node: QTreeWidgetItem):
            for i in range(node.childCount()):
                child = node.child(i)
                if child.data(0, Qt.ItemDataRole.UserRole) is None:
                    child.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsSelectable)
                    restore_folders(child)
                    
        restore_folders(self._tree.invisibleRootItem())
        
        # NOTE: Caller typically calls filter_by_extensions after this, which restores visibility.
        self._tree.blockSignals(False)
        self._tree.setSortingEnabled(True)  # restore interactive header sorting

    # ── Private ───────────────────────────────────────────────────────

    def _on_sort_indicator_changed(self, col: int, _order: Qt.SortOrder) -> None:
        """Keep _SortableTreeItem._sort_col in sync with the active sort column.

        This slot is connected *before* Qt's internal _q_sort slot so that the
        class variable is updated before any __lt__ comparisons are triggered.
        """
        _SortableTreeItem._sort_col = col

    def _show_context_menu(self, pos) -> None:
        item = self._tree.itemAt(pos)
        if item is None:
            return
            
        # Only show copy URL for files
        if item.data(0, Qt.ItemDataRole.UserRole) is not None:
            idx = item.data(0, Qt.ItemDataRole.UserRole)
            file_info = self._all_files[idx]
            menu = QMenu(self)
            copy_action = QAction(tr("file_table.copy_full_url"), self)
            copy_action.triggered.connect(lambda: self._copy_url(file_info.get("url", "")))
            menu.addAction(copy_action)
            menu.exec(self._tree.mapToGlobal(pos))

    def _copy_url(self, url: str) -> None:
        if url:
            QApplication.clipboard().setText(url)

    def _on_item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        if column != 0:
            return
            
        self._tree.blockSignals(True)
        check_state = item.checkState(0)
        
        # Cascade down to all children
        def cascade_check(node: QTreeWidgetItem, state: Qt.CheckState):
            for i in range(node.childCount()):
                child = node.child(i)
                if not child.isHidden():
                    child.setCheckState(0, state)
                    cascade_check(child, state)
                
        cascade_check(item, check_state)
        
        # Cascade up to update parents
        self._sync_tree_check_states()

        self._tree.blockSignals(False)
        self._update_summary()

    def _sync_tree_check_states(self) -> None:
        """Syncs all folder check states based on visible children."""
        def sync_node(node: QTreeWidgetItem) -> Qt.CheckState:
            checked_count = 0
            unchecked_count = 0
            visible_children = 0
            
            for i in range(node.childCount()):
                child = node.child(i)
                if child.isHidden():
                    continue
                    
                visible_children += 1
                if child.data(0, Qt.ItemDataRole.UserRole) is None:
                    child_state = sync_node(child)
                else:
                    child_state = child.checkState(0)
                    
                if child_state == Qt.CheckState.Checked:
                    checked_count += 1
                elif child_state == Qt.CheckState.Unchecked:
                    unchecked_count += 1
                    
            if visible_children == 0:
                return Qt.CheckState.Unchecked
                
            if checked_count == visible_children:
                state = Qt.CheckState.Checked
            elif unchecked_count == visible_children:
                state = Qt.CheckState.Unchecked
            else:
                state = Qt.CheckState.PartiallyChecked
                
            node.setCheckState(0, state)
            return state

        root = self._tree.invisibleRootItem()
        for i in range(root.childCount()):
            child = root.child(i)
            if child.data(0, Qt.ItemDataRole.UserRole) is None and not child.isHidden():
                sync_node(child)

    def _set_all_checked(self, checked: bool) -> None:
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        self._tree.blockSignals(True)
        
        def set_all(node: QTreeWidgetItem):
            for i in range(node.childCount()):
                child = node.child(i)
                if not child.isHidden():
                    child.setCheckState(0, state)
                    set_all(child)
        
        set_all(self._tree.invisibleRootItem())
                
        self._tree.blockSignals(False)
        self._update_summary()

    def _update_summary(self) -> None:
        total = len(self._all_files)
        visible_files = [
            (item, info) for item, info in self._file_items if not item.isHidden()
        ]
        selected_files = [
            info for item, info in visible_files if item.checkState(0) == Qt.CheckState.Checked
        ]
        visible = len(visible_files)
        sel_count = len(selected_files)

        # Sum sizes of selected files
        total_bytes = sum(
            info.get("size_hint", -1) for info in selected_files if info.get("size_hint", -1) > 0
        )
        any_approx = any(
            info.get("size_hint_approx", False)
            for info in selected_files
            if info.get("size_hint", -1) > 0
        )
        size_str = f"  ({_format_size(total_bytes, approx=any_approx)})" if total_bytes > 0 else ""

        if total == 0:
            self._summary_label.setText(tr("file_table.no_files_found"))
        elif visible < total:
            self._summary_label.setText(
                tr("file_table.summary_filtered", sel_count=sel_count, visible=visible, size=size_str, total=total)
            )
        else:
            self._summary_label.setText(
                tr("file_table.summary_all", sel_count=sel_count, total=total, size=size_str)
            )

        self.selection_changed.emit(self.get_selected_files())
