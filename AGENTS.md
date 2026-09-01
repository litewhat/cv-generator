# Agent instructions

## Project

Local CLI that turns Markdown CVs into PDFs with Jinja2 and WeasyPrint. The `generate-pdf` command is implemented.

Do not duplicate this file into the README. Keep this file short and actionable.

## Stack

- Python `>=3.14`, pin in `.python-version`
- uv for interpreter, venv (`.venv`), deps, and lockfile
- Packaged src layout: `src/cv_generator`, build backend `uv_build`
- Runtime: `jinja2`, `markdown`, `pyyaml`, `weasyprint`
- Dev: `pytest` (installed by `uv sync`)

## Commands

```bash
uv sync
uv run python
uv run cv-generator generate-pdf -i cv.md -o cv.pdf
uv run pytest
uv add <package>
uv remove <package>
```

Do not use system Python or `pip`. Prefer `uv add` / `uv remove` over editing `pyproject.toml` dependencies by hand.

## Native deps (WeasyPrint)

cairo, pango, gdk-pixbuf, libffi (Homebrew on macOS). When changing PDF output, verify a real PDF (`%PDF` header / `HTML(...).write_pdf()`), not only `import weasyprint`.

## Architecture

Two separate Markdown paths — do not merge them unless asked:

- **PDF pipeline** (`generate_pdf`): `frontmatter.parse_frontmatter` → `markdown_to_html` → `html_document` → `html_to_pdf`. `html_document` hardcodes `templates/elegant-v1.html.j2`. Unused: `default-v1/v2/v3`.
- **Structured model** (`document.py` + `parse_markdown.py`): `Document` / `Content` / `Node` tree. Tests and JSON fixtures in `examples/cv_generator/document/`. Not used by `generate_pdf`. `parse_markdown` must not import `document`.
- Do not share or unify the two YAML frontmatter parsers. PDF keeps `phone` and `links`. The structured path aliases `phone` → `phone_number` and `links` → `social_profiles`. `parse_markdown` returns a dict; `document.py` validates — do not move validation into the parser.
- Load templates with `importlib.resources` (`cv_generator/templates/...`), not filesystem paths. Keep `elegant-v1` ATS-safe single-column (no CSS grid, flex, or absolute). Markdown extensions stay `fenced_code`, `tables`, `sane_lists`.
- Keep `weasyprint` and `yaml` lazy (not imported when loading `cv_generator.cli`).

## Git

- Only the developer (human) may commit, push, rebase, merge, or perform any other git state-changing operation (including `git init`, `amend`, `reset`, `cherry-pick`, `revert`, `tag`, `branch -d/-m`, `stash`, etc.). Coding agents must not change git state unless explicitly requested by the developer (human).
- Agents may use read-only git commands (`status`, `log`, `diff`, `show`) for inspection without explicit request.

## Conventions

- Scope changes to what was asked. Do not scaffold the full app unprompted.
- English for code, comments, and docs unless the user writes in another language.
- Only use `git worktree` when explicitly instructed; never create or use worktrees otherwise.
- Tests live in `tests/` (one file per module). Run `uv run pytest` after behavior changes.
- Ask before adding a dependency or new tooling (ruff, mypy, formatters, extra Markdown extensions).
- Do not read or edit `.local/` or `.env`.
