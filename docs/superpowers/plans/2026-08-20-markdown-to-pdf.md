# Markdown to PDF Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. REQUIRED: superpowers:test-driven-development — no production code without a failing test first.

**Goal:** Add a `generate-pdf` subcommand that turns one Markdown file into a readable PDF via Python-Markdown, a small Jinja document shell, and WeasyPrint.

**Architecture:** Five units with one job each. The CLI parses argv and maps exceptions to exit codes; it never imports WeasyPrint. `generate_pdf` owns paths, UTF-8 I/O, and an atomic write. Convert modules are pure (`markdown_to_html` → HTML fragment, `html_document` → full HTML, `html_to_pdf` → PDF bytes). A packaged `default.html.j2` is the v1 document shell so Phase B can add a CV template later without rewriting the pipeline.

**Tech Stack:** Python 3.14, uv, stdlib argparse, Python-Markdown 3.10.x (`fenced_code`, `tables`, `sane_lists`), Jinja2 3.1.x, WeasyPrint 69.x, pytest (dev).

**Spec:** `docs/superpowers/specs/2026-08-20-markdown-to-pdf-design.md`

## Global Constraints

- Python `>=3.14`; uv only (no system Python, no `pip`). Prefer `uv add` / `uv remove` over hand-editing dependency lists.
- Native WeasyPrint libs: cairo, pango, gdk-pixbuf, libffi. Verify a real PDF (`%PDF` header), not only `import weasyprint`.
- Stdlib `argparse` only (no Typer/Click).
- macOS and Linux only; Windows is not a target.
- `--input` and `--output` are required file paths. No stdin/stdout, no `-` as a path, no default output derived from the input name.
- v1 non-goals (do not implement): `--template`, custom CSS flags, YAML front matter, CV chrome (sidebar/skills/photo), Pygments / `codehilite` / `--verbose`.
- Phase B (Jinja CV templates) is follow-up, not this plan.
- CLI never imports WeasyPrint. Convert modules never touch argparse or the filesystem, except `html_document` loading the packaged template.
- Success: exit 0, no stdout. Existing `--output` is overwritten. Empty Markdown still produces a valid (mostly blank) PDF.
- `main` catches argparse `SystemExit` and returns its code. `--help` returns `0`. Missing subcommand / missing flags / bad flag: exit `2`. Path/decode/render errors: exit `1`.
- Do not copy this spec into `AGENTS.md`. `notatki.md` is personal notes, not a spec — ignore it.
- `AGENTS.md` forbids git init and commits unless the user asks. **Skip every Commit step** until then. Commands are written so they are ready when requested.
- TDD: watch each new test fail for the right reason before writing production code. Template HTML and README are created in the same task as the tests that lock their behavior; do not implement convert/CLI code before those tests exist.

---

## File structure

| Path | Responsibility |
| --- | --- |
| `src/cv_generator/__init__.py` | Package marker only. Remove the uv-init `main()` hello stub (Task 5). |
| `src/cv_generator/__main__.py` | `python -m cv_generator` → `sys.exit(cli.main())`. |
| `src/cv_generator/cli.py` | argparse; print errors to stderr; return exit codes. Depends on `generate_pdf` only. |
| `src/cv_generator/generate_pdf.py` | Path validation, UTF-8 read, three convert steps, atomic write. Defines `CvGeneratorError`. |
| `src/cv_generator/markdown_to_html.py` | Markdown string → HTML fragment. |
| `src/cv_generator/html_document.py` | Fragment + title → full HTML via packaged Jinja template. |
| `src/cv_generator/html_to_pdf.py` | Full HTML + `base_url` → PDF bytes. Import WeasyPrint **inside the function**. |
| `src/cv_generator/templates/default.html.j2` | HTML5 shell + inline A4 CSS. Variables: `content`, `title`. |
| `tests/test_markdown_to_html.py` | In-memory Markdown tests. Must not import WeasyPrint. |
| `tests/test_html_document.py` | In-memory Jinja tests. Must not import WeasyPrint. |
| `tests/test_html_to_pdf.py` | Real WeasyPrint; bytes start with `%PDF`. |
| `tests/test_generate_pdf.py` | Temp files; happy path writes a real PDF; path/decode errors; overwrite. |
| `tests/test_cli.py` | `main(argv)` exit codes; no WeasyPrint import at CLI import time. |
| `pyproject.toml` | Script entry `cv-generator = "cv_generator.cli:main"`; pytest as a dev dependency. |
| `README.md` | Replace the hello stub with the `generate-pdf` command. |

No extra `[tool.uv.build-backend]` package-data config unless a build proves `default.html.j2` is omitted from the wheel. Editable `uv run` sees the file on disk either way.

---

### Task 1: `markdown_to_html`

**Files:**
- Create: `src/cv_generator/markdown_to_html.py`
- Create: `tests/test_markdown_to_html.py`
- Modify: `pyproject.toml` and `uv.lock` via `uv add --dev pytest` (do not hand-edit dependency lists)

**Interfaces:**
- Consumes: Python-Markdown (already in project dependencies)
- Produces: `def markdown_to_html(markdown_text: str) -> str`

Do not import WeasyPrint, Jinja2, or `html_to_pdf` in the test file or the implementation.

- [ ] **Step 1: Add pytest**

```bash
uv add --dev pytest
```

Confirm `uv run pytest` runs (zero tests is OK: `collected 0 items`).

- [ ] **Step 2: Write the failing tests**

Create `tests/test_markdown_to_html.py`:

````python
from cv_generator.markdown_to_html import markdown_to_html

_FENCE = chr(96) * 3


def test_heading_becomes_h1():
    html = markdown_to_html("# Hello")
    assert "<h1>Hello</h1>" in html
    assert "<html" not in html.lower()
    assert "<body" not in html.lower()


def test_fenced_code_becomes_pre_code():
    html = markdown_to_html(f"{_FENCE}python\nx = 1\n{_FENCE}")
    assert "<pre>" in html
    assert '<code class="language-python">' in html
    assert "x = 1" in html
    assert "codehilite" not in html
    assert "<span" not in html


def test_table_becomes_table_tags():
    html = markdown_to_html("| A | B |\n| --- | --- |\n| 1 | 2 |\n")
    assert "<table>" in html
    assert "<th>A</th>" in html
    assert "<td>1</td>" in html


def test_unordered_list_becomes_ul():
    html = markdown_to_html("- a\n- b\n")
    assert "<ul>" in html
    assert "<li>a</li>" in html
    assert "<li>b</li>" in html
````

- [ ] **Step 3: Run tests to verify they fail**

```bash
uv run pytest tests/test_markdown_to_html.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'cv_generator.markdown_to_html'` (or `ImportError`). Do not create the module until you see this.

- [ ] **Step 4: Write the minimal implementation**

Create `src/cv_generator/markdown_to_html.py`:

```python
import markdown

_EXTENSIONS = ["fenced_code", "tables", "sane_lists"]


def markdown_to_html(markdown_text: str) -> str:
    return markdown.markdown(markdown_text, extensions=_EXTENSIONS)
```

Do not add `codehilite` or other extensions.

- [ ] **Step 5: Run tests to verify they pass**

```bash
uv run pytest tests/test_markdown_to_html.py -v
```

Expected: 4 passed.

- [ ] **Step 6: Commit** (skip unless the user asked to commit)

```bash
git add pyproject.toml uv.lock src/cv_generator/markdown_to_html.py tests/test_markdown_to_html.py
git commit -m "feat: convert Markdown strings to HTML fragments"
```

---

### Task 2: `html_document` and packaged template

**Files:**
- Create: `src/cv_generator/html_document.py`
- Create: `src/cv_generator/templates/default.html.j2`
- Create: `tests/test_html_document.py`

**Interfaces:**
- Consumes: Jinja2 (already in project dependencies); packaged template at `cv_generator/templates/default.html.j2`
- Produces: `def html_document(content: str, title: str) -> str`

Do not import WeasyPrint in the test file or the implementation. Do not read the caller's Markdown file from disk — only the packaged template.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_html_document.py`:

```python
from cv_generator.html_document import html_document


def test_html_document_is_full_page_with_title_and_content():
    html = html_document("<p>Hello</p>", "My Title")
    stripped = html.lstrip()
    assert stripped.startswith("<!DOCTYPE html>") or stripped.lower().startswith("<!doctype html>")
    assert "<title>My Title</title>" in html
    assert "<p>Hello</p>" in html


def test_html_document_does_not_escape_content_tags():
    html = html_document("<h1>X</h1>", "t")
    assert "<h1>X</h1>" in html
    assert "&lt;h1&gt;" not in html


def test_html_document_escapes_title():
    html = html_document("<p>x</p>", "A < B")
    assert "A &lt; B" in html


def test_html_document_includes_a4_page_css():
    html = html_document("<p>x</p>", "t")
    assert "@page" in html
    assert "A4" in html
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_html_document.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'cv_generator.html_document'`.

- [ ] **Step 3: Add the template**

Create `src/cv_generator/templates/default.html.j2` (no `templates/__init__.py`):

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{{ title }}</title>
  <style>
    @page {
      size: A4;
      margin: 2cm;
    }
    body {
      font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
      font-size: 11pt;
      line-height: 1.4;
      color: #111;
    }
    h1, h2, h3, h4, h5, h6 {
      font-weight: 600;
      line-height: 1.25;
      margin: 1.2em 0 0.4em;
    }
    p { margin: 0.6em 0; }
    ul, ol { margin: 0.6em 0; padding-left: 1.4em; }
    table {
      border-collapse: collapse;
      width: 100%;
      margin: 0.8em 0;
    }
    th, td {
      border: 1px solid #ccc;
      padding: 0.35em 0.6em;
      text-align: left;
    }
    code {
      font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
      font-size: 0.9em;
    }
    pre {
      background: #f5f5f5;
      padding: 0.8em;
      overflow-x: auto;
    }
    pre code { font-size: 0.85em; }
  </style>
</head>
<body>
  {{ content }}
</body>
</html>
```

No logo, columns, or sidebar.

- [ ] **Step 4: Write the minimal implementation**

Create `src/cv_generator/html_document.py`:

```python
from importlib.resources import files

from jinja2 import Environment
from markupsafe import Markup


def html_document(content: str, title: str) -> str:
    template_text = (
        files("cv_generator") / "templates" / "default.html.j2"
    ).read_text(encoding="utf-8")
    env = Environment(autoescape=True)
    template = env.from_string(template_text)
    return template.render(content=Markup(content), title=title)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
uv run pytest tests/test_html_document.py tests/test_markdown_to_html.py -v
```

Expected: all passed.

Also confirm the template is loadable as a package resource:

```bash
uv run python -c "from importlib.resources import files; t = (files('cv_generator') / 'templates' / 'default.html.j2').read_text(encoding='utf-8'); print(t[:15])"
```

Expected: starts with `<!DOCTYPE html>` (or the first 15 characters of that file). If this fails under `uv run` in the project, fix the path before moving on. Do not add build-backend config unless a later `uv build` wheel is missing the file.

- [ ] **Step 6: Commit** (skip unless the user asked to commit)

```bash
git add src/cv_generator/html_document.py src/cv_generator/templates/default.html.j2 tests/test_html_document.py
git commit -m "feat: wrap HTML fragments in a Jinja document shell"
```

---

### Task 3: `html_to_pdf`

**Files:**
- Create: `src/cv_generator/html_to_pdf.py`
- Create: `tests/test_html_to_pdf.py`

**Interfaces:**
- Consumes: WeasyPrint (already in project dependencies)
- Produces: `def html_to_pdf(html: str, *, base_url: str | pathlib.Path) -> bytes`

Import WeasyPrint **inside** `html_to_pdf`, not at module top-level, so `import cv_generator.html_to_pdf` does not load cairo/pango. Do not mock WeasyPrint. This is a required real-render path: if cairo/pango is missing, these tests must fail.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_html_to_pdf.py`:

```python
from pathlib import Path

from cv_generator.html_to_pdf import html_to_pdf

_MINIMAL_HTML = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>t</title></head>
<body><h1>Hello</h1></body>
</html>
"""


def test_html_to_pdf_returns_pdf_bytes(tmp_path: Path):
    pdf = html_to_pdf(_MINIMAL_HTML, base_url=tmp_path)
    assert isinstance(pdf, bytes)
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 0


def test_html_to_pdf_accepts_string_base_url(tmp_path: Path):
    pdf = html_to_pdf(_MINIMAL_HTML, base_url=str(tmp_path))
    assert pdf.startswith(b"%PDF")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_html_to_pdf.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'cv_generator.html_to_pdf'`.

- [ ] **Step 3: Write the minimal implementation**

Create `src/cv_generator/html_to_pdf.py`:

```python
from pathlib import Path


def html_to_pdf(html: str, *, base_url: str | Path) -> bytes:
    from weasyprint import HTML

    pdf = HTML(string=html, base_url=str(base_url)).write_pdf()
    if not pdf:
        raise RuntimeError("WeasyPrint returned no PDF bytes")
    return pdf
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_html_to_pdf.py tests/test_markdown_to_html.py tests/test_html_document.py -v
```

Expected: all passed. If WeasyPrint raises about cairo/pango/gdk-pixbuf, stop and fix native libs (Homebrew on macOS: `cairo pango gdk-pixbuf libffi`); do not skip or mock these tests.

- [ ] **Step 5: Commit** (skip unless the user asked to commit)

```bash
git add src/cv_generator/html_to_pdf.py tests/test_html_to_pdf.py
git commit -m "feat: render HTML documents to PDF bytes"
```

---

### Task 4: `generate_pdf` use-case

**Files:**
- Create: `src/cv_generator/generate_pdf.py`
- Create: `tests/test_generate_pdf.py`

**Interfaces:**
- Consumes:
  - `markdown_to_html(markdown_text: str) -> str`
  - `html_document(content: str, title: str) -> str`
  - `html_to_pdf(html: str, *, base_url: str | Path) -> bytes`
- Produces:
  - `class CvGeneratorError(Exception): ...` in `generate_pdf.py`
  - `def generate_pdf(input_path: Path, output_path: Path) -> None`

`generate_pdf` does not use argparse. It raises `FileNotFoundError` (missing input / non-file), `IsADirectoryError` (input or output path is a directory), `UnicodeDecodeError` (input not UTF-8), and `CvGeneratorError` wrapping WeasyPrint or other render failures. Convert-module exceptions are not printed here.

Happy-path tests must call the real pipeline (real WeasyPrint). Do not mock `html_to_pdf` in success tests.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_generate_pdf.py`:

````python
from pathlib import Path

import pytest

from cv_generator.generate_pdf import CvGeneratorError, generate_pdf

_FENCE = chr(96) * 3
_MD = (
    "# Hello\n\n"
    "- one\n"
    "- two\n\n"
    f"{_FENCE}python\n"
    "x = 1\n"
    f"{_FENCE}\n\n"
    "| A | B |\n"
    "| --- | --- |\n"
    "| 1 | 2 |\n"
)


def test_generate_pdf_writes_valid_pdf(tmp_path: Path):
    source = tmp_path / "cv.md"
    source.write_text(_MD, encoding="utf-8")
    output = tmp_path / "cv.pdf"
    generate_pdf(source, output)
    data = output.read_bytes()
    assert data.startswith(b"%PDF")
    assert output.stat().st_size > 0


def test_empty_markdown_writes_valid_pdf(tmp_path: Path):
    source = tmp_path / "empty.md"
    source.write_text("", encoding="utf-8")
    output = tmp_path / "empty.pdf"
    generate_pdf(source, output)
    assert output.read_bytes().startswith(b"%PDF")


def test_creates_missing_output_parent_dirs(tmp_path: Path):
    source = tmp_path / "cv.md"
    source.write_text("# Hi\n", encoding="utf-8")
    output = tmp_path / "nested" / "dir" / "cv.pdf"
    generate_pdf(source, output)
    assert output.is_file()
    assert output.read_bytes().startswith(b"%PDF")


def test_overwrites_existing_output(tmp_path: Path):
    source = tmp_path / "cv.md"
    source.write_text("# First\n", encoding="utf-8")
    output = tmp_path / "cv.pdf"
    generate_pdf(source, output)
    first = output.read_bytes()
    source.write_text("# Second\n\n" + ("word " * 400) + "\n", encoding="utf-8")
    generate_pdf(source, output)
    second = output.read_bytes()
    assert second.startswith(b"%PDF")
    assert second != first


def test_missing_input_raises_file_not_found(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        generate_pdf(tmp_path / "missing.md", tmp_path / "out.pdf")


def test_input_directory_raises_is_a_directory(tmp_path: Path):
    with pytest.raises(IsADirectoryError):
        generate_pdf(tmp_path, tmp_path / "out.pdf")


def test_output_directory_raises_is_a_directory(tmp_path: Path):
    source = tmp_path / "cv.md"
    source.write_text("# Hi\n", encoding="utf-8")
    with pytest.raises(IsADirectoryError):
        generate_pdf(source, tmp_path)


def test_non_utf8_input_raises_unicode_decode_error(tmp_path: Path):
    source = tmp_path / "bad.md"
    source.write_bytes(b"\xff\xfe")
    with pytest.raises(UnicodeDecodeError):
        generate_pdf(source, tmp_path / "out.pdf")


def test_render_failure_does_not_write_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    source = tmp_path / "cv.md"
    source.write_text("# Hi\n", encoding="utf-8")
    output = tmp_path / "out.pdf"

    def boom(html: str, *, base_url: str | Path) -> bytes:
        raise RuntimeError("cairo missing")

    monkeypatch.setattr("cv_generator.generate_pdf.html_to_pdf", boom)
    with pytest.raises(CvGeneratorError, match="cairo missing"):
        generate_pdf(source, output)
    assert not output.exists()


def test_replace_failure_deletes_temp_and_keeps_old_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    import os

    source = tmp_path / "cv.md"
    source.write_text("# Hi\n", encoding="utf-8")
    output = tmp_path / "out.pdf"
    generate_pdf(source, output)
    original = output.read_bytes()

    def fail_replace(src: str | os.PathLike[str], dst: str | os.PathLike[str]) -> None:
        raise OSError("boom")

    monkeypatch.setattr("cv_generator.generate_pdf.os.replace", fail_replace)
    with pytest.raises(OSError, match="boom"):
        generate_pdf(source, output)
    assert output.read_bytes() == original
    leftovers = list(tmp_path.glob(".cv-generator-*.pdf"))
    assert leftovers == []
````

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_generate_pdf.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'cv_generator.generate_pdf'`.

- [ ] **Step 3: Write the minimal implementation**

Create `src/cv_generator/generate_pdf.py`:

```python
import os
import tempfile
from pathlib import Path

from cv_generator.html_document import html_document
from cv_generator.html_to_pdf import html_to_pdf
from cv_generator.markdown_to_html import markdown_to_html


class CvGeneratorError(Exception):
    """Render or conversion failure for the CLI to report (exit 1)."""


def generate_pdf(input_path: Path, output_path: Path) -> None:
    input_path = Path(input_path)
    output_path = Path(output_path)

    if not input_path.exists():
        raise FileNotFoundError(f"Input not found: {input_path}")
    if input_path.is_dir():
        raise IsADirectoryError(f"Input is a directory: {input_path}")
    if not input_path.is_file():
        raise FileNotFoundError(f"Input is not a file: {input_path}")
    if output_path.exists() and output_path.is_dir():
        raise IsADirectoryError(f"Output is a directory: {output_path}")

    text = input_path.read_text(encoding="utf-8")

    try:
        fragment = markdown_to_html(text)
        document = html_document(fragment, title=input_path.stem)
        pdf_bytes = html_to_pdf(document, base_url=input_path.parent)
    except Exception as exc:
        raise CvGeneratorError(str(exc)) from exc

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=".cv-generator-",
        suffix=".pdf",
        dir=output_path.parent,
    )
    try:
        with os.fdopen(fd, "wb") as tmp_file:
            tmp_file.write(pdf_bytes)
        os.replace(tmp_name, output_path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise
```

Title is `input_path.stem` (`cv.md` → `cv`). `base_url` is `input_path.parent` so relative images resolve next to the Markdown file.

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_generate_pdf.py tests/test_markdown_to_html.py tests/test_html_document.py tests/test_html_to_pdf.py -v
```

Expected: all passed.

- [ ] **Step 5: Commit** (skip unless the user asked to commit)

```bash
git add src/cv_generator/generate_pdf.py tests/test_generate_pdf.py
git commit -m "feat: write Markdown files to PDFs atomically"
```

---

### Task 5: CLI, entry point, and README

**Files:**
- Create: `src/cv_generator/cli.py`
- Create: `src/cv_generator/__main__.py`
- Create: `tests/test_cli.py`
- Modify: `src/cv_generator/__init__.py` (delete the hello `main()` stub; leave a package marker)
- Modify: `pyproject.toml` — change `[project.scripts]` from `cv-generator = "cv_generator:main"` to `cv-generator = "cv_generator.cli:main"`
- Modify: `README.md` — replace the stub usage with `generate-pdf`

**Interfaces:**
- Consumes:
  - `generate_pdf(input_path: Path, output_path: Path) -> None`
  - `CvGeneratorError`
- Produces: `def main(argv: list[str] | None = None) -> int`
- `main(None)` uses `sys.argv[1:]`. `python -m cv_generator` and the `cv-generator` script both end in `sys.exit(main())` (`__main__.py` calls it; the console script wrapper sys.exits the return code).

`cli.py` must not import WeasyPrint. It may import `generate_pdf`; WeasyPrint stays unloaded until `html_to_pdf()` runs because that function imports it lazily. Do not add `import weasyprint` (or a top-level import in `html_to_pdf.py`).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_cli.py`:

```python
import subprocess
import sys
from pathlib import Path

from cv_generator.cli import main
from cv_generator.generate_pdf import CvGeneratorError


def test_success_returns_0_and_writes_pdf_silently(tmp_path: Path, capsys):
    source = tmp_path / "cv.md"
    source.write_text("# Hello\n", encoding="utf-8")
    output = tmp_path / "cv.pdf"
    code = main(["generate-pdf", "-i", str(source), "-o", str(output)])
    captured = capsys.readouterr()
    assert code == 0
    assert captured.out == ""
    assert output.read_bytes().startswith(b"%PDF")


def test_long_flags_work(tmp_path: Path):
    source = tmp_path / "cv.md"
    source.write_text("# Hello\n", encoding="utf-8")
    output = tmp_path / "cv.pdf"
    code = main(["generate-pdf", "--input", str(source), "--output", str(output)])
    assert code == 0
    assert output.is_file()


def test_missing_flags_returns_2():
    assert main(["generate-pdf"]) == 2


def test_missing_subcommand_returns_2():
    assert main([]) == 2


def test_unknown_command_returns_2():
    assert main(["not-a-command"]) == 2


def test_help_returns_0(capsys):
    assert main(["--help"]) == 0
    assert "generate-pdf" in capsys.readouterr().out


def test_generate_pdf_help_returns_0(capsys):
    assert main(["generate-pdf", "--help"]) == 0
    out = capsys.readouterr().out
    assert "--input" in out
    assert "--output" in out


def test_missing_input_file_returns_1(tmp_path: Path, capsys):
    missing = tmp_path / "nope.md"
    code = main(["generate-pdf", "-i", str(missing), "-o", str(tmp_path / "out.pdf")])
    err = capsys.readouterr().err
    assert code == 1
    assert str(missing) in err


def test_output_directory_returns_1(tmp_path: Path, capsys):
    source = tmp_path / "cv.md"
    source.write_text("# Hi\n", encoding="utf-8")
    code = main(["generate-pdf", "-i", str(source), "-o", str(tmp_path)])
    err = capsys.readouterr().err
    assert code == 1
    assert err.strip() != ""


def test_non_utf8_input_returns_1(tmp_path: Path, capsys):
    source = tmp_path / "bad.md"
    source.write_bytes(b"\xff\xfe")
    code = main(["generate-pdf", "-i", str(source), "-o", str(tmp_path / "out.pdf")])
    err = capsys.readouterr().err
    assert code == 1
    assert "UTF-8" in err


def test_cv_generator_error_returns_1(tmp_path: Path, capsys, monkeypatch):
    source = tmp_path / "cv.md"
    source.write_text("# Hi\n", encoding="utf-8")

    def boom(input_path: Path, output_path: Path) -> None:
        raise CvGeneratorError("cairo missing")

    monkeypatch.setattr("cv_generator.cli.generate_pdf", boom)
    code = main(["generate-pdf", "-i", str(source), "-o", str(tmp_path / "out.pdf")])
    err = capsys.readouterr().err
    assert code == 1
    assert "cairo missing" in err


def test_importing_cli_does_not_import_weasyprint():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import cv_generator.cli, sys; "
            "raise SystemExit(0 if 'weasyprint' not in sys.modules else 1)",
        ],
        check=False,
    )
    assert result.returncode == 0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_cli.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'cv_generator.cli'`.

- [ ] **Step 3: Implement CLI, `__main__`, entry point, and clear the stub**

Create `src/cv_generator/cli.py`:

```python
import argparse
import sys
from pathlib import Path

from cv_generator.generate_pdf import CvGeneratorError, generate_pdf


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(prog="cv-generator")
    subparsers = parser.add_subparsers(dest="command", required=True)
    pdf_parser = subparsers.add_parser(
        "generate-pdf",
        help="Convert a Markdown file to a PDF",
    )
    pdf_parser.add_argument(
        "-i",
        "--input",
        required=True,
        type=Path,
        help="Markdown file to convert",
    )
    pdf_parser.add_argument(
        "-o",
        "--output",
        required=True,
        type=Path,
        help="PDF file to write",
    )

    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 0

    try:
        generate_pdf(args.input, args.output)
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 1
    except IsADirectoryError as exc:
        print(exc, file=sys.stderr)
        return 1
    except UnicodeDecodeError:
        print("Input is not valid UTF-8.", file=sys.stderr)
        return 1
    except CvGeneratorError as exc:
        print(exc, file=sys.stderr)
        return 1
    return 0
```

Create `src/cv_generator/__main__.py`:

```python
import sys

from cv_generator.cli import main

sys.exit(main())
```

Replace `src/cv_generator/__init__.py` with an empty file (or a one-line package docstring). Delete:

```python
def main() -> None:
    print("Hello from cv-generator!")
```

In `pyproject.toml`, change:

```toml
[project.scripts]
cv-generator = "cv_generator.cli:main"
```

Then refresh the script wrapper:

```bash
uv sync
```

- [ ] **Step 4: Run CLI tests to verify they pass**

```bash
uv run pytest tests/test_cli.py -v
```

Expected: all passed.

- [ ] **Step 5: Update README**

Replace the **Status** and **Usage** sections in `README.md` so they match the working command. Do not mention the hello stub. Usage must show:

```bash
uv run cv-generator generate-pdf --input cv.md --output cv.pdf
uv run cv-generator generate-pdf -i cv.md -o cv.pdf
uv run cv-generator --help
uv run cv-generator generate-pdf --help
```

State that `--input` and `--output` are required, that an existing PDF at `--output` is overwritten, and that success prints nothing. Keep Requirements / Setup / Stack. Do not paste the design spec into `AGENTS.md`.

Status should say the `generate-pdf` command is available, not that the app is a stub.

- [ ] **Step 6: Run the full suite and smoke the installed script**

```bash
uv run pytest -v
```

Expected: all tests passed.

Smoke (do not add these files to the repo):

```bash
smoke_dir="$(mktemp -d)"
printf '# Hello\n\n- item\n' > "$smoke_dir/cv.md"
uv run cv-generator generate-pdf --input "$smoke_dir/cv.md" --output "$smoke_dir/cv.pdf"
uv run python -c "p='$smoke_dir/cv.pdf'; d=open(p,'rb').read(); assert d.startswith(b'%PDF'), d[:20]; print('ok', len(d))"
uv run python -m cv_generator generate-pdf -i "$smoke_dir/cv.md" -o "$smoke_dir/cv2.pdf"
uv run python -c "p='$smoke_dir/cv2.pdf'; d=open(p,'rb').read(); assert d.startswith(b'%PDF')"
uv run cv-generator >/tmp/cv-generator-noargs.err; echo "exit:$?"
```

Expected:

- First two conversions write `%PDF` files.
- `uv run cv-generator` with no args exits `2` (not a hello string).
- `uv run cv-generator generate-pdf --input ...` produces no stdout on success.

- [ ] **Step 7: Commit** (skip unless the user asked to commit)

```bash
git add src/cv_generator/cli.py src/cv_generator/__main__.py src/cv_generator/__init__.py pyproject.toml README.md tests/test_cli.py uv.lock
git commit -m "feat: add generate-pdf CLI for Markdown to PDF"
```

---

## Out of scope (do not do in this plan)

- Stdin/stdout, default output path, `--template`, custom CSS, YAML front matter, CV layout, Pygments, `--verbose`, Windows support.
- Phase B CV Jinja template.
- Git init / commits unless the user asks.
- Editing `AGENTS.md` or `notatki.md`.
