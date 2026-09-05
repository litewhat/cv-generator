# CV Generator review

Review of the current repository (working tree on `main`: `555fac0e3517f54d89b6d37da118d20f0f21a150`, clean). README.md and AGENTS.md were not reviewed, per request.

This document is for a follow-up agent that will implement fixes. Do not treat passing tests as proof that the issues below are intended product behavior. Several tests currently **encode** the bugs.

## How this review was done

1. Read all production modules under `src/cv_generator/` and `src/lib/`, the `elegant-v1` template, `pyproject.toml`, tests, and JSON examples.
2. Traced the Markdown → parse tree → HTML → PDF path, including error handling and atomic write.
3. Reproduced parser/formatter edge cases with `uv run python` against the installed package.
4. Ran `uv run pytest` (166 passed), `uv run ruff check src tests` (clean), and `uv run ty check` (12 diagnostics).

## Verdict

The happy path works: valid UTF-8 Markdown with YAML frontmatter becomes a real PDF (`%PDF` header), writes are atomic, and CLI exit codes 0/1/2 are wired. The serious problems are **silent wrong output**, not crashes. Realistic CV Markdown (wrapped bullets, a paragraph after a job’s bullet list, `2016. BSc …` education lines, missing images, empty social URLs) can produce a PDF with content in the wrong section, the wrong block type, or missing assets, while still exiting 0.

---

## Critical

These are correctness bugs. They produce a PDF with no error. Users will not notice unless they read the PDF carefully.

### C1. Nested heading is closed when any non-list leaf follows a list

- **Where:** `src/cv_generator/parser.py:106-112`
- **What:** After a list item, if the next block is a “paragraph” (anything that is not a fenced code block or a `---` line) and the heading stack is deeper than 1, the parser **pops the current heading** and attaches the new leaf to the parent.
- **Why it is wrong:** This is not how Markdown or CV structure works. It was introduced so this fixture stays “flat”:

  ```markdown
  ## Skills
  ### Platforms
  - AWS
  - GCP

  Spoken languages: English, Polish
  ```

  `tests/cv_generator/test_parser.py` (`test_mixed_children_under_a_heading`) and `tests/cv_generator/test_formatter.py` (`test_mixed_children_paragraphs_and_lists`) lock that in. The same heuristic breaks normal jobs.

- **Reproduced (wrapped list item — very common Markdown):**

  Input:

  ```markdown
  # Experience
  ## Software Engineer — Acme
  - Designed and implemented a distributed
    payment pipeline that reduced latency.
  ```

  Parse tree: the continuation line is **not** under the job. HTML:

  ```html
  <section class="cv-content__entry"><h2>Software Engineer — Acme</h2>
    <ul><li>Designed and implemented a distributed</li></ul>
  </section>
  <p>payment pipeline that reduced latency.</p>
  ```

- **Reproduced (paragraph after job bullets):**

  Input:

  ```markdown
  # Experience
  ## Software Engineer — Acme
  2020–2023
  - Built internal tools
  - Developed services

  Promoted to Staff in 2022.
  ```

  `"Promoted to Staff in 2022."` becomes a sibling of the job under Experience, not a child of the job. Keep-together (`cv-content__entry`) will not include it.

- **Also reparented by the same branch:** a table after a list; `***` after a list. Fences and `---` are special-cased to stay nested (`test_fence_after_list_stays_nested`, `test_thematic_break_after_list_stays_nested`), which proves the pop is deliberate and incomplete.

- **Fix:**
  1. Delete the `is_paragraph and prev_kind == "list" and len(stack) > 1` pop. Headings should close only via `close_until` (next heading of the same or shallower level, or EOF).
  2. Treat indented continuation lines of a list item as part of that item (or at least as children of the same heading), instead of as a new paragraph that triggers a pop.
  3. Update `test_mixed_children_under_a_heading` and `test_mixed_children_paragraphs_and_lists`: “Spoken languages…” should remain under `Platforms`, **or** change the sample Markdown so languages live under their own heading / before `Platforms`. Do not keep the heuristic to satisfy that fixture.
  4. Add tests for: wrapped bullet under a job; extra paragraph after job bullets; table after a list. All must stay inside the job node.

### C2. `2016. BSc …` (and any `N. text` with N ≥ 3 digits) renders as an ordered list

- **Where:**
  - Parser list regex: `src/cv_generator/parser.py:64` (`_LIST_ITEM`)
  - Formatter list regex: `src/cv_generator/formatter.py:12` and `:48`
  - Block conversion: `src/lib/convert.py:9-10` (`markdown.markdown` with default block parsing)
- **What:** A line like `2016. BSc Computer Science` matches `\d+\.` and is sent through `markdown_to_html` as a list. Python-Markdown emits `<ol start="2016"><li>BSc Computer Science</li></ol>`. The year disappears from visible text as a year and becomes an ordered-list start attribute.
- **Reproduced:**

  ```markdown
  # Education
  2016. BSc Computer Science
  ```

  → `<ol start="2016"><li>BSc Computer Science</li></ol>`

  This is a normal Education / Polish-style “year.” line. `2016) BSc` and `2020-2023` stay paragraphs; only the period form breaks.

- **Important interaction with C1:** parser classifies `2016. BSc` as `kind == "list"`. A following line (`University of Warsaw`) is then a paragraph after a list and will pop a nested heading.

- **Fix:** Parser/formatter must not treat year-like prefixes as lists. Product-wise, CV bullets are `-` / `*` / `+`; ordered lists if needed should be `1.` / `2.` (one or two digits), not years. That is **not enough** by itself: even if the parser stores `2016. BSc` as a paragraph, `markdown_to_html("2016. BSc Computer Science")` still returns `<ol start="2016">`. So:
  1. Restrict `_LIST_ITEM` (both copies) to `[-*+]` and optionally `\d{1,2}\.`.
  2. For paragraph leaves, either convert **inline** Markdown only (emphasis, code, links) or escape a leading `^\d+\.` before calling `markdown.markdown`.
  3. Add a test that `# Education\n\n2016. BSc Computer Science\n` yields a `<p>` containing `2016.` and does **not** contain `<ol`.
  4. Keep a test that `- item` / `* item` still become one `<ul>`.

---

## Important

Silent failures, misleading errors, or validation holes. Wrong output or a confusing failure; not always a corrupt PDF.

### I1. Unclosed fenced code block is not an error

- **Where:** `src/cv_generator/parser.py:143-161`
- **What:** If ` ``` ` / `~~~` never closes, the parser swallows the rest of the file into one leaf under the current heading. No `ParseError`. Unclosed YAML **does** raise (`parser.py:28`).
- **Observed:** Python-Markdown then does **not** treat the unclosed opener as a fence, so inner `# Heading` lines are interpreted as HTML headings inside that leaf. Tree and HTML disagree: later sections may still “look like” headings in the PDF but are not `Node`s (no `cv-content__entry`, wrong nesting).
- **Fix:** Raise `ParseError("Unclosed fenced code block")` when EOF is hit without a closer (same policy as unclosed frontmatter). Add a test that no PDF is written (`test_generate_pdf.py` already does this for unclosed YAML).

### I2. Missing images: conversion still exits 0

- **Where:** `src/lib/convert.py:13-17`, `src/cv_generator/generate_pdf.py:32`
- **What:** `![alt](missing.png)` becomes `<img src="missing.png">`. WeasyPrint logs `ERROR:weasyprint:Failed to load image …` (only if logging is configured) and still returns PDF bytes. `generate_pdf` succeeds. `html_to_pdf` only rejects a falsy return value; WeasyPrint returns a non-empty PDF even when the image is missing (reproduced: valid `%PDF-1.7`).
- **Fix:** Fail the run when WeasyPrint reports a failed fetch (WeasyPrint URL fetcher / logging handler, or a pre-pass over `img[src]` / `href` relative files). At minimum, map image load failures to `CvGeneratorError` and CLI exit 1. Add a test with a Markdown image whose file does not exist next to the `.md`.

### I3. Empty and whitespace-only social profile URLs are valid

- **Where:** `src/cv_generator/document.py:46-48` (`SocialProfile.from_mapping`)
- **What:** `url` must be a `str`, but it is not stripped and may be empty. Template renders `<a href="">github</a>` (`templates/elegant-v1.html.j2:206`).
- **Tests that encode the bug:** `tests/cv_generator/test_document.py` `test_from_mapping_empty_url_is_allowed`.
- **Fix:** Reject empty/whitespace URLs the same way as header fields (`_require_non_empty_str`). Flip the test to `pytest.raises(ValidationError, match="url")`. Optionally require `http://` / `https://`.

### I4. Blank line before `---` is treated as “no frontmatter”

- **Where:** `src/cv_generator/parser.py:19-21`
- **What:** Frontmatter is recognized only if line 0 strips to `---`. A leading newline makes the whole file the body. `Document.parse` then raises `ValidationError: Missing field 'name'` even though the file contains a complete header.
- **Reproduced:** CLI exit 1, stderr `Missing field 'name'\n`.
- **Fix:** Skip leading blank lines before looking for `---`, or raise `ParseError` that frontmatter must start the file. Do not report a missing `name` when the YAML is present but not detected. Add a test for `\n---\nname: …`.

### I5. `except Exception` turns every parse/render failure into `CvGeneratorError(str(exc))`

- **Where:** `src/cv_generator/generate_pdf.py:29-34`
- **What:**
  - Programming errors (`AttributeError`, `TypeError`) become a generic CLI exit 1.
  - `str(exc)` can be empty (`str(Exception()) == ""`), so the CLI can print a blank line and return 1 (`cli.py:51-53`).
  - WeasyPrint / OS errors during conversion are wrapped and no longer distinguishable from validation errors.
- **Fix:** Catch `ParseError`, `ValidationError`, and WeasyPrint/render errors explicitly. Re-raise `OSError` (and subclasses) so the existing CLI handler stays meaningful. Use `str(exc) or type(exc).__name__` if you keep a wrapper. Do not swallow unexpected exceptions in library code if the CLI should show a traceback for bugs.

### I6. `phone` / `links` silently overwrite `phone_number` / `social_profiles`

- **Where:** `src/cv_generator/parser.py:46-50`
- **What:** If both keys exist, the alias wins and the other value is dropped with no error.
- **Tests that encode this:** `test_phone_alias_wins_over_phone_number`, `test_links_alias_wins_over_social_profiles`.
- **Fix:** If both are present and differ, raise `ParseError`. If they are equal, keep one. Update those tests.

### I7. Raw HTML in Markdown is injected into the PDF

- **Where:** `src/lib/convert.py:9-10`; formatter passes the result as `Markup` (`formatter.py:30`).
- **What:** `markdown.markdown` allows raw HTML. Reproduced: `<span style="position:absolute">x</span>` survives. The template avoids CSS grid/flex/absolute (`test_shell_is_not_multi_column` only inspects the **template**, not user HTML). A CV can break the single-column / ATS-safe layout without any error.
- **Fix:** Prefer a safe conversion (escape HTML in source, or a sanitizer). If raw HTML stays allowed, document it; still consider stripping `style` / `position` / `display`. Add a test that `<div style="position:absolute">` does not reach the HTML (once fixed).

### I8. `ty check` does not pass

- **Where:** `src/cv_generator/document.py` (Mapping invariance; `~None` not iterable after `_is_sequence`); `tests/cv_generator/test_document.py` (passing `format="html"` and a list into typed APIs; `Node | str` attribute access); `tests/cv_generator/test_generate_pdf.py` (`captured` dict values typed as `object`).
- **What:** `uv run ty check` reports 12 diagnostics. Runtime tests still pass.
- **Fix:** Narrow types (`Mapping[str, object]`, `Sequence[object]` after the guard). In tests, use `cast` / `# type: ignore` only where you are **intentionally** passing invalid values, or split “invalid type at runtime” tests so they don’t fight the type checker.

---

## Suggestions

Improvements, weak tests, and coverage gaps. Not silent production bugs by themselves.

### S1. Tests that do not test what their names claim (or test nothing useful)

Remove, merge, or rewrite these so a later change cannot hide behind a green suite.

| Test                                                                                                                                                                 | Problem                                                                                                                                                                                                                                                   |
| -------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `tests/cv_generator/test_cli.py::test_os_error_from_replace_returns_1`                                                                                               | Monkeypatches `cli.generate_pdf` to raise `OSError`. Does **not** call `os.replace`. Duplicate of `test_os_error_returns_1`. Real replace failure is already covered in `test_generate_pdf.py::test_replace_failure_deletes_temp_and_keeps_old_output`.   |
| `test_os_error_returns_1` and `test_permission_error_returns_1`                                                                                                      | Same pattern: fake `generate_pdf`. One parametrized test of CLI `except OSError` is enough.                                                                                                                                                               |
| `test_document.py::test_validation_error_is_a_sibling_of_parse_error` and `test_parse_error_is_an_exception`                                                         | Class-hierarchy tautologies. Keep `test_parse_does_not_convert_parse_error_into_validation_error` if you need the split.                                                                                                                                  |
| `test_content_holds_all_header_fields_and_nodes`, `test_document_exposes_public_source_format_and_content`                                                           | Construct a dataclass and read fields back. No parse/validate/render.                                                                                                                                                                                     |
| `test_parser.py::test_from_markdown_does_not_import_document`                                                                                                        | Grep on source text; a comment mentioning `document` would fail. Prefer an import-graph test or drop it.                                                                                                                                                  |
| `test_generate_pdf.py::test_calls_to_html_with_parsed_document`                                                                                                      | `"<title>cv</title>" not in html` is a vacuous negative. Keep the positive title assertion.                                                                                                                                                               |
| `test_generate_pdf.py::test_html_to_pdf_base_url_is_markdown_parent`                                                                                                 | Mocks `html_to_pdf`, so WeasyPrint never resolves a relative image. Add a real test: image file next to the `.md`, assert it is embedded (PDF size / `pdftotext` cannot see images; use PDF object dump or a known byte length vs HTML-only).             |
| `test_formatter.py::test_elegant_v1_tokens_and_a4`                                                                                                                   | Coupled to hex colors and font names. Fine as a template-identity smoke test; do not treat it as layout correctness.                                                                                                                                      |
| `test_document.py::test_from_mapping_empty_url_is_allowed`                                                                                                           | Encodes I3. Invert it.                                                                                                                                                                                                                                    |
| `test_parser.py::test_links_as_string_is_copied_to_social_profiles`, `test_nested_link_value_is_copied_as_is`, `test_header_values_are_not_stripped_or_type_checked` | Document that the parser does not validate (that is the architecture). They are useful only if comments say “validation is in `document.py`”. Invalid `links` should still fail at `Document.parse` with a clear message — add **that** integration test. |

### S2. Missing tests that would have caught C1–C2 and I1–I4

Add focused tests (parser tree + HTML, and one `generate_pdf` smoke each):

- Wrapped list item under `## Job` stays in the job node.
- Paragraph after bullets stays in the job node.
- `2016. BSc Computer Science` stays a paragraph.
- Unclosed fence → `ParseError`, no output file.
- Leading blank line before frontmatter (I4).
- Empty `links.github: ""` → `ValidationError`.
- CLI: input path is a directory (generate_pdf has this; CLI does not).
- CLI: real incomplete header (not a monkeypatched `CvGeneratorError`) prints `Missing field '…'` and exit 1.
- Relative image that **exists** is embedded; missing image fails (after I2).
- Ordered vs unordered lists are not merged into one list if you keep both (`- a` then `1. b`).

Do not add tests that only re-read dataclass fields or CSS variable strings unless they guard a regression you have seen.

### S3. JSON examples are not parser goldens

`examples/cv_generator/document/*.json` are round-tripped through `Content.from_mapping` only. `mixed-children.json` stores `"AWS"` / `"GCP"` **without** `- ` prefixes; the Markdown parser would emit `"- AWS"`. There is no `.md` fixture whose parse tree equals these JSON files.

If examples are the schema, keep them. If they are meant to represent Markdown CVs, add matching `.md` files and assert `from_markdown` → `Content.from_mapping` → JSON.

### S4. Duplicated `_LIST_ITEM` regex

`parser.py` and `formatter.py` each define the same pattern. After C2, put the regex in one module (or a tiny shared constant in `lib` / `parser` imported by the formatter) so they cannot drift.

### S5. No autolink of bare URLs

`markdown_to_html("Visit https://example.com")` stays plain text. CVs often put portfolio URLs in bullets without `[text](url)`. Consider the `nl2br`/`extra` autolink story only if you add an extension (ask before adding Markdown extensions).

### S6. Hardcoded `lang="en"`

`templates/elegant-v1.html.j2:2`. Fine for the default template; a Polish CV will still declare English. Optional frontmatter `lang` later; not a bug.

### S7. Atomic write does not `fsync`

`generate_pdf.py:37-45` writes then `os.replace`. A crash mid-write leaves a temp file (cleanup on exception is good). A power loss after write without fsync can theoretically replace with a partial file. For this CLI, optional `flush` + `os.fsync(tmp_file.fileno())` before replace.

### S8. Temp-file cleanup can hide the original exception

`generate_pdf.py:46-51`: if `os.unlink` raises something other than `FileNotFoundError`, the original write/`replace` error is lost. Use `except OSError` on unlink, or `raise ... from` carefully.

### S9. `html_to_pdf` empty-bytes guard is effectively dead

WeasyPrint `write_pdf()` returned non-empty bytes for empty HTML (736 bytes in this environment). The `if not pdf` branch is untested. Keep it as a belt-and-suspenders check; mock it if you want coverage, don’t treat it as image-failure handling (see I2).

### S10. `pyproject.toml` description is still the placeholder

`description = "Add your description here"`. Packaging metadata only.

### S11. CLI `SystemExit` with non-int code becomes 0

`cli.py:37-38`: `return exc.code if isinstance(exc.code, int) else 0`. argparse uses 0 and 2. Unlikely, but a non-int code would look like success.

### S12. Social `type` / `url` error messages

Missing `type` → `Unsupported social profile type: None`. Missing `url` → `Field 'url' must be a string`. Prefer `Missing field 'type'` / `Missing field 'url'` for consistency with header errors.

---

## Test coverage — overall

The suite is large (166 tests) and **is** aligned with modules (`tests/cv_generator/test_*.py`, `tests/lib/test_convert.py`). Atomic PDF write, UTF-8, argparse, and header validation are genuinely covered.

What is weak is not “number of tests”; it is **what they assert**:

- Parser tests specify an unusual heading-pop after lists and never assert wrapped bullets or `2016.` lines.
- Document tests allow empty social URLs.
- Convert tests only check headings, fences, tables, `-` lists, and `%PDF` bytes — not images, ordered lists, or raw HTML.
- CLI tests over-mock `generate_pdf` instead of driving real validation failures.
- The only PDF text extraction test is skipped when `pdftotext` is missing (`test_pdf_text_is_linear_top_to_bottom`).

Prefer fewer tests that encode user-visible PDF/HTML structure over more tests that encode internal heuristics.

---

## Suggested fix order

1. **C1** — remove heading-pop; keep wrapped bullets and post-list paragraphs in the current heading. Update mixed-children tests.
2. **C2** — stop treating years as ordered lists in parser, formatter, and `markdown_to_html` for paragraph leaves.
3. **I1, I3, I4, I6** — fail closed (unclosed fence, empty URL, frontmatter detection, duplicate aliases).
4. **I2** — missing image → exit 1.
5. **I5, I8** — narrower exception handling.
6. **S1–S2** — delete misleading tests; add the regressions above.
7. **I7, I8, S4+** as follow-up.

`document.py` is where URL/header validation lives (`SocialProfile.from_mapping`, `_require_non_empty_str`). Parser must not grow validation. Formatter should not re-implement a second, drifting list grammar if you can share C2’s rule.

## Verification for the implementing agent

After fixes:

```bash
uv run pytest
uv run ty check
uv run ruff check src tests
uv run ruff format --check src tests
```

Re-run the reproductions in C1, C2, I1, I2, I3, I4 (real PDF, `%PDF` header, and HTML assertions — not mocks of `html_to_pdf` except where you are testing orchestration).
