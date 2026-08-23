# This file is part of SafeTool Downloader, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Centralized logging configuration for SafeTool Downloader."""

from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path

from safetool_downloader_desktop.settings import load_setting, ENABLE_LOGGING

_LOG_DIR = Path.home() / "logs"
_LOG_PREFIX = "safetool-downloader"


def setup_logging() -> None:
    """Configure application logging based on user settings.

    Always logs to console (stderr).  When the user has enabled logging in
    Settings, an additional file handler writes to ``~/logs/``.
    """
    root_logger = logging.getLogger("safetool_downloader_desktop")
    root_logger.setLevel(logging.DEBUG)

    # Prevent duplicate handlers on repeated calls (e.g. tests)
    if root_logger.handlers:
        return

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)-8s [%(name)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    # Console handler — always active
    console = logging.StreamHandler(sys.stderr)
    console.setLevel(logging.DEBUG)
    console.setFormatter(formatter)
    root_logger.addHandler(console)

    # File handler — only when the user opted in via Settings
    is_logging_enabled = str(load_setting(ENABLE_LOGGING, False)).lower() in (
        "true",
        "1",
        "yes",
    )
    if is_logging_enabled:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        log_file = _LOG_DIR / f"{_LOG_PREFIX}_{datetime.now():%Y%m%d_%H%M%S}.log"
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_fmt = logging.Formatter(
            "%(asctime)s %(levelname)-8s [%(name)s] %(message)s"
        )
        file_handler.setFormatter(file_fmt)
        root_logger.addHandler(file_handler)
        root_logger.info("File logging enabled → %s", log_file)
