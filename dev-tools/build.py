# This file is part of SafeTool Downloader, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.
#!/usr/bin/env python3
"""
Build script for SafeTool Downloader.

Runs PyInstaller and then creates platform-specific installers:
  - Linux:   .deb (dpkg-deb) + .rpm (rpmbuild) + .AppImage (appimagetool)
  - Windows: Inno Setup .exe installer
  - macOS:   .dmg disk image

Usage:
    python dev-tools/build.py                  # Build for current platform
    python dev-tools/build.py --skip-installer # PyInstaller only, no packaging

Requires:
  - PyInstaller (pip install pyinstaller)
  - Linux:   dpkg-deb (pre-installed on Debian/Ubuntu), rpmbuild (rpm), appimagetool
  - Windows: Inno Setup 6 (iscc on PATH)
  - macOS:   create-dmg (brew install create-dmg)
"""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

# Windows terminals may use cp1252 — force UTF-8
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
SPEC_FILE = ROOT / "packaging" / "pyinstaller" / "safetool-downloader.spec"
DIST_DIR = ROOT / "dist"

# Import version from config (add project root to path)
sys.path.insert(0, str(ROOT))


def get_version_info() -> tuple[str, str, str]:
    """Return (version, suffix, full_version) from config."""
    from config import APP_VERSION, APP_VERSION_SUFFIX, get_full_version
    return APP_VERSION, APP_VERSION_SUFFIX, get_full_version()


def run(cmd: list[str], **kwargs) -> None:
    """Run a command, printing it first."""
    print(f"  $ {' '.join(cmd)}")
    subprocess.check_call(cmd, **kwargs)


def build_pyinstaller() -> Path:
    """Run PyInstaller and return path to the output directory."""
    print("\n══════════════════════════════════════════════════════════")
    print("  PyInstaller Build")
    print("══════════════════════════════════════════════════════════\n")

    version, suffix, full = get_version_info()
    env = os.environ.copy()
    env["APP_VERSION"] = version

    run(
        [
            sys.executable, "-m", "PyInstaller",
            "--noconfirm",
            "--clean",
            "--distpath", str(DIST_DIR),
            "--workpath", str(ROOT / "build" / "pyinstaller-work"),
            str(SPEC_FILE),
        ],
        env=env,
    )

    # Determine output directory name (must match spec COLLECT name)
    if sys.platform == "darwin":
        app_name = "SafeToolDownloader"
    elif sys.platform == "win32":
        app_name = "safetool-downloader"
    else:
        app_name = "safetool-downloader"

    output_dir = DIST_DIR / app_name
    if not output_dir.exists():
        print(f"ERROR: Expected output at {output_dir}")
        sys.exit(1)

    print(f"\n✅ PyInstaller output: {output_dir}")
    return output_dir


# ─────────────────────────────────────────────────────────────────────────────
# Linux packaging
# ─────────────────────────────────────────────────────────────────────────────

def package_linux(output_dir: Path, full_version: str) -> list[Path]:
    """Create .deb and .rpm packages using standard system tools."""
    print("\n── Linux Packaging (.deb + .rpm) ────────────────────────\n")
    artifacts: list[Path] = []
    app_name = "safetool-downloader"
    desktop_id = "org.safetoolhub.safetooldownloader"
    arch_deb = "amd64"
    arch_rpm = "x86_64"
    install_prefix = f"opt/{app_name}"

    # ── Common: prepare staging directory ──
    staging = DIST_DIR / "staging"
    if staging.exists():
        shutil.rmtree(staging)

    # Application files
    app_dest = staging / install_prefix
    shutil.copytree(output_dir, app_dest)

    # Desktop entry
    desktop_dir = staging / "usr" / "share" / "applications"
    desktop_dir.mkdir(parents=True)
    desktop_entry = textwrap.dedent(f"""\
        [Desktop Entry]
        Type=Application
        Name=SafeTool Downloader
        GenericName=Web File Downloader
        Exec=/{install_prefix}/safetool-downloader-desktop %U
        Icon={desktop_id}
        Categories=Network;FileTransfer;Utility;
        Comment=Download files from websites — scan, preview, and batch download
        Terminal=false
        StartupNotify=true
    """)
    (desktop_dir / f"{desktop_id}.desktop").write_text(desktop_entry)

    # Icon
    icon_src = ROOT / "assets" / "icon.png"
    icon_dest = staging / "usr" / "share" / "icons" / "hicolor" / "512x512" / "apps"
    icon_dest.mkdir(parents=True)
    if icon_src.exists():
        shutil.copy2(icon_src, icon_dest / f"{desktop_id}.png")

    # AppStream metainfo
    metainfo_src = ROOT / "packaging" / "linux" / "flatpak" / "org.safetoolhub.safetooldownloader.metainfo.xml"
    metainfo_dest = staging / "usr" / "share" / "metainfo"
    metainfo_dest.mkdir(parents=True)
    if metainfo_src.exists():
        shutil.copy2(metainfo_src, metainfo_dest / f"{desktop_id}.metainfo.xml")

    # Symlink in /usr/bin
    bin_dir = staging / "usr" / "bin"
    bin_dir.mkdir(parents=True)
    symlink = bin_dir / app_name
    symlink.symlink_to(f"../../{install_prefix}/safetool-downloader-desktop")

    # ── .deb via dpkg-deb ──
    dpkg_deb = shutil.which("dpkg-deb")
    if dpkg_deb:
        deb_root = DIST_DIR / "deb-build"
        if deb_root.exists():
            shutil.rmtree(deb_root)
        shutil.copytree(staging, deb_root, symlinks=True)

        debian_dir = deb_root / "DEBIAN"
        debian_dir.mkdir()
        control = textwrap.dedent(f"""\
            Package: {app_name}
            Version: {full_version}
            Section: utils
            Priority: optional
            Architecture: {arch_deb}
            Maintainer: SafeToolHub <contact@safetoolhub.org>
            Description: Web file downloader with preview and filtering
             SafeTool Downloader scans websites for downloadable files,
             shows a preview with type filters, and downloads them in
             batch with progress tracking.
            Homepage: https://safetoolhub.org
        """)
        (debian_dir / "control").write_text(control)

        # Debian copyright
        doc_dir = deb_root / "usr" / "share" / "doc" / app_name
        doc_dir.mkdir(parents=True, exist_ok=True)
        copyright_text = textwrap.dedent(f"""\
            Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
            Upstream-Name: SafeTool Downloader
            Upstream-Contact: SafeToolHub <contact@safetoolhub.org>
            Source: https://github.com/safetoolhub/safetool-downloader

            Files: *
            Copyright: 2025-2026 SafeToolHub
            License: GPL-3.0+

            License: GPL-3.0+
             This program is free software: you can redistribute it and/or modify
             it under the terms of the GNU General Public License as published by
             the Free Software Foundation, either version 3 of the License, or
             (at your option) any later version.
             .
             This program is distributed in the hope that it will be useful,
             but WITHOUT ANY WARRANTY; without even the implied warranty of
             MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
             GNU General Public License for more details.
             .
             On Debian systems, the full text of the GNU General Public License
             version 3 can be found in /usr/share/common-licenses/GPL-3.
        """)
        (doc_dir / "copyright").write_text(copyright_text)

        deb_name = f"SafeToolDownloader-{full_version}-linux-{arch_deb}.deb"
        deb_path = DIST_DIR / deb_name
        if deb_path.exists():
            deb_path.unlink()

        run([dpkg_deb, "--build", "--root-owner-group", str(deb_root), str(deb_path)])
        if deb_path.exists():
            artifacts.append(deb_path)
            print(f"✅ Deb: {deb_path}")
    else:
        print("⚠️  dpkg-deb not found, skipping .deb")

    # ── .rpm via rpmbuild ──
    rpmbuild = shutil.which("rpmbuild")
    if rpmbuild:
        rpm_topdir = DIST_DIR / "rpm-build"
        if rpm_topdir.exists():
            shutil.rmtree(rpm_topdir)
        for d in ["BUILD", "RPMS", "SOURCES", "SPECS", "SRPMS", "BUILDROOT"]:
            (rpm_topdir / d).mkdir(parents=True)

        tarball_name = f"{app_name}-{full_version}"
        tarball_src = rpm_topdir / "SOURCES" / tarball_name
        shutil.copytree(staging, tarball_src, symlinks=True)

        spec_content = textwrap.dedent(f"""\
            Name:           {app_name}
            Version:        {full_version.replace('-', '_')}
            Release:        1%{{?dist}}
            Summary:        Web file downloader with preview and filtering
            License:        GPL-3.0-or-later
            URL:            https://safetoolhub.org

            AutoReqProv:    no

            %define _build_id_links none

            %description
            SafeTool Downloader scans websites for downloadable files,
            shows a preview with type filters, and downloads them in
            batch with progress tracking.

            %install
            cp -a %{{_sourcedir}}/{tarball_name}/* %{{buildroot}}/

            %files
            /{install_prefix}/
            /usr/bin/{app_name}
            /usr/share/applications/{desktop_id}.desktop
            /usr/share/icons/hicolor/512x512/apps/{desktop_id}.png
            /usr/share/metainfo/{desktop_id}.metainfo.xml
        """)
        spec_path = rpm_topdir / "SPECS" / f"{app_name}.spec"
        spec_path.write_text(spec_content)

        try:
            run([
                rpmbuild, "-bb",
                "--define", f"_topdir {rpm_topdir}",
                str(spec_path),
            ])
            rpm_out = rpm_topdir / "RPMS" / arch_rpm
            if rpm_out.exists():
                for rpm_file in rpm_out.glob("*.rpm"):
                    dest = DIST_DIR / f"SafeToolDownloader-{full_version}-linux-{arch_rpm}.rpm"
                    shutil.move(str(rpm_file), str(dest))
                    artifacts.append(dest)
                    print(f"✅ RPM: {dest}")
        except subprocess.CalledProcessError as e:
            print(f"⚠️  rpmbuild failed: {e}")
    else:
        print("⚠️  rpmbuild not found, skipping .rpm")

    return artifacts


def package_appimage(output_dir: Path, full_version: str) -> list[Path]:
    """Create AppImage using appimagetool."""
    print("\n── AppImage Packaging ──────────────────────────────────\n")
    artifacts: list[Path] = []
    app_name = "safetool-downloader"
    desktop_id = "org.safetoolhub.safetooldownloader"

    appimagetool = shutil.which("appimagetool")
    if not appimagetool:
        candidate = Path("/usr/local/bin/appimagetool")
        if candidate.exists() and candidate.is_file():
            appimagetool = str(candidate)
    if not appimagetool:
        print("⚠️  appimagetool not found, skipping AppImage")
        return artifacts

    print(f"  Using appimagetool: {appimagetool}")

    appdir = DIST_DIR / "AppDir"
    if appdir.exists():
        shutil.rmtree(appdir)

    # Application files → AppDir/opt/safetool-downloader/
    install_dir = appdir / "opt" / app_name
    shutil.copytree(output_dir, install_dir)

    # AppRun entry point
    apprun_src = ROOT / "packaging" / "linux" / "appimage" / "AppRun"
    apprun_dst = appdir / "AppRun"
    if apprun_src.exists():
        shutil.copy2(apprun_src, apprun_dst)
    else:
        apprun_dst.write_text(textwrap.dedent(f"""\
            #!/bin/bash
            HERE="$(dirname "$(readlink -f "$0")")"
            exec "$HERE/opt/{app_name}/safetool-downloader-desktop" "$@"
        """))
    apprun_dst.chmod(0o755)

    # Desktop file
    desktop_src = ROOT / "packaging" / "linux" / "appimage" / "safetool-downloader.desktop"
    desktop_dst = appdir / f"{desktop_id}.desktop"
    desktop_apps_dir = appdir / "usr" / "share" / "applications"
    desktop_apps_dir.mkdir(parents=True, exist_ok=True)

    if desktop_src.exists():
        shutil.copy2(desktop_src, desktop_dst)
        shutil.copy2(desktop_src, desktop_apps_dir / f"{desktop_id}.desktop")
    else:
        desktop_content = textwrap.dedent(f"""\
            [Desktop Entry]
            Type=Application
            Name=SafeTool Downloader
            GenericName=Web File Downloader
            Exec=safetool-downloader-desktop %U
            Icon={desktop_id}
            Categories=Network;FileTransfer;Utility;
            Comment=Download files from websites — scan, preview, and batch download
            Terminal=false
            StartupNotify=true
        """)
        desktop_dst.write_text(desktop_content)
        (desktop_apps_dir / f"{desktop_id}.desktop").write_text(desktop_content)

    # Icon
    icon_src = ROOT / "assets" / "icon.png"
    if icon_src.exists():
        shutil.copy2(icon_src, appdir / f"{desktop_id}.png")
        shutil.copy2(icon_src, appdir / f"{app_name}.png")
        icon_dir = appdir / "usr" / "share" / "icons" / "hicolor" / "512x512" / "apps"
        icon_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(icon_src, icon_dir / f"{desktop_id}.png")

    # AppStream metainfo
    metainfo_dir = appdir / "usr" / "share" / "metainfo"
    metainfo_dir.mkdir(parents=True)
    metainfo_src = ROOT / "packaging" / "linux" / "flatpak" / "org.safetoolhub.safetooldownloader.metainfo.xml"
    if metainfo_src.exists():
        shutil.copy2(metainfo_src, metainfo_dir / f"{desktop_id}.metainfo.xml")
        shutil.copy2(metainfo_src, metainfo_dir / f"{desktop_id}.appdata.xml")

    # Run appimagetool
    appimage_name = f"SafeToolDownloader-{full_version}-linux-x86_64.AppImage"
    appimage_path = DIST_DIR / appimage_name

    try:
        env = os.environ.copy()
        env["ARCH"] = "x86_64"
        env.setdefault("APPIMAGE_EXTRACT_AND_RUN", "1")
        print(f"  Building AppImage: {appimage_name}")

        result = subprocess.run(
            [appimagetool, "--no-appstream", str(appdir), str(appimage_path)],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            print(f"⚠️  appimagetool failed with return code {result.returncode}")
            if result.stdout:
                print(f"     stdout: {result.stdout}")
            if result.stderr:
                print(f"     stderr: {result.stderr}")
        elif appimage_path.exists():
            artifacts.append(appimage_path)
            print(f"✅ AppImage: {appimage_path}")
        else:
            print(f"⚠️  AppImage not created at expected path: {appimage_path}")

    except Exception as e:
        print(f"⚠️  Unexpected error during AppImage creation: {e}")

    return artifacts


# ─────────────────────────────────────────────────────────────────────────────
# Windows packaging
# ─────────────────────────────────────────────────────────────────────────────

def package_windows(output_dir: Path, full_version: str, version: str) -> list[Path]:
    """Create Inno Setup installer."""
    print("\n── Windows Packaging ───────────────────────────────────\n")
    artifacts: list[Path] = []

    iscc = shutil.which("iscc") or shutil.which("ISCC")
    iss = ROOT / "packaging" / "windows" / "safetool-downloader.iss"

    if iscc and iss.exists():
        env = os.environ.copy()
        env["APP_VERSION"] = version
        env["APP_FULL_VERSION"] = full_version

        run([
            iscc,
            f"/DAPP_VERSION={version}",
            f"/DAPP_FULL_VERSION={full_version}",
            str(iss),
        ], env=env)

        installer_name = f"SafeToolDownloader-{full_version}-windows-setup.exe"
        expected = DIST_DIR / installer_name
        if expected.exists():
            artifacts.append(expected)
            print(f"✅ Installer: {expected}")
        else:
            inno_output = DIST_DIR / "Output"
            if inno_output.exists():
                for f in inno_output.iterdir():
                    if f.suffix == ".exe":
                        dest = DIST_DIR / installer_name
                        shutil.move(str(f), str(dest))
                        artifacts.append(dest)
                        print(f"✅ Installer: {dest}")
    else:
        if not iscc:
            print("⚠️  Inno Setup (iscc) not found, skipping Windows installer")
        if not iss.exists():
            print(f"⚠️  {iss} not found, skipping Windows installer")

    return artifacts


# ─────────────────────────────────────────────────────────────────────────────
# macOS packaging
# ─────────────────────────────────────────────────────────────────────────────

def package_macos(output_dir: Path, full_version: str) -> list[Path]:
    """Create .dmg from .app bundle."""
    print("\n── macOS Packaging ────────────────────────────────────\n")
    artifacts: list[Path] = []

    app_bundle = DIST_DIR / "SafeToolDownloader.app"
    if not app_bundle.exists():
        print(f"⚠️  {app_bundle} not found, skipping DMG")
        return artifacts

    dmg_name = f"SafeToolDownloader-{full_version}-macos.dmg"
    dmg_path = DIST_DIR / dmg_name

    create_dmg = shutil.which("create-dmg")
    if create_dmg:
        if dmg_path.exists():
            dmg_path.unlink()

        try:
            icon_args = []
            icon_icns = ROOT / "assets" / "icon.icns"
            if icon_icns.exists():
                icon_args = ["--volicon", str(icon_icns)]

            run([
                create_dmg,
                "--volname", "SafeTool Downloader",
                *icon_args,
                "--window-pos", "200", "120",
                "--window-size", "600", "400",
                "--icon-size", "100",
                "--icon", "SafeToolDownloader.app", "175", "200",
                "--app-drop-link", "425", "200",
                str(dmg_path),
                str(app_bundle),
            ])
        except subprocess.CalledProcessError:
            # create-dmg exits 2 on "no code sign" which is OK
            pass

        if dmg_path.exists():
            artifacts.append(dmg_path)
            print(f"✅ DMG: {dmg_path}")
    else:
        try:
            run([
                "hdiutil", "create",
                "-volname", "SafeTool Downloader",
                "-srcfolder", str(app_bundle),
                "-ov",
                "-format", "UDZO",
                str(dmg_path),
            ])
            if dmg_path.exists():
                artifacts.append(dmg_path)
                print(f"✅ DMG: {dmg_path}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("⚠️  create-dmg/hdiutil not available, skipping DMG")

    return artifacts


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Build SafeTool Downloader")
    parser.add_argument("--skip-installer", action="store_true",
                        help="Only run PyInstaller, skip native installer packaging")
    args = parser.parse_args()

    version, suffix, full_version = get_version_info()

    print(f"Building SafeTool Downloader v{full_version}")
    print(f"Platform: {platform.system()} {platform.machine()}")

    # Step 1: PyInstaller
    output_dir = build_pyinstaller()

    if args.skip_installer:
        print("\n--skip-installer: Skipping native packaging")
        return

    # Step 2: Platform-specific packaging
    artifacts: list[Path] = []
    system = platform.system()

    if system == "Linux":
        artifacts = package_linux(output_dir, full_version)
        artifacts.extend(package_appimage(output_dir, full_version))
    elif system == "Windows":
        artifacts = package_windows(output_dir, full_version, version)
    elif system == "Darwin":
        artifacts = package_macos(output_dir, full_version)

    # Summary
    print("\n══════════════════════════════════════════════════════════")
    print("  Build Summary")
    print("══════════════════════════════════════════════════════════\n")
    print(f"  Version:  {full_version}")
    print(f"  Platform: {system}")
    if artifacts:
        print("  Artifacts:")
        for a in artifacts:
            size_mb = a.stat().st_size / (1024 * 1024)
            print(f"    • {a.name}  ({size_mb:.1f} MB)")
    else:
        print(f"  PyInstaller output: {output_dir}")
        print("  (No native installer created)")
    print()


if __name__ == "__main__":
    main()
