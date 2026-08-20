# Agent instructions

## Project

Local CLI that will turn Markdown CVs into PDFs with Jinja2 and WeasyPrint. The toolchain is ready; `src/cv_generator` is still a uv-init stub. `notatki.md` is personal notes, not a spec — do not implement those ideas unless the user asks.

Do not duplicate this file into the README. Keep this file short and actionable.

## Stack

- Python `>=3.14`, pin in `.python-version`
- uv for interpreter, venv (`.venv`), deps, and lockfile
- Packaged src layout: `src/cv_generator`, build backend `uv_build`
- Libraries: `jinja2`, `markdown`, `weasyprint`

## Commands

```bash
uv sync
uv run python
uv run cv-generator
uv add <package>
uv remove <package>
```

Do not use system Python or `pip`. Prefer `uv add` / `uv remove` over editing `pyproject.toml` dependencies by hand.

## Native deps (WeasyPrint)

cairo, pango, gdk-pixbuf, libffi (Homebrew on macOS). When changing PDF output, verify a real PDF (`%PDF` header / `HTML(...).write_pdf()`), not only `import weasyprint`.

## Conventions

- Scope changes to what was asked. Do not scaffold the full app unprompted.
- English for code, comments, and docs unless the user writes in another language.
- No git init or commits unless requested.
