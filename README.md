# SafeTool Downloader

A cross-platform desktop application for batch downloading files from web pages.  
Built with **PySide6 / Qt6**, featuring a clean Material-inspired UI, file-type filtering, and optional recursive crawling.

![Python](https://img.shields.io/badge/python-3.11+-blue)
![License](https://img.shields.io/badge/license-GPLv3-green)
![Qt](https://img.shields.io/badge/Qt-6-41CD52)

## Features

- **URL scanning** — paste a URL, scan the page for downloadable files
- **Recursive crawling** — optionally follow same-domain links with configurable depth, delay, and page limits
- **File-type filtering** — toggle categories (PDF, Images, Audio, Video, Documents, Archives, Code) or download everything
- **File preview table** — review found files with size, extension badges, and source page before downloading
- **Batch download** — download selected files with per-file progress bars and overall progress
- **Settings persistence** — remembers last URL, output directory, concurrency, and recursive preferences
- **Cross-platform** — runs on Linux, Windows, and macOS

## Requirements

- Python ≥ 3.11 (recommended 3.12)
- [uv](https://docs.astral.sh/uv/) as package/environment manager
- PySide6-Essentials ≥ 6.7
- requests, beautifulsoup4, lxml, qtawesome

## Installation

```bash
# Clone the repository
git clone https://github.com/safetoolhub/safetool-downloader.git
cd safetool-downloader

# Create virtual environment
uv venv .venv --python 3.12

# Install dependencies
uv pip install -r requirements.txt
```

> **Windows:** replace `.venv/bin/` with `.venv\Scripts\`.

## Usage

```bash
# Launch the app
.venv/bin/python -m safetool_downloader_desktop.app
```

Or, if installed via `pip install -e .`, use the entry point:

```bash
safetool-downloader-desktop
```

1. Paste a URL into the input field
2. Optionally enable **Recursive scan** and set max depth
3. Toggle file-type filter chips (PDF, Images, etc.)
4. Click **Scan** — the app fetches the page(s) and lists downloadable files
5. Review and select files in the preview table
6. Choose a destination folder and click **Download**

## Development

```bash
# Run the test suite
.venv/bin/python -m pytest

# Regenerate app icons (requires Pillow)
.venv/bin/python dev-tools/generate_icons.py
```

## Project Structure

```
safetool-downloader/
├── config.py                    # App metadata (name, version, author, URLs) — single source of truth
├── requirements.txt             # Dependencies for uv pip install -r
├── pyproject.toml               # Build config and entry points
├── assets/                      # Generated icons (icon.png, icon.ico)
├── dev-tools/                   # Build and packaging scripts
├── tests/                       # pytest test suite
└── safetool_downloader_desktop/
    ├── app.py                   # Entry point — QApplication, style, launches MainWindow
    ├── main_window.py           # Main window: header, URL input, file table, download bar
    ├── settings.py              # QSettings persistence helpers
    ├── styles/
    │   ├── design_system.py     # Design tokens & QSS stylesheet generators
    │   └── icons.py             # Material Design Icon management (IconManager)
    ├── dialogs/
    │   ├── base_dialog.py       # Base dialog with styling
    │   ├── settings_dialog.py   # Settings preferences dialog
    │   └── about_dialog.py      # About / Welcome dialog
    ├── widgets/
    │   ├── url_input_widget.py  # URL bar, scan button, filter chips, recursive controls
    │   └── file_preview_table.py# Dual-mode table: file preview + download progress
    └── workers/
        ├── scanner_worker.py    # QThread BFS recursive web scanner
        └── download_worker.py   # QThread batch file downloader with streaming
```

## License

This project is licensed under the **GNU General Public License v3.0** with additional attribution terms.  
See [LICENSE](LICENSE) for details.

**SafeToolHub** — [safetoolhub.org](https://safetoolhub.org)
