# Agent instructions

## Project

Local CLI that turns Markdown CVs into PDFs with Jinja2 and WeasyPrint. The `generate-pdf` command is implemented.

Do not duplicate this file into the README. Keep this file short and actionable.

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

## Native deps (WeasyPrint)

cairo, pango, gdk-pixbuf, libffi (Homebrew on macOS). When changing PDF output, verify a real PDF (`%PDF` header / `HTML(...).write_pdf()`), not only `import weasyprint`.

## Architecture

One Markdown path:

- `generate_pdf`: `Document.parse` → `formatter.to_html` → `lib.convert.html_to_pdf`. Atomic PDF write (mkdir, mkstemp, `os.replace`).
- `to_html` walks `document.content.nodes`, calls `lib.convert.markdown_to_html` on leaf strings, and renders `templates/elegant-v1.html.j2`.
- `from_markdown` (`parse.py`) must not import `document`. It returns a dict (`phone` → `phone_number`, `links` → `social_profiles`). `document.py` validates — do not move validation into the parser. Do not edit `document.py` unless asked.
- PDF header fields are `phone_number` / `social_profiles` after parse aliases. The template binds `Content` fields (no `meta`, no `phone`, no `links` dict).
- `elegant-v1` only (ATS-safe single-column: no CSS grid, flex, or absolute). `default-v1/v2/v3` are gone.
- Load templates with `importlib.resources` (`cv_generator/templates/...`), not filesystem paths. Markdown extensions stay `fenced_code`, `tables`, `sane_lists`.
- Imports are module-level. Importing `cv_generator.cli` loads `yaml` and `weasyprint`.

## Git

- Only the developer (human) may commit, push, rebase, merge, or perform any other git state-changing operation (including `git init`, `amend`, `reset`, `cherry-pick`, `revert`, `tag`, `branch -d/-m`, `stash`, etc.). Coding agents must not change git state unless explicitly requested by the developer (human).
- Agents may use read-only git commands (`status`, `log`, `diff`, `show`) for inspection without explicit request.

## Conventions

- Scope changes to what was asked. Do not scaffold the full app unprompted.
- English for code, comments, and docs unless the user writes in another language.
- Only use `git worktree` when explicitly instructed; never create or use worktrees otherwise.
- Tests live under `tests/cv_generator/` and `tests/lib/`, one file per production module, grouped in pytest classes. Run `uv run pytest` after behavior changes.
- Ask before adding a dependency or new tooling (ruff, mypy, formatters, extra Markdown extensions).
- Do not read or edit `.local/` or `.env`.

## Code search & token conservation rules

- Do NOT load whole files into context without locating the target line numbers first.
- ALWAYS use ripgrep (rg) to search for function names, classes, variables, and string literals.
  - Example: rg -n "get_user_data" src/
- USE ast-grep (sg) when searching for specific code structures across varying formatting, indentation, or signatures.
  - Example (Async functions): ast-grep run --pattern 'async def $NAME($ARGS): $$$' --lang python src/
  - Example (Decorators): ast-grep run --pattern '@$DECORATOR\ndef $NAME($ARGS): $$$' --lang python src/
- Fetch ONLY minimal context blocks around matching results (use ripgrep's -C flag or inspect strictly defined line ranges).
