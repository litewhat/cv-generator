# CV Markdown Structure — YAML Frontmatter + ATS Single Column (no Education)

> **Status:** not implemented (verified against repo on 2026-08-25)

Date: 2026-08-22

## Goal

Define a stable `cv.md` input contract and extend the existing `generate-pdf` pipeline so a recruiter-ready, ATS-friendly single-column CV can be authored in Markdown and rendered to A4 PDF. The contract uses YAML frontmatter for structured header data and linear `##` sections for body content. The `Education` section is intentionally omitted in this version.

```bash
uv run cv-generator generate-pdf --input cv.md --output cv.pdf
uv run cv-generator generate-pdf -i examples/cv.example.md -o cv.pdf
```

Success: a Markdown file following the contract below exits 0, writes a valid PDF (`%PDF` header) at `--output`, shows a styled header (name/title/contacts), and renders Summary, Experience, Skills, Projects as linear sections. Plain Markdown without frontmatter still renders (header falls back to `input_path.stem`).

## Non-goals

- Two-column / sidebar layout
- Photo, age, full address, or other EU-style chrome
- `Education` section (deferred; re-adding later is additive via plain `## Education`)
- `--template` or custom CSS flags (Phase B)
- Stdin/stdout or `-` path, default output path
- Pygments / `codehilite` / syntax highlighting
- `--verbose`
- Windows support (macOS and Linux only)

## Architecture

Extend the existing 5-unit pipeline; add one focused unit for frontmatter.

```
src/cv_generator/
  __init__.py
  __main__.py
  cli.py                 # unchanged argv contract
  generate_pdf.py        # now: frontmatter strip -> markdown_to_html -> html_document -> html_to_pdf
  frontmatter.py         # NEW: parse_frontmatter(text) -> (meta, body)
  markdown_to_html.py    # fragment only, unchanged extensions
  html_document.py       # fragment + title + meta -> full HTML (header)
  html_to_pdf.py         # full HTML -> PDF bytes
  templates/
    default-v1.html.j2      # document shell + header CSS
examples/
  cv.example.md          # full example, no Education
  cv.skeleton.md         # commented skeleton, no Education
```

| Unit | Does | Depends on | Does not |
| --- | --- | --- | --- |
| `frontmatter` | Extract YAML `---` block at start of file, parse with `yaml.safe_load`, return `(meta, body)` | `yaml` (pyyaml) | files, Jinja, WeasyPrint, argparse |
| `generate_pdf` | Validate paths, read UTF-8, call `parse_frontmatter`, call three convert steps, atomic write | `frontmatter`, convert modules, `pathlib` | argparse |
| `markdown_to_html` | Markdown string -> HTML fragment | `markdown` | files, Jinja, WeasyPrint, frontmatter |
| `html_document` | Fragment + title + meta -> full HTML (Jinja) | Jinja2, packaged template | files (except template), WeasyPrint |
| `html_to_pdf` | Full HTML + `base_url` -> PDF bytes | WeasyPrint | files, Markdown, Jinja, frontmatter |
| `cli` | Parse argv, map exceptions to exit codes | `generate_pdf` | Markdown, Jinja, WeasyPrint, yaml |

`cli` never imports `weasyprint` or `yaml`. Convert modules never touch argparse or filesystem except `html_document` loading the template.

## Public functions

```python
def parse_frontmatter(text: str) -> tuple[dict, str]: ...
# (meta, body) — meta is dict from YAML, body is markdown without frontmatter
# No frontmatter -> ({}, text). Invalid YAML -> raises ValueError (wrapped by generate_pdf).

def markdown_to_html(markdown_text: str) -> str: ...
# unchanged

def html_document(content: str, title: str, meta: dict | None = None) -> str: ...
# meta optional for backward compat; renders header when present

def html_to_pdf(html: str, *, base_url: str | Path) -> bytes: ...

def generate_pdf(input_path: Path, output_path: Path) -> None: ...

def main(argv: list[str] | None = None) -> int: ...
```

`generate_pdf` wraps frontmatter/YAML parse errors as `CvGeneratorError` (like WeasyPrint errors). `html_document` keeps `(content, title)` order so existing calls remain valid.

## Data flow

1. CLI parses `generate-pdf --input/--output` (also `-i`/`-o`) — unchanged.
2. `generate_pdf`:
   - Reject missing input, non-files, directory outputs (existing).
   - Read input as UTF-8 (existing).
   - `meta, body = parse_frontmatter(text)` — new step; `ValueError` on bad YAML -> `CvGeneratorError`.
   - `fragment = markdown_to_html(body)` — unchanged extensions `fenced_code`, `tables`, `sane_lists`.
   - `title = meta.get("title") or meta.get("name") or input_path.stem`
   - `document = html_document(fragment, title=title, meta=meta)`
   - `pdf = html_to_pdf(document, base_url=input_path.parent)`
   - Atomic write via `tempfile.mkstemp(dir=output_path.parent)` + `os.replace` (existing).
3. CLI returns `0`.

Empty Markdown and Markdown without frontmatter still produce a valid PDF (meta empty, header shows title only).

## CLI contract

Unchanged from v1:

```bash
uv run cv-generator generate-pdf --input cv.md --output cv.pdf
uv run cv-generator generate-pdf -i cv.md -o cv.pdf
uv run cv-generator --help
uv run cv-generator generate-pdf --help
```

- `generate-pdf` is the only subcommand.
- `--input` and `--output` required; no stdin/stdout.
- Existing `--output` overwritten; success exit 0, no stdout; errors exit 1 with short stderr, usage errors exit 2.

Add `OSError` handling from `docs/superpowers/plans/2026-08-21-oserror-handler.md` remains in place.

## Frontmatter schema

Only structured data that benefits from distinct header styling. All narrative stays in Markdown body.

```yaml
---
name: Paweł Zielonka        # required for header h1; fallback to title/stem if missing
title: Software Engineer     # required; also used as <title> fallback
email: lite.what@gmail.com   # optional but recommended
phone: "+48 000 000 000"     # optional
location: Warsaw, Poland     # city + country only; no full address
links:
  linkedin: https://linkedin.com/in/...
  github: https://github.com/...
  website: https://example.com   # optional, any key allowed; values are URLs
---
```

- Top-level keys are lowercased strings; unknown keys are ignored by template (future-proof).
- `links` is a dict of label->URL; template renders each as `<a href>`.
- No `summary`, `skills`, or other body content in frontmatter.
- File must start with `---\n` on the first line; closing `---` must be on its own line. If not found, parser treats entire file as body (no frontmatter). Whitespace after `---` is allowed; `\r\n` tolerated.
- Invalid YAML raises `ValueError` with `yaml.YAMLError` message; `generate_pdf` wraps it as `CvGeneratorError` -> CLI exit 1.

## Markdown body contract

Target: Software Engineer (general), ATS-friendly single column, 1-2 pages, tailored per job via `cv.master.md` -> `cv.acme.md` copy.

Order (default, fully without Education):

```
## Summary
## Experience
## Skills
## Projects
# optional: ## Languages, ## Certifications — add only if relevant
```

Rules:

- Frontmatter ends, then body starts immediately. No `h1` in body — `h1` is reserved for `meta.name` in header. Top sections are `##` (h2).
- `## Summary`: 2-3 lines, mirror job keywords; first section for recruiter scan.
- `## Experience`: each entry is `### Company — Role | Location | Dates` (h3) on one line, followed by `-` bullets (verb + metric). Dates format `2021 — Present` or `2018 — 2021`. Last line may be `**Stack:** ...`.
- `## Skills`: bullet list grouped by category: `- **Languages:** Python, Go` . Do not use tables for skills (ATS parses bullets more reliably); `sane_lists` already enabled.
- `## Projects`: 2-3 entries max, same h3 pattern: `### name — One-liner | https://...`, then 1-2 bullets.
- Tailoring: edit `title` in frontmatter, `Summary` paragraph, and reorder `Skills` bullets to match job stack; optionally delete a `Projects` entry. Do not change heading levels.

No `## Education` heading in examples, tests, or docs for this version. Adding it later requires no code change (plain Markdown heading flows through `markdown_to_html`).

## Template

`src/cv_generator/templates/default-v1.html.j2` remains a complete HTML5 page loaded via `importlib.resources.files("cv_generator") / "templates" / "default-v1.html.j2"`.

Variables:

- `content` — HTML fragment (Markup, unescaped), same as before.
- `title` — string for `<title>` (from frontmatter or stem, escaped).
- `meta` — dict or None (new). When present, template renders a header bar:

```html
<header class="cv-header">
  <h1>{{ meta.name }}</h1>
  {% if meta.title %}<p class="cv-title">{{ meta.title }}</p>{% endif %}
  {% if meta.email or meta.phone or meta.location %}
  <p class="cv-contacts">... joined by " | " ...</p>
  {% endif %}
  {% if meta.links %}<p class="cv-links">... each as <a> joined by " | " ...</p>{% endif %}
</header>
```

CSS (inline, single-column):

- `@page { size: A4; margin: 2cm; }` preserved.
- Add `.cv-header { border-bottom: 1px solid #ccc; margin-bottom: 1.2em; padding-bottom: 0.6em; }`, `.cv-header h1 { margin: 0 0 0.2em; font-size: 20pt; }`, `.cv-title { margin: 0; color: #333; font-size: 11pt; }`, `.cv-contacts, .cv-links { margin: 0.2em 0 0; font-size: 9pt; color: #444; }`, links `color: #0a58ca; text-decoration: none;`.
- No sidebar, no photo, no two-column grid.
- `autoescape=True` already set in `html_document.py:11`; use `{{ meta.name }}` etc escaped, `{{ content }}` as `Markup` unescaped.

Backwards compat: if `meta` is None/empty, header shows only `title` as h1? Actually show `title` as h1 when `name` missing, to keep PDFs without frontmatter still have a title.

## Markdown extensions

Unchanged: `fenced_code`, `tables`, `sane_lists` at `src/cv_generator/markdown_to_html.py:3`. No `codehilite`. Tables remain available for body if needed, but `Skills` uses lists.

## Errors

Add one row to `generate_pdf` contract:

| Situation | Where | Exit | stderr |
| --- | --- | --- | --- |
| Invalid YAML frontmatter | `parse_frontmatter` -> `generate_pdf` | 1 | `CvGeneratorError: <yaml message>` |
| Frontmatter not closed / not at start | `parse_frontmatter` | 0 (treated as no frontmatter) | — |

Existing errors unchanged: missing input, output is directory, not UTF-8, WeasyPrint failure, `OSError` on atomic write (per `2026-08-21-oserror-handler.md`).

## Tests

| Layer | Assert | I/O |
| --- | --- | --- |
| `frontmatter` | No frontmatter passthrough, valid extraction, missing closing treated as body, invalid YAML raises ValueError, `\r\n` and whitespace handling, `links` dict preserved | in-memory |
| `html_document` | With/without meta renders; `meta.name` escaped; links rendered as anchors; `content` not escaped; `@page` still present; header absent when meta empty | in-memory |
| `markdown_to_html` | Unchanged (heading, fenced code, table, ul) | in-memory |
| `html_to_pdf` | Bytes start with `%PDF` | in-memory (real WeasyPrint) |
| `generate_pdf` | Frontmatter file writes valid PDF; plain Markdown still works; invalid YAML raises `CvGeneratorError` and writes no output; overwrites existing PDF | temp files |
| `cli` | Unchanged (exit codes); add one check that frontmatter PDF via CLI succeeds | temp files + `main(argv)` |
| `examples` | `examples/cv.example.md` and `skeleton.md` contain no `## Education` | file existence |

`html_document` and `frontmatter` tests must not import `weasyprint`.

## Docs to update

- `examples/cv.example.md` and `examples/cv.skeleton.md` — new, no Education.
- `README.md` — add "CV Markdown format" section: frontmatter schema, section order (Summary/Experience/Skills/Projects), tailoring workflow, mention that Education is intentionally omitted in this version, show `examples/cv.example.md` usage.
- Do not edit `AGENTS.md`; `notatki.md` is personal notes (per `AGENTS.md:5`).

## Future work

- Re-add `## Education` as an optional linear section (no code change) or as a distinct template block if a sidebar is desired later.
- `--template` flag and custom CSS.
- Optional `--validate` flag that checks frontmatter keys against schema.

