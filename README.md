# CV Generator

Local CLI for generating CVs as PDF from Markdown. Aimed at developers on macOS and Linux.

## Status

The `generate-pdf` command is available: it converts a Markdown file to a PDF with Jinja2 and WeasyPrint.

## Requirements

- [uv](https://docs.astral.sh/uv/) (0.12+)
- Python 3.14 (installed by uv from `.python-version`)
- Native libraries for WeasyPrint: cairo, pango, gdk-pixbuf, libffi

## Setup

### macOS

```bash
brew install cairo pango gdk-pixbuf libffi
uv sync
```

### Linux

Install cairo, pango, gdk-pixbuf, and libffi with your distro package manager, then:

```bash
uv sync
```

## Usage

`--input` and `--output` are required. An existing PDF at `--output` is overwritten. Success prints nothing.

```bash
uv run cv-generator generate-pdf --input cv.md --output cv.pdf
uv run cv-generator generate-pdf -i cv.md -o cv.pdf
uv run cv-generator --help
uv run cv-generator generate-pdf --help
```

## Testing

Requires dev dependencies (installed by default with `uv sync`):

```bash
uv sync
uv run pytest
uv run ty check
uv run pytest -v               # verbose
uv run pytest tests/test_cli.py -v  # single file
```

## Stack

| Package                                               | Role            |
| ----------------------------------------------------- | --------------- |
| [Jinja2](https://jinja.palletsprojects.com/)          | HTML templates  |
| [Python-Markdown](https://python-markdown.github.io/) | Markdown → HTML |
| [WeasyPrint](https://weasyprint.org/)                 | HTML → PDF      |
