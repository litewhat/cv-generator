# Markdown to PDF (v1)

Date: 2026-08-20

## Goal

Add a `generate-pdf` subcommand that turns one Markdown file into a readable PDF using the existing stack: Python-Markdown, a small Jinja document shell, and WeasyPrint.

```bash
uv run cv-generator generate-pdf --input cv.md --output cv.pdf
```

Success: that command exits 0, writes a valid PDF (`%PDF` header) at `--output`, and the PDF shows headings, lists, tables, and fenced code from the Markdown.

## Non-goals (v1)

- Stdin/stdout or `-` as a path
- Default output path derived from the input name
- `--template`, custom CSS flags, YAML front matter
- CV-specific layout (sidebar, skills, photo chrome)
- Syntax highlighting / Pygments
- `--verbose`
- Windows as a target (macOS and Linux only, as the rest of the project)

Phase B (Jinja CV templates) is follow-up work, not part of this spec. See [Future work](#future-work-phase-b).

## Architecture

Five units. Each has one job. CLI never imports WeasyPrint. Convert modules never touch argparse or the filesystem, except `html_document` loading the packaged template.

```
src/cv_generator/
  __init__.py            # package marker; no CLI stub
  __main__.py            # python -m cv_generator → cli.main
  cli.py                 # argv → subcommand; exit codes
  generate_pdf.py        # use-case: paths in, files out
  markdown_to_html.py    # Markdown text → HTML fragment
  html_document.py       # fragment + title → full HTML (Jinja)
  html_to_pdf.py         # full HTML → PDF bytes (WeasyPrint)
  templates/
    default.html.j2      # document shell + basic CSS
```

`pyproject.toml` entry point: `cv-generator = "cv_generator.cli:main"`. Remove the current `cv_generator:main` hello stub.

| Unit | Does | Depends on | Does not |
| --- | --- | --- | --- |
| `cli` | Parse argv, print errors to stderr, return exit codes | `generate_pdf` | Markdown, Jinja, WeasyPrint |
| `generate_pdf` | Validate paths, read UTF-8, call the three steps, atomic write | convert modules, `pathlib` | argparse |
| `markdown_to_html` | Markdown string → HTML fragment | `markdown` | files, Jinja, WeasyPrint |
| `html_document` | Fragment + title → full HTML document | Jinja2, packaged template | files (except the template resource), WeasyPrint |
| `html_to_pdf` | Full HTML + `base_url` → PDF bytes | WeasyPrint | files, Markdown, Jinja |

## Public functions

```python
def markdown_to_html(markdown_text: str) -> str: ...

def html_document(content: str, title: str) -> str: ...

def html_to_pdf(html: str, *, base_url: str | Path) -> bytes: ...

def generate_pdf(input_path: Path, output_path: Path) -> None: ...

def main(argv: list[str] | None = None) -> int: ...
```

`main(None)` uses `sys.argv[1:]`. `python -m cv_generator` and the `cv-generator` script both call `sys.exit(main())`.

## Data flow

1. CLI parses `generate-pdf --input/--output` (also `-i`/`-o`).
2. `generate_pdf`:
   - Reject missing input, non-files, and directory outputs.
   - Read input as UTF-8.
   - `html = markdown_to_html(text)`
   - `doc = html_document(html, title=input_path.stem)`
   - `pdf = html_to_pdf(doc, base_url=input_path.parent)`
   - Create `output_path.parent` (`mkdir(parents=True, exist_ok=True)`).
   - Write bytes to a temp file in that same directory, then `os.replace` onto `output_path`.
3. CLI returns `0`.

Empty Markdown still produces a valid (mostly blank) PDF.

## CLI contract

```bash
uv run cv-generator generate-pdf --input cv.md --output cv.pdf
uv run cv-generator generate-pdf -i cv.md -o cv.pdf
uv run cv-generator --help
uv run cv-generator generate-pdf --help
```

- `generate-pdf` is the only subcommand. A missing subcommand is an error (argparse, exit 2).
- `--input` and `--output` are required. No stdin/stdout.
- Existing `--output` is overwritten.
- Success: exit 0, no stdout.
- Use stdlib `argparse` only (no Typer/Click).

## Errors

`main` catches argparse `SystemExit` and returns its code so tests can assert return values. `--help` returns `0`.

| Situation | Where | Exit | stderr |
| --- | --- | --- | --- |
| Unknown command, missing flags, bad flag | argparse | 2 | usage |
| Input missing or not a file | `generate_pdf` | 1 | short path error |
| `--output` is an existing directory | `generate_pdf` | 1 | short path error |
| Input not UTF-8 | `generate_pdf` | 1 | short decode error |
| WeasyPrint / native-lib failure | `generate_pdf` / `html_to_pdf` | 1 | library message; temp file deleted; no half-written PDF |

`generate_pdf` raises `FileNotFoundError` (missing input), `IsADirectoryError` (input or output path is a directory), `UnicodeDecodeError` (input not UTF-8), and `CvGeneratorError` (defined in `generate_pdf.py`) wrapping WeasyPrint or other render failures. Convert modules may raise library exceptions; they do not print. `cli` maps those four types to exit 1 and must not `import weasyprint`.

Atomic write: on any failure after creating the temp file, delete the temp file. Never leave a truncated file at `--output`. `os.replace` overwrites an existing PDF.

## Markdown

Python-Markdown with a fixed extension list: `fenced_code`, `tables`, `sane_lists`. No `codehilite`. Return a fragment (`<h1>…`, `<p>…`, `<table>…`), not a full document.

## Template

`src/cv_generator/templates/default.html.j2` is a complete HTML5 page.

Variables:

- `content` — HTML fragment. Jinja autoescape on; pass `content` as already-safe HTML (we produced it) so tags render.
- `title` — `input_path.stem` (`cv.md` → `cv`). Used in `<title>` and nowhere else that would look like CV chrome.

Load with `importlib.resources.files("cv_generator") / "templates" / "default.html.j2"` so the file ships with the package. The module directory is included by `uv_build`; no extra package-data config unless a build proves otherwise.

CSS (inline in the template): `@page` A4 with modest margins; system sans-serif body; styles for headings, paragraphs, lists, tables, and `code`/`pre` so the PDF is readable. No logo, columns, or sidebar.

## WeasyPrint

```python
weasyprint.HTML(string=html, base_url=str(base_url)).write_pdf()
```

`base_url` is the Markdown file’s parent directory so relative images (`![alt](photo.jpg)`) resolve next to the `.md` file.

## Tests

Dev dependency: `pytest` via `uv add --dev pytest`. Run with `uv run pytest`. Tests live in `tests/` at the repo root.

| Layer | Assert | I/O |
| --- | --- | --- |
| `markdown_to_html` | Heading, fenced code, and table Markdown become the matching tags | in-memory |
| `html_document` | Full HTML document; `content` and `title` present | in-memory |
| `html_to_pdf` | Bytes start with `%PDF` and are non-empty | in-memory |
| `generate_pdf` | Temp `.md` writes a real PDF; missing input raises; existing output is overwritten | temp files |
| `cli` | `main(["generate-pdf", "-i", …, "-o", …])` returns 0; missing flags return 2; missing file returns 1 | temp files + `main(argv)` |

Exactly one test path must call WeasyPrint (`html_to_pdf` and/or `generate_pdf`) so missing cairo/pango fails CI/local runs. Markdown and Jinja tests must not import WeasyPrint.

## Docs to update in the same change

README: show the `generate-pdf` command instead of the hello stub. Do not copy this spec into `AGENTS.md`.

## Future work (phase B)

Not in v1. When it happens:

- Keep this pipeline. Add a CV Jinja template and a `--template` flag on `generate-pdf`.
- `templates/default.html.j2` remains the fallback.
- Still no stdin/stdout unless a later spec says so.
