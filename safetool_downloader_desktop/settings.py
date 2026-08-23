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
RECURSIVE_RESTRICT_PATH = "recursive_restrict_path"
PRESERVE_STRUCTURE = "preserve_structure"
DUPLICATE_ACTION = "duplicate_action"
LANGUAGE = "language"

# Valid values for DUPLICATE_ACTION
DUPLICATE_SKIP = "skip"
DUPLICATE_OVERWRITE = "overwrite"
DUPLICATE_RENAME = "rename"


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
    val = load_setting(RECURSIVE_MAX_DEPTH, 10)
    try:
        return max(0, min(20, int(val)))
    except (TypeError, ValueError):
        return 10


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


def is_recursive_restrict_path_enabled() -> bool:
    """Return whether recursive crawling is restricted to the base URL path (default True)."""
    val = load_setting(RECURSIVE_RESTRICT_PATH, True)
    return str(val).lower() not in ("false", "0", "no")


def is_preserve_structure_enabled() -> bool:
    """Return whether the original folder structure should be preserved on download (default True)."""
    val = load_setting(PRESERVE_STRUCTURE, True)
    return str(val).lower() not in ("false", "0", "no")


def get_duplicate_action() -> str:
    """Return what to do when a file already exists with the same size (default: skip)."""
    val = str(load_setting(DUPLICATE_ACTION, DUPLICATE_SKIP)).lower()
    if val in (DUPLICATE_SKIP, DUPLICATE_OVERWRITE, DUPLICATE_RENAME):
        return val
    return DUPLICATE_SKIP


def get_language() -> str:
    """Return the configured interface language (default: 'es')."""
    val = load_setting(LANGUAGE, "es")
    return str(val) if val else "es"


# ── URL history ───────────────────────────────────────────────────────
URL_HISTORY = "url_history"
URL_HISTORY_MAX_SIZE = 15


def get_url_history() -> list[str]:
    """Return the list of recently scanned URLs, most recent first."""
    val = load_setting(URL_HISTORY, [])
    if isinstance(val, list):
        return [str(u) for u in val if u]
    # QSettings may deserialize a single-item list as a plain string
    if isinstance(val, str) and val:
        return [val]
    return []


def add_url_to_history(url: str) -> None:
    """Add a URL to the front of the history, deduplicating and trimming to max size."""
    if not url or not url.startswith(("http://", "https://")):
        return
    history = get_url_history()
    history = [u for u in history if u != url]
    history.insert(0, url)
    save_setting(URL_HISTORY, history[:URL_HISTORY_MAX_SIZE])


def clear_url_history() -> None:
    """Clear the URL history."""
    save_setting(URL_HISTORY, [])
