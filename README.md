# CV Generator

Local CLI for generating CVs as PDF from Markdown. Aimed at developers on macOS and Linux.

## Status

The Python environment and PDF stack are set up. The application itself is still a stub (`uv run cv-generator` prints a hello message).

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

```bash
uv run cv-generator
# or
uv run python
source .venv/bin/activate
```

## Stack

| Package | Role |
| --- | --- |
| [Jinja2](https://jinja.palletsprojects.com/) | HTML templates |
| [Python-Markdown](https://python-markdown.github.io/) | Markdown → HTML |
| [WeasyPrint](https://weasyprint.org/) | HTML → PDF |
