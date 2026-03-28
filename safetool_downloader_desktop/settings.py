# This file is part of SafeTool Downloader, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Persistent user preferences via QSettings."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings

from config import APP_NAME, APP_AUTHOR

_ORG = "safetoolhub.org"
_APP = APP_NAME


def get_settings() -> QSettings:
    """Return the application QSettings instance."""
    return QSettings(_ORG, _APP)


def save_setting(key: str, value: object) -> None:
    s = get_settings()
    s.setValue(key, value)


def load_setting(key: str, default: object = None) -> object:
    s = get_settings()
    return s.value(key, default)


# ── Convenience keys ──────────────────────────────────────────────────
LAST_URL = "last_url"
LAST_OUTPUT_DIR = "last_output_dir"
CONCURRENT_DOWNLOADS = "concurrent_downloads"
DEFAULT_FILE_TYPES = "default_file_types"
ENABLE_LOGGING = "enable_logging"

# Recursive crawling
RECURSIVE_ENABLED = "recursive_enabled"
RECURSIVE_MAX_DEPTH = "recursive_max_depth"
RECURSIVE_DELAY = "recursive_delay"
RECURSIVE_MAX_PAGES = "recursive_max_pages"


def get_output_dir() -> str:
    """Return the last used output directory or the user's Downloads folder."""
    saved = load_setting(LAST_OUTPUT_DIR)
    if saved and Path(str(saved)).is_dir():
        return str(saved)
    downloads = Path.home() / "Downloads"
    if downloads.is_dir():
        return str(downloads)
    return str(Path.home())


def get_concurrent_downloads() -> int:
    """Return the max concurrent downloads setting (default 3)."""
    val = load_setting(CONCURRENT_DOWNLOADS, 3)
    try:
        return max(1, min(10, int(val)))
    except (TypeError, ValueError):
        return 3


def is_recursive_enabled() -> bool:
    """Return whether recursive crawling is enabled by default."""
    val = load_setting(RECURSIVE_ENABLED, False)
    return str(val).lower() in ("true", "1", "yes")


def get_recursive_max_depth() -> int:
    """Return the default max depth for recursive crawling."""
    val = load_setting(RECURSIVE_MAX_DEPTH, 1)
    try:
        return max(0, min(5, int(val)))
    except (TypeError, ValueError):
        return 1


def get_recursive_delay() -> float:
    """Return delay between page requests in seconds."""
    val = load_setting(RECURSIVE_DELAY, 0.5)
    try:
        return max(0.0, min(5.0, float(val)))
    except (TypeError, ValueError):
        return 0.5


def get_recursive_max_pages() -> int:
    """Return max pages to scan during recursive crawling."""
    val = load_setting(RECURSIVE_MAX_PAGES, 100)
    try:
        return max(1, min(1000, int(val)))
    except (TypeError, ValueError):
        return 100
