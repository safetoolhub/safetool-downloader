# This file is part of SafeTool Downloader, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Tests for settings module."""

from __future__ import annotations


class TestSettings:
    """Settings module helper functions."""

    def test_get_output_dir_returns_string(self) -> None:
        from safetool_downloader_desktop.settings import get_output_dir

        result = get_output_dir()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_is_recursive_enabled_returns_bool(self) -> None:
        from safetool_downloader_desktop.settings import is_recursive_enabled

        result = is_recursive_enabled()
        assert isinstance(result, bool)

    def test_get_recursive_max_depth_returns_int(self) -> None:
        from safetool_downloader_desktop.settings import get_recursive_max_depth

        result = get_recursive_max_depth()
        assert isinstance(result, int)
        assert result >= 0

    def test_save_and_load_setting(self) -> None:
        from safetool_downloader_desktop.settings import load_setting, save_setting

        key = "_test_key_ci"
        save_setting(key, "test_value")
        result = load_setting(key, "default")
        assert result == "test_value"
        # Clean up
        save_setting(key, "")
