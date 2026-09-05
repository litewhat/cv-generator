# Agent instructions

## Project

Local CLI that turns Markdown CVs into PDFs with Jinja2 and WeasyPrint.

Do not duplicate this file into the README. Keep this file short and actionable.

## Operating boundaries

- Do not read or edit `.local/` or `.env`.
- Any Git state-changing operation or use of `git worktree` requires an explicit request from the developer (human). Read-only Git commands such as `status`, `log`, `diff`, and `show` need no explicit request.
- Ask before adding new dependencies, tools, or Markdown extensions.
- Do not edit `document.py` unless asked.

## Stack

- Python `>=3.14`, pin in `.python-version`
- uv for interpreter, venv (`.venv`), deps, and lockfile
- Packaged src layout: `src/cv_generator` and `src/lib`, build backend `uv_build` (`module-name = ["cv_generator", "lib"]`)
- Runtime: `jinja2`, `markdown`, `pyyaml`, `weasyprint`
- Dev: `pytest`, `ruff`, `ty` (installed by `uv sync`)

## Commands

```bash
uv sync
uv run python
uv run cv-generator generate-pdf -i cv.md -o cv.pdf
uv run pytest
uv run ty check
uv run ruff check src tests
uv run ruff check --fix src tests
uv run ruff format src tests
uv run ruff format --check src tests
uv add <package>
uv remove <package>
```

Do not use system Python or `pip`. Prefer `uv add` / `uv remove` over editing `pyproject.toml` dependencies by hand.

## Completion checks

- After behavior changes, run `uv run pytest`.
- For Python changes, also run `uv run ty check`, `uv run ruff check src tests`, and `uv run ruff format --check src tests`.

## Native deps (WeasyPrint)

cairo, pango, gdk-pixbuf, libffi (Homebrew on macOS). When changing PDF output, verify a real PDF (`%PDF` header / `HTML(...).write_pdf()`), not only `import weasyprint`.

Reuse the existing tests in `tests/lib/test_convert.py` and `tests/cv_generator/test_generate_pdf.py`, which generate real PDFs and check the `%PDF` header.

## Architecture

One Markdown path:

- `generate_pdf`: `Document.parse` → `formatter.to_html` → `lib.convert.html_to_pdf`. Atomic PDF write (mkdir, mkstemp, `os.replace`).
- `to_html` walks `document.content.nodes`, calls `lib.convert.markdown_to_html` on leaf strings, and renders `templates/elegant-v1.html.j2`.
- `from_markdown` (`src/cv_generator/parser.py`) must not import `document`. It returns a dict (`phone` → `phone_number`, `links` → `social_profiles`). `document.py` validates — do not move validation into the parser.
- PDF header fields are `phone_number` / `social_profiles` after parse aliases. The template binds `Content` fields (no `meta`, no `phone`, no `links` dict).
- `elegant-v1` only (ATS-safe single-column: no CSS grid, flex, or absolute).
- Load templates with `importlib.resources` (`cv_generator/templates/...`), not filesystem paths. Markdown extensions stay `fenced_code`, `tables`, `sane_lists`.
- Keep imports at module level.

Current behavior: importing `cv_generator.cli` eagerly loads `yaml` and `weasyprint` through its dependencies.

## Conventions

- Scope changes to what was asked. Do not scaffold the full app unprompted.
- English for code, comments, and docs unless the user writes in another language.
- Tests live under `tests/cv_generator/` and `tests/lib/`, one file per production module, grouped in pytest classes.

## Code search & token conservation rules

- Locate files with `rg --files -g '<pattern>'`, then search with `rg -n -F '<text>' <path>` in the narrowest relevant scope. Respect access restrictions and ignore rules; use `rg -l` when only filenames are needed.
- Read focused context around matches or specific line ranges; expand only as needed. Batch independent searches and reuse findings instead of repeating unchanged reads.
- For structural or multiline syntax searches, use `ast-grep` if available; otherwise use targeted `rg`. Do not install tooling without authorization.
- Narrow excessive or truncated output and rerun. Do not treat truncated output as complete or a failed search as proof of absence. Verify affected references and behavior, inspect the diff, and run required completion checks.
