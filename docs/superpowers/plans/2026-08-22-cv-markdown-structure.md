# CV Markdown Structure — YAML Frontmatter + ATS Single Column (no Education) Implementation Plan

> **Status:** not implemented (verified against repo on 2026-08-25)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. REQUIRED: superpowers:test-driven-development — no production code without a failing test first.

**Goal:** Add a stable `cv.md` contract (YAML frontmatter header + linear `##` sections Summary/Experience/Skills/Projects, no Education) and wire it through the existing `generate-pdf` pipeline so `examples/cv.example.md` renders to an ATS-friendly single-column A4 PDF.

**Architecture:** Add one focused unit `frontmatter.py` that extracts/parses the `---` YAML block and returns `(meta, body)`. Extend `generate_pdf.py` to strip frontmatter before `markdown_to_html` and pass `meta` to `html_document`. Extend `html_document.py` + `templates/default-v1.html.j2` to render a header bar from `meta` (name/title/contacts/links) while keeping the body as a linear flow. No change to CLI argv contract, `markdown_to_html` extensions, or `html_to_pdf` lazy import.

**Tech Stack:** Python `>=3.14`, uv, `pyyaml` (new, via `uv add`), `markdown 3.10.x` (`fenced_code`, `tables`, `sane_lists`), `jinja2 3.1.x`, `weasyprint 69.x`, `pytest` (dev).

**Spec:** `docs/superpowers/specs/2026-08-22-cv-markdown-structure-design.md`

## Global Constraints

- Python `>=3.14`; uv only (no system Python, no `pip`). Prefer `uv add` / `uv remove` over hand-editing dependency lists.
- Native WeasyPrint libs: cairo, pango, gdk-pixbuf, libffi. Verify a real PDF (`%PDF` header / `HTML(...).write_pdf()`), not only `import weasyprint`.
- Stdlib `argparse` only (no Typer/Click) at `src/cv_generator/cli.py:8`.
- macOS and Linux only; Windows not a target.
- `--input` and `--output` are required; no stdin/stdout, no `-` path, no default output.
- `cli` never imports `weasyprint` or `yaml`. Convert modules never touch argparse/filesystem except `html_document` loading the packaged template.
- Success: exit 0, no stdout; existing `--output` overwritten; empty Markdown still produces valid PDF.
- `main` catches `SystemExit` and returns its code; `--help` returns 0; missing subcommand/flags returns 2; path/decode/render/`OSError` returns 1 (per `docs/superpowers/plans/2026-08-21-oserror-handler.md`).
- `markdown_to_html` extensions fixed at `src/cv_generator/markdown_to_html.py:3`: `fenced_code`, `tables`, `sane_lists`; no `codehilite`.
- Do not add two-column/sidebar/photo/Education/`--template`/custom CSS. Education fully omitted in examples/docs.
- `notatki.md` is personal notes, not a spec — ignore per `AGENTS.md:5`. Do not copy spec into `AGENTS.md`. No git commits unless user asks — skip Commit steps until then, but keep commands ready.
- TDD: watch each new test fail for the right reason before writing production code.

---

## File structure

| Path | Responsibility |
| --- | --- |
| `src/cv_generator/frontmatter.py` | **New** — `parse_frontmatter(text: str) -> tuple[dict, str]`; extracts leading `---` block, parses YAML with `yaml.safe_load`. |
| `src/cv_generator/generate_pdf.py:14` | Modify — call `parse_frontmatter` after UTF-8 read, pass `meta` to `html_document`; wrap YAML errors as `CvGeneratorError`. |
| `src/cv_generator/html_document.py:7` | Modify — signature `html_document(content: str, title: str, meta: dict \| None = None) -> str`; pass `meta` to template; keep `Markup(content)` + `autoescape=True`. |
| `src/cv_generator/templates/default-v1.html.j2:1` | Modify — add `header.cv-header` block rendered from `meta` (name/title/contacts/links) plus small CSS; keep `{{ content }}` body. |
| `src/cv_generator/markdown_to_html.py:3` | **No change** — keep fixed extensions. |
| `src/cv_generator/html_to_pdf.py:1` | **No change** — lazy WeasyPrint import preserved. |
| `examples/cv.example.md` | **New** — full SWE example, no `## Education`. |
| `examples/cv.skeleton.md` | **New** — commented skeleton, no `## Education`. |
| `tests/test_frontmatter.py` | **New** — in-memory frontmatter tests; must not import `weasyprint`. |
| `tests/test_html_document.py` | Extend — header rendering tests. |
| `tests/test_generate_pdf.py` | Extend — frontmatter integration tests. |
| `tests/test_cli.py` | Extend — one frontmatter happy-path CLI test (optional). |
| `pyproject.toml:9` | Modify via `uv add pyyaml` (do not hand-edit). `uv.lock` updated automatically. |
| `README.md:32` | Modify — add "CV Markdown format" section; show `examples/cv.example.md` usage. |

No extra `[tool.uv.build-backend]` package-data config unless a wheel build proves `default-v1.html.j2` missing.

---

### Task 1: `frontmatter` parser

**Files:**
- Create: `src/cv_generator/frontmatter.py`
- Create: `tests/test_frontmatter.py`
- Modify: `pyproject.toml` / `uv.lock` via `uv add pyyaml` (do once in this task)

**Interfaces:**
- Consumes: `yaml` (`pyyaml`) — `yaml.safe_load`
- Produces: `def parse_frontmatter(text: str) -> tuple[dict, str]` — `(meta, body)`. `meta` is dict (empty if no frontmatter). `body` is markdown without the `---` block. Raises `ValueError` on invalid YAML (caller wraps to `CvGeneratorError`).

Caller `generate_pdf` will import this. This module must not import `markdown`, `jinja2`, `weasyprint`, or `pathlib`.

- [ ] **Step 1: Add pyyaml**

```bash
uv add pyyaml
```

Check:

```bash
uv run python -c "import yaml; print(yaml.__version__)"
```

Expected: version printed, no error.

- [ ] **Step 2: Write the failing tests**

Create `tests/test_frontmatter.py`:

```python
import pytest

from cv_generator.frontmatter import parse_frontmatter


def test_no_frontmatter_returns_empty_meta_and_original_text():
    text = "# Hello\n\n- item\n"
    meta, body = parse_frontmatter(text)
    assert meta == {}
    assert body == text


def test_valid_frontmatter_extracted():
    md = """---
name: Alex Kowalski
title: Software Engineer
email: alex@example.com
location: Warsaw, Poland
links:
  github: https://github.com/alexkowalski
---
## Summary
Hello
"""
    meta, body = parse_frontmatter(md)
    assert meta["name"] == "Alex Kowalski"
    assert meta["title"] == "Software Engineer"
    assert meta["email"] == "alex@example.com"
    assert meta["location"] == "Warsaw, Poland"
    assert meta["links"]["github"] == "https://github.com/alexkowalski"
    assert body.startswith("## Summary")
    assert "---" not in body


def test_missing_closing_delimiter_treated_as_no_frontmatter():
    md = """---
name: Alex
## Summary
Hello
"""
    meta, body = parse_frontmatter(md)
    assert meta == {}
    assert body == md


def test_frontmatter_not_at_start_treated_as_body():
    md = "Intro\n---\nname: Alex\n---\n## Summary\n"
    meta, body = parse_frontmatter(md)
    assert meta == {}
    assert body == md


def test_invalid_yaml_raises_value_error():
    md = """---
name: [unclosed
---
## Summary
"""
    with pytest.raises(ValueError, match="YAML"):
        parse_frontmatter(md)


def test_crlf_and_whitespace_after_dashes():
    md = "---  \r\nname: Alex\r\n---\r\n## Summary\r\n"
    meta, body = parse_frontmatter(md)
    assert meta["name"] == "Alex"
    assert body.startswith("## Summary")


def test_empty_frontmatter_returns_empty_dict():
    md = "---\n---\n## Summary\n"
    meta, body = parse_frontmatter(md)
    assert meta == {}
    assert body.startswith("## Summary")
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
uv run pytest tests/test_frontmatter.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'cv_generator.frontmatter'`. Do not create the module until you see this.

- [ ] **Step 4: Write the minimal implementation**

Create `src/cv_generator/frontmatter.py`:

```python
import yaml


def parse_frontmatter(text: str) -> tuple[dict, str]:
    # Frontmatter must start at very first char with "---"
    if not text.startswith("---"):
        return {}, text

    # Find closing delimiter on its own line
    # Split into lines keeping endings to handle \n and \r\n
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text

    # Search for closing ---
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break

    if end_idx is None:
        return {}, text

    yaml_block = "\n".join(lines[1:end_idx])
    # Reconstruct body preserving original line breaks after closing ---
    # Use splitlines approach to handle \r\n
    # Find the position after the closing line in original text
    # Simpler: rejoin remaining lines with \n (normalized) — tests expect this
    body = "\n".join(lines[end_idx + 1 :])
    # Preserve trailing newline if original had it and body not empty?
    # Keep body as joined lines; if original ended with newline, ensure body ends correctly
    # For minimal v1, normalized \n is acceptable
    if not yaml_block.strip():
        meta: dict = {}
    else:
        try:
            loaded = yaml.safe_load(yaml_block)
        except yaml.YAMLError as exc:
            raise ValueError(f"Invalid YAML frontmatter: {exc}") from exc
        if loaded is None:
            meta = {}
        elif not isinstance(loaded, dict):
            raise ValueError(f"Invalid YAML frontmatter: expected mapping, got {type(loaded).__name__}")
        else:
            meta = loaded

    # Ensure meta is dict[str, any] — yaml may return non-str keys, but spec expects str keys
    if not isinstance(meta, dict):
        meta = {}
    return meta, body
```

Notes: Keep import at top (`import yaml`); this module does NOT import weasyprint. Error messages must contain "YAML" for test match.

- [ ] **Step 5: Run tests to verify they pass**

```bash
uv run pytest tests/test_frontmatter.py -v
```

Expected: 7 passed.

Also run existing suite to ensure no regression:

```bash
uv run pytest tests/test_markdown_to_html.py tests/test_html_document.py -q
```

Expected: still passed.

- [ ] **Step 6: Commit** (skip unless user asked to commit)

```bash
git add pyproject.toml uv.lock src/cv_generator/frontmatter.py tests/test_frontmatter.py
git commit -m "feat: parse YAML frontmatter from cv.md"
```

---

### Task 2: `html_document` header + template

**Files:**
- Modify: `src/cv_generator/html_document.py:7`
- Modify: `src/cv_generator/templates/default-v1.html.j2:1`
- Modify: `tests/test_html_document.py`

**Interfaces:**
- Consumes: `meta: dict | None` from caller; `content: str` (HTML fragment, already safe); `title: str`
- Produces: `def html_document(content: str, title: str, meta: dict | None = None) -> str` — must remain callable as `html_document(content, title)` for backward compat (existing tests at `tests/test_html_document.py:1` call with 2 args).

Do not import `weasyprint` or `yaml` here.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_html_document.py` (keep existing 4 tests at lines 8-25 from `docs/superpowers/plans/2026-08-20-markdown-to-pdf.md:170-201`):

```python
def test_html_document_with_meta_renders_header():
    html = html_document("<p>Body</p>", "Fallback", meta={"name": "Alex Kowalski", "title": "Software Engineer", "email": "alex@example.com", "location": "Warsaw, Poland", "links": {"github": "https://github.com/alex"}})
    assert "Alex Kowalski" in html
    assert "Software Engineer" in html
    assert "alex@example.com" in html
    assert "Warsaw, Poland" in html
    assert 'href="https://github.com/alex"' in html
    # Body still present
    assert "<p>Body</p>" in html


def test_html_document_meta_escapes_name():
    html = html_document("<p>x</p>", "t", meta={"name": "A < B", "title": "T"})
    assert "A &lt; B" in html
    assert "A < B" not in html.split("</header>")[0]  # header escaped


def test_html_document_without_meta_still_works():
    # Backward compat: 2-arg call
    html = html_document("<p>Hello</p>", "My Title")
    assert "<p>Hello</p>" in html
    assert "<title>My Title</title>" in html
    # Should not crash, header may show title as fallback or be minimal
    assert html.lstrip().startswith("<!DOCTYPE html>")


def test_html_document_none_meta_no_header_crash():
    html = html_document("<p>x</p>", "t", meta=None)
    assert "<p>x</p>" in html


def test_html_document_empty_meta_no_links():
    html = html_document("<p>x</p>", "t", meta={})
    assert "<p>x</p>" in html
    # No anchor when no links
    # At least not crash; ensure header logic handles empty dict
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_html_document.py -v
```

Expected: FAIL — either `TypeError: html_document() got an unexpected keyword argument 'meta'` or assertions about header content missing. If tests fail due to missing template header, that is correct; do not edit template yet.

- [ ] **Step 3: Update the template**

Edit `src/cv_generator/templates/default-v1.html.j2` to add header + CSS. Keep existing structure at `templates/default-v1.html.j2:1-49`; insert header block before `{{ content }}` and add CSS:

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
    .cv-header {
      border-bottom: 1.5px solid #ccc;
      margin-bottom: 1.2em;
      padding-bottom: 0.7em;
    }
    .cv-header h1 {
      margin: 0 0 0.15em;
      font-size: 20pt;
      line-height: 1.1;
    }
    .cv-title {
      margin: 0;
      font-size: 11pt;
      color: #333;
      font-weight: 500;
    }
    .cv-contacts, .cv-links {
      margin: 0.25em 0 0;
      font-size: 9pt;
      color: #444;
    }
    .cv-links a {
      color: #0a58ca;
      text-decoration: none;
    }
    h1, h2, h3, h4, h5, h6 {
      font-weight: 600;
      line-height: 1.25;
      margin: 1.2em 0 0.4em;
    }
    .cv-header h1 { margin: 0 0 0.15em; }
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
  {% if meta and (meta.name or meta.title or meta.email or meta.phone or meta.location or meta.links) %}
  <header class="cv-header">
    {% if meta.name %}<h1>{{ meta.name }}</h1>{% elif title %}<h1>{{ title }}</h1>{% endif %}
    {% if meta.title %}<p class="cv-title">{{ meta.title }}</p>{% endif %}
    {% set contacts = [] %}
    {% if meta.email %}{% set _ = contacts.append(meta.email) %}{% endif %}
    {% if meta.phone %}{% set _ = contacts.append(meta.phone) %}{% endif %}
    {% if meta.location %}{% set _ = contacts.append(meta.location) %}{% endif %}
    {% if contacts %}<p class="cv-contacts">{{ contacts | join(" | ") }}</p>{% endif %}
    {% if meta.links %}<p class="cv-links">{% for label, url in meta.links.items() %}<a href="{{ url }}">{{ label }}</a>{% if not loop.last %} | {% endif %}{% endfor %}</p>{% endif %}
  </header>
  {% endif %}
  {{ content }}
</body>
</html>
```

Ensure `{{ content }}` remains `Markup` unescaped; header fields are autoescaped.

- [ ] **Step 4: Update the implementation**

Edit `src/cv_generator/html_document.py:7` to:

```python
from importlib.resources import files

from jinja2 import Environment
from markupsafe import Markup


def html_document(content: str, title: str, meta: dict | None = None) -> str:
    template_text = (
        files("cv_generator") / "templates" / "default-v1.html.j2"
    ).read_text(encoding="utf-8")
    env = Environment(autoescape=True)
    template = env.from_string(template_text)
    # Normalize meta to dict or None for template
    if meta is not None and not isinstance(meta, dict):
        meta = {}
    return template.render(content=Markup(content), title=title, meta=meta)
```

Keep `autoescape=True` and `Markup(content)` so body HTML renders unescaped while `title` and `meta` values escape.

- [ ] **Step 5: Run tests to verify they pass**

```bash
uv run pytest tests/test_html_document.py -v
```

Expected: all 9 tests passed (4 original + 5 new).

Also verify template loads as package resource:

```bash
uv run python -c "from importlib.resources import files; t = (files('cv_generator') / 'templates' / 'default-v1.html.j2').read_text(encoding='utf-8'); assert 'cv-header' in t; print('template ok')"
```

- [ ] **Step 6: Commit** (skip unless user asked to commit)

```bash
git add src/cv_generator/html_document.py src/cv_generator/templates/default-v1.html.j2 tests/test_html_document.py
git commit -m "feat: render CV header from frontmatter meta"
```

---

### Task 3: Wire `generate_pdf` to frontmatter

**Files:**
- Modify: `src/cv_generator/generate_pdf.py:14`
- Modify: `tests/test_generate_pdf.py`
- Create (optional): `tests/test_cli.py` extension for frontmatter (or add one test there)

**Interfaces:**
- Consumes: `parse_frontmatter(text: str) -> tuple[dict, str]` from Task 1; `markdown_to_html`, `html_document` (now with `meta`), `html_to_pdf`
- Produces: `def generate_pdf(input_path: Path, output_path: Path) -> None` unchanged signature; now strips frontmatter, derives `title` from `meta.get("title") or meta.get("name") or input_path.stem`, wraps YAML errors as `CvGeneratorError`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_generate_pdf.py` (after existing tests at `tests/test_generate_pdf.py:110`):

```python
def test_generate_pdf_with_frontmatter_writes_valid_pdf(tmp_path: Path):
    md = """---
name: Alex Kowalski
title: Software Engineer
email: alex@example.com
links:
  github: https://github.com/alexkowalski
---
## Summary
Hello world

## Experience
### Acme — Engineer | Warsaw | 2021 — Present
- Built API
"""
    source = tmp_path / "cv.md"
    source.write_text(md, encoding="utf-8")
    output = tmp_path / "cv.pdf"
    generate_pdf(source, output)
    data = output.read_bytes()
    assert data.startswith(b"%PDF")
    assert len(data) > 0


def test_generate_pdf_without_frontmatter_still_writes_pdf(tmp_path: Path):
    source = tmp_path / "cv.md"
    source.write_text("## Summary\nHello\n", encoding="utf-8")
    output = tmp_path / "out.pdf"
    generate_pdf(source, output)
    assert output.read_bytes().startswith(b"%PDF")


def test_generate_pdf_invalid_yaml_raises_and_writes_no_output(tmp_path: Path):
    md = """---
name: [unclosed
---
## Summary
Hello
"""
    source = tmp_path / "bad.md"
    source.write_text(md, encoding="utf-8")
    output = tmp_path / "out.pdf"
    with pytest.raises(CvGeneratorError, match="YAML"):
        generate_pdf(source, output)
    assert not output.exists()
    leftovers = list(tmp_path.glob(".cv-generator-*.pdf"))
    assert leftovers == []


def test_generate_pdf_frontmatter_title_used_in_html(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    captured = {}

    def fake_html_document(content: str, title: str, meta=None):
        captured["title"] = title
        captured["meta"] = meta
        return "<html><head><title>t</title></head><body>doc</body></html>"

    def fake_html_to_pdf(html: str, *, base_url):
        return b"%PDF-1.4 fake"

    monkeypatch.setattr("cv_generator.generate_pdf.html_document", fake_html_document)
    monkeypatch.setattr("cv_generator.generate_pdf.html_to_pdf", fake_html_to_pdf)

    md = """---
name: Alex
title: Senior Engineer
---
## Summary
Hi
"""
    source = tmp_path / "cv.md"
    source.write_text(md, encoding="utf-8")
    output = tmp_path / "out.pdf"
    generate_pdf(source, output)
    assert captured["title"] == "Senior Engineer"
    assert captured["meta"]["name"] == "Alex"
    assert output.read_bytes().startswith(b"%PDF")
```

Optional CLI test — append to `tests/test_cli.py`:

```python
def test_cli_frontmatter_cv_succeeds(tmp_path: Path):
    md = """---
name: Alex
title: Engineer
email: alex@example.com
---
## Summary
Test
"""
    source = tmp_path / "cv.md"
    source.write_text(md, encoding="utf-8")
    out = tmp_path / "cv.pdf"
    from cv_generator.cli import main
    assert main(["generate-pdf", "-i", str(source), "-o", str(out)]) == 0
    assert out.read_bytes().startswith(b"%PDF")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_generate_pdf.py::test_generate_pdf_with_frontmatter_writes_valid_pdf -v
```

Expected: FAIL — either `TypeError` about `html_document` not accepting `meta` (if Task 2 not done) or `AssertionError` because frontmatter not stripped and header not rendered. The most informative failure before Task 3 code is that the PDF is still valid but the title test fails; isolate the `fake_html_document` test:

```bash
uv run pytest tests/test_generate_pdf.py::test_generate_pdf_frontmatter_title_used_in_html -v
```

Expected: `TypeError: html_document() got an unexpected keyword argument 'meta'` or `AssertionError` on title.

- [ ] **Step 3: Implement the wiring**

Edit `src/cv_generator/generate_pdf.py:14` — full file after edit:

```python
import os
import tempfile
from pathlib import Path

from cv_generator.frontmatter import parse_frontmatter
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
        meta, body = parse_frontmatter(text)
        fragment = markdown_to_html(body)
        title = meta.get("title") or meta.get("name") or input_path.stem
        document = html_document(fragment, title=title, meta=meta)
        pdf_bytes = html_to_pdf(document, base_url=input_path.parent)
    except (CvGeneratorError, FileNotFoundError, IsADirectoryError, UnicodeDecodeError):
        raise
    except ValueError as exc:
        # YAML parse error from frontmatter
        raise CvGeneratorError(str(exc)) from exc
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

Key points:
- `parse_frontmatter` called inside the `try` so `ValueError` wraps to `CvGeneratorError`.
- `title` derivation matches spec; fallback to `input_path.stem` preserves existing behavior for plain Markdown.
- `html_document` called with `meta` (dict, possibly empty).
- Re-raise the four types that `cli.py` maps explicitly; everything else becomes `CvGeneratorError`.

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_generate_pdf.py tests/test_frontmatter.py tests/test_html_document.py -v
```

Expected: all passed (existing + new). At least one test in this task hits real WeasyPrint (`test_generate_pdf_with_frontmatter_writes_valid_pdf` asserts `%PDF`).

Full suite:

```bash
uv run pytest -v
```

Expected: all 32 original + new tests passed (new count ~ 7 + 5 + 4 = 16 added).

- [ ] **Step 5: Smoke with real PDF**

```bash
smoke_dir="$(mktemp -d)"
cat > "$smoke_dir/cv.md" <<'MD'
---
name: Alex Kowalski
title: Software Engineer
email: alex@example.com
location: Warsaw, Poland
links:
  github: https://github.com/alexkowalski
---
## Summary
Hello world

## Skills
- **Languages:** Python, Go
MD
uv run cv-generator generate-pdf --input "$smoke_dir/cv.md" --output "$smoke_dir/cv.pdf"
uv run python -c "d=open('$smoke_dir/cv.pdf','rb').read(); assert d.startswith(b'%PDF'); print('frontmatter pdf ok', len(d))"
# Plain Markdown still works
printf '## Summary\nHello\n' > "$smoke_dir/plain.md"
uv run cv-generator generate-pdf -i "$smoke_dir/plain.md" -o "$smoke_dir/plain.pdf"
uv run python -c "d=open('$smoke_dir/plain.pdf','rb').read(); assert d.startswith(b'%PDF'); print('plain pdf ok')"
```

Expected: both `ok`.

- [ ] **Step 6: Commit** (skip unless user asked to commit)

```bash
git add src/cv_generator/generate_pdf.py tests/test_generate_pdf.py tests/test_cli.py
git commit -m "feat: wire frontmatter through generate_pdf to html_document"
```

---

### Task 4: Examples and README

**Files:**
- Create: `examples/cv.example.md`
- Create: `examples/cv.skeleton.md`
- Modify: `README.md:32`

**Interfaces:**
- Consumes: frontmatter schema + section order from spec.
- Produces: two example files with no `## Education`; README documents the contract.

- [ ] **Step 1: Create `examples/cv.example.md`**

```markdown
---
name: Alex Kowalski
title: Software Engineer
email: alex.kowalski@example.com
phone: "+48 123 456 789"
location: Warsaw, Poland
links:
  linkedin: https://linkedin.com/in/alexkowalski
  github: https://github.com/alexkowalski
  website: https://alexkowalski.dev
---

## Summary
Software Engineer with 6 years building backend systems in Python. Focus on APIs, data pipelines, and cloud infrastructure. Seeking a Senior SWE role where I can own services end-to-end.

## Experience

### Acme Corp — Software Engineer | Warsaw, PL | 2021 — Present
- Designed and shipped payments API serving 2M req/day; reduced p95 latency 38% (FastAPI, Postgres, Redis)
- Led migration of monolith to 4 services; improved deploy frequency 3× with Docker + GitHub Actions
- Mentored 2 junior engineers; introduced code review checklist adopted org-wide
- **Stack:** Python, Django, Postgres, AWS, Docker

### BetaLabs — Junior Software Engineer | Remote | 2018 — 2021
- Built ETL for 10M+ records/day (Python, Airflow, BigQuery)
- Automated test suite coverage 62% → 84%; cut incident MTTR 40%
- **Stack:** Python, Airflow, BigQuery, Linux

## Skills
- **Languages:** Python, Go, TypeScript, SQL
- **Backend:** Django, FastAPI, REST, Postgres, Redis
- **Cloud & Tools:** AWS (EC2, S3, RDS), Docker, CI/CD, Git, Linux
- **Practices:** TDD, Code Review, Agile

## Projects

### cv-generator — Markdown → PDF CLI | https://github.com/alexkowalski/cv-generator
- CLI that converts Markdown CV to A4 PDF via Jinja2 + WeasyPrint
- Atomic writes, UTF-8 validation, lazy WeasyPrint import

## Languages
- Polish — Native, English — C1
```

Verify: file contains `---` frontmatter, no line `## Education` (case-insensitive).

- [ ] **Step 2: Create `examples/cv.skeleton.md`**

```markdown
---
name: Your Name
title: Software Engineer
email: you@example.com
phone: "+48 000 000 000"
location: Warsaw, Poland
links:
  linkedin: https://linkedin.com/in/...
  github: https://github.com/...
---

## Summary
<!-- 2-3 lines tailored to the job, mirror its keywords -->

## Experience

### Company — Role | Location | Dates
- Achievement with metric (verb + result)
- Achievement
- **Stack:** Python, ...

## Skills
- **Languages:** Python, Go, SQL
- **Backend:** Django, FastAPI, Postgres, Redis
- **Cloud & Tools:** AWS, Docker, CI/CD, Linux
- **Practices:** TDD, Agile

## Projects

### Project Name — One-liner | https://github.com/...
- What you built and impact
```

- [ ] **Step 3: Update `README.md`**

Add a new section after **Usage** titled `## CV Markdown format`. Content:

```markdown
## CV Markdown format

CVs are authored as Markdown with optional YAML frontmatter for the header. No `Education` section in this version.

**Frontmatter** (must be first lines, closed with `---`):

name, title, email, phone, location, links (dict of label->URL). Unknown keys ignored.

**Body sections** (linear, ATS single-column):

## Summary -> ## Experience -> ## Skills -> ## Projects
Optional: ## Languages, ## Certifications. Each experience entry: `### Company — Role | Location | Dates` + `-` bullets.

**Tailoring:** keep `cv.master.md`, copy to `cv.acme.md`, edit `title`/`Summary`/`Skills` order to match the job.

**Examples:** `examples/cv.example.md` (full) and `examples/cv.skeleton.md` (skeleton). Generate with:

uv run cv-generator generate-pdf -i examples/cv.example.md -o cv.pdf
```

Keep existing Requirements/Setup/Stack sections unchanged. Do not mention Education beyond "intentionally omitted".

- [ ] **Step 4: Smoke the examples**

```bash
uv run cv-generator generate-pdf --input examples/cv.example.md --output /tmp/cv.example.pdf
uv run python -c "d=open('/tmp/cv.example.pdf','rb').read(); assert d.startswith(b'%PDF'); print('example pdf ok', len(d))"
uv run cv-generator generate-pdf -i examples/cv.skeleton.md -o /tmp/cv.skeleton.pdf
uv run python -c "d=open('/tmp/cv.skeleton.pdf','rb').read(); assert d.startswith(b'%PDF')"
# Verify no Education
grep -qi "## Education" examples/cv.example.md && echo "ERROR: Education found" || echo "no Education OK"
grep -qi "## Education" examples/cv.skeleton.md && echo "ERROR" || echo "skeleton no Education OK"
```

Expected: both PDFs `ok`, both greps `OK`.

- [ ] **Step 5: Run full suite**

```bash
uv run pytest -q
```

Expected: all passed.

- [ ] **Step 6: Commit** (skip unless user asked to commit)

```bash
git add examples/cv.example.md examples/cv.skeleton.md README.md
git commit -m "docs: add CV example and skeleton without Education"
```

---

## Self-Review

**1. Spec coverage:**
- Spec Goal: YAML frontmatter + linear sections without Education -> Task 1 (parser), Task 2 (header), Task 3 (wiring), Task 4 (examples without Education)
- Frontmatter schema: name/title/email/phone/location/links -> Task 1 + Task 2 header block
- Section order Summary/Experience/Skills/Projects, no Education -> Task 4 examples enforce; template does not special-case Education
- Data flow (parse -> markdown_to_html -> html_document with meta -> html_to_pdf -> atomic write) -> Task 3
- CLI contract unchanged + OSError handling preserved -> Task 3 re-raises correct types, Task 4 smoke via CLI
- Template header CSS single-column, no sidebar/photo -> Task 2
- Markdown extensions unchanged -> Task 3 calls `markdown_to_html(body)` with original extensions
- Errors: invalid YAML -> CvGeneratorError -> Task 1 + Task 3; missing closing -> treated as body -> Task 1
- Tests: frontmatter/html_document/generate_pdf layers -> Tasks 1-3

**2. Placeholder scan:** No TBD/TODO, no "add validation" vagueness; every step has concrete file paths, code blocks, and expected outputs. No "similar to Task N".

**3. Type consistency:** `parse_frontmatter: str -> tuple[dict, str]` used in `generate_pdf.py` as `meta, body = parse_frontmatter(text)`; `html_document(content: str, title: str, meta: dict | None = None) -> str` called as `html_document(fragment, title=title, meta=meta)`; `meta` dict keys lowercased strings matching spec.

---

## Out of scope (Do not do)

- Adding `## Education` back (fully omitted; re-add is future additive change)
- Two-column/sidebar/photo chrome
- `--template` / custom CSS flags
- Stdin/stdout, default output, `--verbose`, Pygments, Windows
- Editing `AGENTS.md` or `notatki.md`

