# This file is part of SafeTool Downloader, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Tests for config module — version metadata and helpers."""

from __future__ import annotations

import re


class TestConfig:
    """Validate config.py metadata."""

    def test_app_name(self) -> None:
        from config import APP_NAME

        assert APP_NAME == "SafeTool Downloader"

    def test_app_version_format(self) -> None:
        from config import APP_VERSION

        assert re.match(r"^\d+\.\d+\.\d+$", APP_VERSION)

    def test_app_version_suffix_is_string(self) -> None:
        from config import APP_VERSION_SUFFIX

        assert isinstance(APP_VERSION_SUFFIX, str)

    def test_get_full_version_with_suffix(self) -> None:
        from config import APP_VERSION, APP_VERSION_SUFFIX, get_full_version

        full = get_full_version()
        if APP_VERSION_SUFFIX:
            assert full == f"{APP_VERSION}-{APP_VERSION_SUFFIX}"
        else:
            assert full == APP_VERSION

    def test_required_fields_exist(self) -> None:
        from config import (
            APP_AUTHOR,
            APP_CONTACT,
            APP_DESCRIPTION,
            APP_LICENSE,
            APP_NAME,
            APP_REPO,
            APP_VERSION,
            APP_WEBSITE,
        )

        for field in [APP_AUTHOR, APP_CONTACT, APP_DESCRIPTION, APP_LICENSE,
                      APP_NAME, APP_REPO, APP_VERSION, APP_WEBSITE]:
            assert isinstance(field, str)
            assert len(field) > 0
