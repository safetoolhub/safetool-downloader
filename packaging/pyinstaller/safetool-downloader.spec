# -*- mode: python ; coding: utf-8 -*-
# SafeTool Downloader Packaging
# Copyright (C) 2026 safetoolhub.org
# License: GPL-3.0-or-later
#
# PyInstaller spec file for SafeTool Downloader desktop application.
# Supports Linux, Windows and macOS from a single spec file.

import os
import sys
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────
ROOT = Path(SPECPATH).parent.parent          # repo root (two levels up)
VERSION = os.environ.get("APP_VERSION", "0.1.0")

# ── Data files ───────────────────────────────────────────────────────────────
datas = [
    (str(ROOT / "assets"),  "assets"),
    (str(ROOT / "LICENSE"), "."),
    (str(ROOT / "config.py"), "."),
]

# ── Hidden imports ───────────────────────────────────────────────────────────
hidden_imports = [
    # PySide6
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "PySide6.QtSvg",
    "PySide6.QtSvgWidgets",
    # HTTP / scraping
    "requests",
    "bs4",
    "lxml",
    "lxml.etree",
    "lxml.html",
    # Icons
    "qtawesome",
    # Top-level modules
    "config",
    # Desktop package
    "safetool_downloader_desktop",
    "safetool_downloader_desktop.app",
    "safetool_downloader_desktop.config",
    "safetool_downloader_desktop.main_window",
    "safetool_downloader_desktop.settings",
    "safetool_downloader_desktop.styles",
    "safetool_downloader_desktop.styles.design_system",
    "safetool_downloader_desktop.styles.icons",
    "safetool_downloader_desktop.dialogs",
    "safetool_downloader_desktop.dialogs.about_dialog",
    "safetool_downloader_desktop.dialogs.base_dialog",
    "safetool_downloader_desktop.dialogs.settings_dialog",
    "safetool_downloader_desktop.widgets",
    "safetool_downloader_desktop.widgets.url_input_widget",
    "safetool_downloader_desktop.widgets.file_preview_table",
    "safetool_downloader_desktop.workers",
    "safetool_downloader_desktop.workers.scanner_worker",
    "safetool_downloader_desktop.workers.download_worker",
    # Standard library extras
    "json",
    "logging.handlers",
]

# ── Excludes ─────────────────────────────────────────────────────────────────
excludes = [
    "tkinter",
    "test",
    "tests",
]

# ── Analysis ─────────────────────────────────────────────────────────────────
a = Analysis(
    [str(ROOT / "safetool_downloader_desktop" / "app.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

# ── Platform-specific output ─────────────────────────────────────────────────
if sys.platform == "darwin":
    # ── macOS: .app bundle ───────────────────────────────────────────────────
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name="SafeToolDownloader",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,
        disable_windowed_traceback=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=str(ROOT / "assets" / "icon.icns") if (ROOT / "assets" / "icon.icns").exists() else None,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name="SafeToolDownloader",
    )
    app = BUNDLE(
        coll,
        name="SafeToolDownloader.app",
        icon=str(ROOT / "assets" / "icon.icns") if (ROOT / "assets" / "icon.icns").exists() else None,
        bundle_identifier="org.safetoolhub.safetooldownloader",
        version=VERSION,
        info_plist={
            "NSHighResolutionCapable": True,
            "NSPrincipalClass": "NSApplication",
            "CFBundleShortVersionString": VERSION,
        },
    )

elif sys.platform == "win32":
    # ── Windows: directory build (Inno Setup wraps it) ───────────────────────
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name="safetool-downloader-desktop",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,
        disable_windowed_traceback=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=str(ROOT / "assets" / "icon.ico"),
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name="safetool-downloader",
    )

else:
    # ── Linux: directory build (dpkg/rpm/AppImage wrap it) ───────────────────
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name="safetool-downloader-desktop",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,
        disable_windowed_traceback=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=str(ROOT / "assets" / "icon.png"),
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name="safetool-downloader",
    )
