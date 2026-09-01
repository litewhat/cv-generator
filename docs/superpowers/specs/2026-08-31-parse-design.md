# Document.parse design

Date: 2026-09-01

## Problem

`Document` and `Data` in `src/cv_generator/document.py` are the in-memory CV. Today that split is an envelope:

```python
Document(format: Literal["markdown"], data: Data)
Data(name, title, email, phone_number, location, social_profiles, nodes)
```

`parse_markdown` imports those types, returns `Data`, and validates required header fields. `Document.parse` only checks `format` and wraps the `Data`. That mixes three jobs in the parser: markdown/YAML syntax, CV field mapping, and schema checks.

Parsing and validation are separate concepts with separate exceptions. `parse_markdown` should return an open dict. `Content.from_mapping` is the schema. `Document.parse` is the public factory: source text in, a complete `Document` out (dispatch + wrap). The envelope stays, with clearer names: `Data` becomes `Content`, `data` becomes `content`, and `format` becomes `source_format` (the format of the parsed source).

Today’s PDF pipeline still does `parse_frontmatter` → markdown body → HTML. This work does not rewire that path.

## Scope

One change: split parse and validation, and rename the envelope. Do **not** flatten `Content` into `Document`. Do **not** land an intermediate `parse_markdown` that returns a typed `Document` (or still-typed `Data` / `Content`) with mixed parse+validation.

- Rename `Data` → `Content`, `Document.data` → `Document.content`, `Document.format` / `parse(..., format=)` → `source_format`.
- `parse_markdown` returns an open dict and does not import `document.py`.
- `Content.from_mapping` is the schema.
- `Document.parse` orchestrates: `source_format` dispatch → `parse_markdown` → `Content.from_mapping` → `Document(source_format, content)`.
- `ParseError` vs `ValidationError` vs `ValueError`. Details below.
- Remove the unused `validate_document` stub (it is dead).
- Files: `src/cv_generator/document.py`, `src/cv_generator/parse_markdown.py`, `tests/test_document.py`, `tests/test_parse_markdown.py`.
- Out of scope: `generate_pdf`, `frontmatter.py`, templates, HTML/PDF tests.

**Follow-up (not this work):** point `generate_pdf` at `Document.parse`, then remove `frontmatter.py` and `tests/test_frontmatter.py`. Do not break the current PDF command in this change.

## Public API

```python
# parse_markdown.py — does not import document.py
class ParseError(Exception):
    """Invalid CV source text."""

def parse_markdown(text: str) -> dict[str, object]: ...


# document.py
from cv_generator.parse_markdown import ParseError, parse_markdown

class ValidationError(Exception):
    """Parsed mapping does not match the content schema."""

type SocialProfileType = Literal["github", "linkedin"]
type NodeContent = Node | str

@dataclass(frozen=True, slots=True)
class SocialProfile:
    type: SocialProfileType
    url: str

@dataclass(frozen=True, slots=True)
class Node:
    name: str
    nodes: tuple[NodeContent, ...]

@dataclass(frozen=True, slots=True)
class Content:
    name: str
    title: str
    email: str
    phone_number: str
    location: str
    social_profiles: tuple[SocialProfile, ...]
    nodes: tuple[NodeContent, ...]

    @classmethod
    def from_mapping(cls, raw: Mapping[str, object]) -> Content: ...

@dataclass(frozen=True, slots=True)
class Document:
    source_format: Literal["markdown"]
    content: Content

    @staticmethod
    def parse(
        text: str,
        *,
        source_format: Literal["markdown"] = "markdown",
    ) -> Document: ...
```

- `Document` is the envelope: stored `source_format` plus `content`. `Content` is the parsed CV: header fields, social profiles, and node tree. No `_data is None`, no `**options`. There is no `Data` type and no `format` / `data` fields.
- Input is source **text**. File I/O stays in `generate_pdf`.
- `parse` is a factory. Tests may still construct `Content(...)` and `Document(source_format=..., content=...)` directly.
- `source_format=` on `parse` is dispatch (which parser to run) **and** is stored on the instance (`document.source_format`). It names the format of the parsed source. Only `"markdown"` is supported.
- `SocialProfile`, `Node`, `NodeContent`, `SocialProfileType` stay as they are (`"github" | "linkedin"`).
- Fields are public, not underscored.
- `ParseError` is defined in `parse_markdown.py` and **re-exported** from `document.py`. Callers should not be able to `from cv_generator.document import ParseError`.
- `ValidationError` is defined only in `document.py`. The parser must not import or raise it.
- Schema entry is `Content.from_mapping`. There is no `Document.from_mapping`. There is no `schema=` argument. Nested `SocialProfile.from_mapping` / `Node.from_mapping` are allowed as implementation.
- Do not export `parse_markdown` from `cv_generator/__init__.py`.

## Components

| Module              | Role                                                                                                                                               |
| ------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| `parse_markdown.py` | `ParseError`; `parse_markdown(text) -> dict` (YAML split, aliases, body walk)                                                                      |
| `document.py`       | `ValidationError`, model types (`Content`, `Document`, `Node`, `SocialProfile`), `Content.from_mapping`, `Document.parse`; re-exports `ParseError` |
| `frontmatter.py`    | Not part of parse. Stays until `generate_pdf` is rewired (follow-up)                                                                               |

Import direction: `document.py` may import `parse_markdown.py` at **module level**. `parse_markdown.py` must not import `document.py`. The lazy import inside `Document.parse` goes away.

`Document.parse`:

1. If `source_format != "markdown"`, raise `ValueError` (not `ParseError`, not `ValidationError`).
2. `raw = parse_markdown(text)`.
3. Return `Document(source_format=source_format, content=Content.from_mapping(raw))`.

It does not catch `ParseError` or `ValidationError`. It does not convert one into the other.

`parse_markdown` does not return `Content` or `Document` and does not know about `source_format`. YAML split helpers are private in that module. Callers of parse do not use `parse_frontmatter`.

Out of scope: Jinja templates, `markdown_to_html`, HTML/PDF, growing `SocialProfileType`, new dependencies (no pydantic, no jsonschema).

## Data flow

```
text → parse_markdown → open dict → Content.from_mapping → Content → Document(source_format, content)
         ParseError                      ValidationError
```

### `parse_markdown(text) -> dict`

1. Strip a leading BOM if present.
2. Split optional YAML frontmatter from the body (same delimiter rules as `parse_frontmatter`: file must start with a `---` line, closed by a later `---` line, body is the remainder). `----` is not an opener.
3. Copy the YAML mapping into a dict. Apply aliases. Extra top-level YAML keys stay.
4. Walk the body into `nodes` (always set; never taken from YAML).
5. Return the dict. Lists, not tuples. No `Content` / `Document` / `Node` / `SocialProfile` instances.

Empty YAML / `loaded is None` / missing opener → treat metadata as `{}`. Unclosed `---`, `yaml.YAMLError`, or a non-mapping loaded value → `ParseError`.

The dict is **Content-shaped**: keys `name`, `title`, `email`, `phone_number`, `location`, `social_profiles`, `nodes` (plus any extra YAML keys). It is not `{source_format, content}` and not `{format, data}`. Example JSON under `examples/cv_generator/document/*.json` already matches this shape.

### Header aliases (normalization, not validation)

Authoring keys in YAML:

| YAML       | Dict key          |
| ---------- | ----------------- |
| `name`     | `name`            |
| `title`    | `title`           |
| `email`    | `email`           |
| `phone`    | `phone_number`    |
| `location` | `location`        |
| `links`    | `social_profiles` |

Copy the YAML mapping, then apply aliases (`phone` → `phone_number`, `links` → `social_profiles`) and **delete** the authoring keys. If both `phone` and `phone_number` exist, the value from `phone` wins. Values are copied as YAML loaded them (no type check, no strip, no required-key check). Missing YAML keys are **absent** from the dict, not filled with defaults.

**`links` → `social_profiles`:**

| `links`         | Result                                                                                                                                                      |
| --------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| absent          | no `social_profiles` key                                                                                                                                    |
| `null` or `{}`  | `"social_profiles": []`                                                                                                                                     |
| mapping         | `[{"type": <yaml key>, "url": <yaml value>}, ...]` in YAML key order. Unknown types (e.g. `twitter`) included. Values copied as-is (including non-strings). |
| any other value | `"social_profiles": <that value>`                                                                                                                           |

`nodes` is always present after the body walk. Empty body → `"nodes": []`.

### Body grammar

Restricted markdown subset. Inline markdown in leaves is **source text**, not HTML. Do not run the body through `markdown_to_html` during parse.

Parser `nodes` are JSON-shaped: a `str` leaf, or `{"name": str, "nodes": list}` for a heading. Mixed children allowed.

| Block                                                                               | Result                                                                                          |
| ----------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| ATX heading (`#`–`######`, `#` then whitespace then text)                           | `{"name": <heading text>, "nodes": [...]}`. Name strips whitespace and optional closing `#`.    |
| Paragraph                                                                           | One leaf `str`: consecutive non-blank lines that are not another block type, joined with `\n`   |
| List item                                                                           | One leaf `str`: text after a marker (`-`, `*`, `+`, or `N.`) on that item, inline markdown kept |
| Any other block (fenced code, table, blockquote, thematic break, setext heading, …) | One opaque leaf `str` (raw block source, trailing newline stripped)                             |

Rules:

- Heading with empty name (`#` or `#   `) → `ParseError`.
- `#foo` (no space after `#`) is not a heading; it is a leaf string.
- A heading at level `L` attaches under the nearest **open** heading with level `< L`. If none, it is a root child. No dummy parents for skipped levels (`h2` then `h4` nests `h4` under `h2`). `## Experience` with no `h1` is a root node.
- Content before the first heading is root children.
- Nested list items do not create heading nodes; each item is a sibling leaf under the current heading (or root).
- Blank lines only separate blocks.

**Outline algorithm:** keep a stack of open headings `(level, name, mutable children)`. On a heading at `L`, close and freeze (`{"name", "nodes": list}`) every stack entry with `level >= L`, appending each onto its parent’s children (or root). Push the new heading. On a leaf, append the string to the current heading’s children, or to root. After the last block, close the stack.

**Paragraph-after-list heuristic (required):** if a **plain paragraph** leaf (not a fenced block, not a leaf whose stripped text is exactly `---`) immediately follows a list item, and the heading stack depth is greater than 1, close the deepest heading first, then attach that paragraph to the parent. This is grammar, not schema. It matches `examples/cv_generator/document/mixed-children.json` (e.g. “Spoken languages…” is a sibling of `Platforms`, not a child). Fence and exact `---` leaves after a list stay nested.

### `Content.from_mapping(raw) -> Content`

Consumes the open dict. Extra keys are ignored (including a `format` or `source_format` key if one appears). Does not parse markdown. Does not construct `Document`. Raises `ValidationError` only. Does not take `source_format`.

`raw` must be a `Mapping`; otherwise `ValidationError`.

**Header (required)** — `name`, `title`, `email`, `phone_number`, `location`:

| Situation         | Error                                        |
| ----------------- | -------------------------------------------- |
| key missing       | `ValidationError` missing field              |
| not a `str`       | `ValidationError` must be a string           |
| empty after strip | `ValidationError` must be a non-empty string |

Store the stripped string. YAML `phone` / `links` are not read here. A leftover `phone` key without `phone_number` is missing `phone_number`.

**`social_profiles`:**

| Input                | Result                                    |
| -------------------- | ----------------------------------------- |
| absent or `None`     | `()`                                      |
| empty sequence       | `()`                                      |
| sequence of mappings | `tuple[SocialProfile, ...]` in list order |
| any other value      | `ValidationError` must be a sequence      |

Each profile: `type` must be `"github"` or `"linkedin"`; `url` must be a `str` (empty URL allowed). Unknown type → `ValidationError`. Extra keys on a profile mapping ignored.

**`nodes`:**

| Input            | Result                    |
| ---------------- | ------------------------- |
| absent or `None` | `()`                      |
| sequence         | `tuple[NodeContent, ...]` |
| any other value  | `ValidationError`         |

Each element: a `str` (leaf, stored as-is) or a mapping → `Node`. On a mapping, `name` must be a non-empty `str` after strip; `nodes` uses the same absent/`None`/sequence rule as the top-level field (missing `nodes` → empty). Extra keys on a node mapping ignored.

Accept lists or tuples; store tuples on `Content`.

## Error handling

`ParseError` and `ValidationError` are siblings: both subclass `Exception`, neither subclasses the other, neither is a `ValueError`.

| Situation                                                                                                         | Exception         |
| ----------------------------------------------------------------------------------------------------------------- | ----------------- |
| `source_format` is not `"markdown"`                                                                               | `ValueError`      |
| Unclosed frontmatter, invalid YAML, frontmatter not a mapping                                                     | `ParseError`      |
| ATX heading with empty name                                                                                       | `ParseError`      |
| `raw` not a mapping                                                                                               | `ValidationError` |
| Missing / non-string / empty (after strip) `name`, `title`, `email`, `phone_number`, `location`                   | `ValidationError` |
| `social_profiles` present but not a sequence; unknown profile type; non-string `url`                              | `ValidationError` |
| `nodes` present but not a sequence; node `name` missing / not a non-empty string; child neither `str` nor mapping | `ValidationError` |

`ParseError` = invalid **source**. `ValidationError` = parsed dict does not satisfy **schema**. `ValueError` = unsupported `source_format` on `Document.parse` (dispatch). A successful `parse` stores that `source_format` on the `Document`.

Empty source `""`: `parse_markdown` succeeds (`{"nodes": []}`). `Document.parse("")` raises `ValidationError` (missing `name` on `Content`). That is stricter than today’s PDF path, which accepts empty markdown; it only matters once `generate_pdf` uses `Document.parse`.

Body without frontmatter: parse succeeds (nodes from the body, no header keys). `Document.parse` raises `ValidationError`.

Unclosed YAML through `Document.parse` remains `ParseError`.

Validation messages use schema field names (`phone_number`, `social_profiles`), not “frontmatter field `phone`/`links`”.

## Testing

- `tests/test_parse_markdown.py` — dict shape, aliases, extra keys **kept**, body grammar, YAML syntax failures. No `Content` / `Document` / `Node` / `SocialProfile` equality. `pytest.raises(ParseError, ...)` only for syntax. Must **not** raise on missing/empty/non-string headers, unknown social types, or `links` as a string. Optional: `json.load` equality with `examples/cv_generator/document/*.json`.
- `tests/test_document.py` — `ParseError` vs `ValidationError` vs `ValueError`; `Document(source_format=..., content=...)` construction; `Content.from_mapping` rules; `Document.parse(text) == Document(source_format="markdown", content=Content.from_mapping(parse_markdown(text)))`; default vs explicit `source_format="markdown"` produce the same `Document` including `.source_format == "markdown"`; unsupported `source_format` → `ValueError`; empty source → `ValidationError`; unclosed YAML through `parse` → `ParseError`. No grammar re-tests.

Move current required-field / empty-string / unknown-link / non-mapping-links tests from `test_parse_markdown.py` to `test_document.py`. Update `match=` strings to schema field names.

No PDF or HTML tests in this work. Do not modify `generate_pdf.py`, `frontmatter.py`, or `tests/test_frontmatter.py`.

## Key decisions

1. **`Content` is the CV body. `Document` is the envelope.** Rename `Data` → `Content`, `data` → `content`. Keep `Document(source_format, content: Content)`. JSON goldens and `from_mapping` input stay a flat mapping of Content fields, not `{source_format, content}` and not `{format, data}`.
2. **No flatten step.** Do not delete the content type, do not move its fields onto `Document`, do not drop stored `source_format`. Do not land an intermediate `parse_markdown -> Document`.
3. **`source_format=` is parse dispatch and a stored field.** It names the format of the parsed source. `Document.parse(..., source_format="markdown")` rejects other values with `ValueError` and stores `"markdown"` on success. A hand-built `Document(source_format="markdown", content=...)` equals one produced by `parse` for the same content. There is no `format` field or `format=` argument.
4. **No `schema=` argument.** Schema is `Content.from_mapping`. `parse` always calls it, then wraps.
5. **Parse and validation are separate.** `parse_markdown` returns an open Content-shaped dict. `Content.from_mapping` validates. `Document.parse` orchestrates.
6. **`parse_markdown` does not import `document.py`.** No cycle; module-level import in `document.py` is fine.
7. **Dict, not an attribute object.** Extra keys survive parse; JSON goldens match; schema ignores extras (including a `format` or `source_format` key if present).
8. **Aliases in the parser, constraints in the schema.** `phone`/`links` rewrite only. Required/non-empty/allowed social types are `ValidationError`.
9. **`ParseError` vs `ValidationError` vs `ValueError`.** Source vs schema vs unsupported `source_format` dispatch.
10. **Headings are nodes; paragraphs and list items are leaves.** Unknown blocks are opaque markdown leaves. Inline markdown is not interpreted.
11. **`frontmatter.py` is not the parse pipeline.** Delete it when `generate_pdf` switches (follow-up).
12. **No new dependencies.**
