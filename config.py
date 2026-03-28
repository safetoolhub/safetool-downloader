# This file is part of SafeTool Downloader, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Centralised application metadata.

Every module that needs the application name, version, author, etc.
should import from this file.  The values here are the single source
of truth.
"""

from __future__ import annotations

# ── Identity ─────────────────────────────────────────────────────────
APP_NAME: str = "SafeTool Downloader"
APP_VERSION: str = "0.1.0"
APP_VERSION_SUFFIX: str = "beta"

# ── Author / Organisation ────────────────────────────────────────────
APP_AUTHOR: str = "SafeToolHub"
APP_CONTACT: str = "safetoolhub@protonmail.com"
APP_WEBSITE: str = "https://safetoolhub.org"
APP_REPO: str = "https://github.com/safetoolhub/safetool-downloader"

# ── Description ──────────────────────────────────────────────────────
APP_DESCRIPTION: str = "Web file downloader with preview and filtering."

# ── Computed version ─────────────────────────────────────────────────
def get_full_version() -> str:
    """Return e.g. ``'0.1.0-beta'`` or ``'0.1.0'``."""
    if APP_VERSION_SUFFIX:
        return f"{APP_VERSION}-{APP_VERSION_SUFFIX}"
    return APP_VERSION

# ── Legal ────────────────────────────────────────────────────────────
APP_LICENSE: str = "GPLv3"
