# This file is part of SafeTool Downloader, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture()
def tmp_output(tmp_path: Path) -> Path:
    """Temporary output directory for each test."""
    out = tmp_path / "output"
    out.mkdir()
    return out
