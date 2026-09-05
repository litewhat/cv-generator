# CV Generator

Local CLI that converts Markdown CVs with YAML frontmatter into single-column PDFs using Jinja2, WeasyPrint, and the included `elegant-v1` template. Aimed at developers on macOS and Linux.

## Requirements

- [uv](https://docs.astral.sh/uv/) (0.12+)
- Python 3.14 (installed by uv from `.python-version`)
- Native libraries for WeasyPrint: cairo, pango, gdk-pixbuf, libffi

## Setup

Clone or download this repository, then enter its root directory (`cd cv-generator`). Install the native libraries for your platform below.

### macOS

```bash
brew install cairo pango gdk-pixbuf libffi
```

### Linux

Install cairo, pango, gdk-pixbuf, and libffi with your distro package manager.

### Install the project

From the repository root on either platform:

```bash
uv sync
```

`uv sync` provisions the Python version pinned in `.python-version`, creates `.venv`, and installs the application and development dependencies using `uv.lock`. Use `uv run` to run commands in this environment without activating it manually.

## Usage

Save this complete example as UTF-8 `cv.md`:

```markdown
---
name: Alex Morgan
title: Software Engineer
email: alex@example.com
phone: "+48 123 456 789"
location: Warsaw, Poland
links:
  github: https://github.com/example
  linkedin: https://www.linkedin.com/in/example
---

# Summary

Software engineer building reliable Python applications.

# Experience

## Software Engineer — Example Company

2023–present

- Built internal tools that reduced manual reporting.
- Developed and tested Python services.

# Skills

Python, SQL, Git
```

Generate `cv.pdf` in the current directory:

```bash
uv run cv-generator generate-pdf -i cv.md -o cv.pdf
```

### Input format

YAML frontmatter must begin the file, enclosed by `---` lines. Plain Markdown without the required metadata fails validation.

- `name`, `title`, `email`, `phone` (or `phone_number`), and `location` must be non-empty strings. Quote phone numbers so YAML does not interpret them as numbers.
- `links` is optional. It accepts only `github` and `linkedin` keys with URL strings, as shown above.
- `#` headings define sections, and `##` headings define subsections such as individual jobs. Paragraphs contain descriptions or dates; bullets list achievements or skills. Separate paragraphs with blank lines.

### CLI behavior

`--input` and `--output` are required, with `-i` and `-o` as short forms. Missing output directories are created automatically. An existing PDF at `--output` is overwritten. Success prints nothing.

Exit codes are `0` for success, `1` for handled conversion errors (reported to stderr), and `2` for invalid arguments.

The equivalent command with long options and the help commands are:

```bash
uv run cv-generator generate-pdf --input cv.md --output cv.pdf
uv run cv-generator --help
uv run cv-generator generate-pdf --help
```

## Development

After setup, edit `src/` and exercise your changes with `uv run`, for example using the generation command above. Format the code:

```bash
uv run ruff format src tests
```

Run all standard checks before submitting changes. Development dependencies are installed by `uv sync`; the real PDF tests also require the native WeasyPrint libraries listed above.

```bash
uv run pytest
uv run ty check
uv run ruff check src tests
uv run ruff format --check src tests
```

For verbose or focused test runs:

```bash
uv run pytest -v
uv run pytest tests/cv_generator/test_cli.py -v
```

Use `uv add <package>` and `uv remove <package>` to update dependencies and the lockfile. Run `uv sync` after dependency changes to bring your environment up to date.

### Source map

| Path | Purpose |
| --- | --- |
| `src/cv_generator/cli.py` | Arguments and error reporting |
| `src/cv_generator/generate_pdf.py` | Conversion orchestration and file writing |
| `src/cv_generator/parser.py` | YAML and Markdown parsing |
| `src/cv_generator/document.py` | Validation |
| `src/cv_generator/formatter.py` | HTML rendering |
| `src/cv_generator/templates/elegant-v1.html.j2` | Layout and styling |
| `src/lib/convert.py` | Markdown, HTML, and PDF conversion |
| `tests/cv_generator/` and `tests/lib/` | Corresponding tests |

See [AGENTS.md](AGENTS.md) for agent-specific instructions.

## Stack

| Package                                               | Role            |
| ----------------------------------------------------- | --------------- |
| [Jinja2](https://jinja.palletsprojects.com/)          | HTML templates  |
| [Python-Markdown](https://python-markdown.github.io/) | Markdown → HTML |
| [WeasyPrint](https://weasyprint.org/)                 | HTML → PDF      |
