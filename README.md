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

## Installation

```bash
# Clone the repository
git clone https://github.com/safetoolhub/safetool-downloader.git
cd safetool-downloader

# Install in editable mode
pip install -e .
```

### Requirements

- Python ≥ 3.11
- PySide6-Essentials ≥ 6.7
- requests, beautifulsoup4, lxml, qtawesome

## Usage

```bash
# Launch the app
safetool-downloader-desktop
```

1. Paste a URL into the input field
2. Optionally enable **Recursive scan** and set max depth
3. Toggle file-type filter chips (PDF, Images, etc.)
4. Click **Scan** — the app fetches the page(s) and lists downloadable files
5. Review and select files in the preview table
6. Choose a destination folder and click **Download**

## Project Structure

```
safetool_downloader_desktop/
├── app.py                   # Entry point
├── main_window.py           # Main window with header, URL input, table, downloads
├── config.py                # App metadata constants
├── settings.py              # QSettings persistence
├── styles/
│   ├── design_system.py     # Design tokens & QSS stylesheet generators
│   └── icons.py             # Material Design Icon management
├── dialogs/
│   ├── base_dialog.py       # Base dialog with styling
│   ├── settings_dialog.py   # Settings preferences dialog
│   └── about_dialog.py      # About / Welcome dialog
├── widgets/
│   ├── url_input_widget.py  # URL bar, scan button, filter chips, recursive controls
│   ├── file_preview_table.py# File preview with selection, sorting, summary
│   └── download_progress_widget.py  # Download controls & per-file progress
└── workers/
    ├── scanner_worker.py    # QThread web scanner with BFS recursive crawling
    └── download_worker.py   # QThread batch file downloader
```

## License

This project is licensed under the **GNU General Public License v3.0** with additional attribution terms.  
See [LICENSE](LICENSE) for details.

**© SafeToolHub** — [safetoolhub.org](https://safetoolhub.org)
