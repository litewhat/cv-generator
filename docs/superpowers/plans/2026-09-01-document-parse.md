# Document.parse Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this plan is for **one sequential agent**). Do not use subagent-driven-development: Tasks 1–3 all edit `document.py` / `parse_markdown.py` / the same two test files, so parallel agents will conflict. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split markdown parsing from content-schema validation, and rename the `Document` envelope (`Data` → `Content`, `data` → `content`, `format` → `source_format`).

**Architecture:** `parse_markdown(text)` returns an open Content-shaped dict and raises only `ParseError`. `Content.from_mapping(raw)` is the schema and raises only `ValidationError`. `Document.parse` dispatches on `source_format`, calls those two, and wraps `Document(source_format, content)`. `parse_markdown.py` must not import `document.py`; `document.py` imports the parser at module level and re-exports `ParseError`.

**Tech Stack:** Python >= 3.14, uv, pytest, PyYAML (`yaml.safe_load`). No pydantic, no jsonschema, no new dependencies.

**Spec:** `docs/superpowers/specs/2026-08-31-parse-design.md`

## Global Constraints

- Python `>= 3.14`; run tests with `uv run pytest` (never system Python / pip).
- No new dependencies. No pydantic, no jsonschema.
- Do **not** flatten `Content` into `Document`. Do **not** land `parse_markdown` returning `Document`, `Data`, or `Content`.
- Do **not** modify `src/cv_generator/generate_pdf.py`, `src/cv_generator/frontmatter.py`, `tests/test_frontmatter.py`, templates, or HTML/PDF tests.
- Do **not** export `parse_markdown` from `src/cv_generator/__init__.py`.
- `parse_markdown.py` must not import `document.py`. `document.py` may import `parse_markdown.py` at module level (delete the lazy import inside `Document.parse`).
- `ParseError` is defined in `parse_markdown.py` and re-exported from `document.py` (`from cv_generator.document import ParseError` must work; `ParseError is` the parser class). Spec sentence “Callers should not be able to import ParseError from document” is a contradiction of the re-export — follow the re-export.
- `ValidationError` is defined only in `document.py`. The parser must not import or raise it.
- `ParseError` and `ValidationError` subclass `Exception` only (not each other, not `ValueError`). Unsupported `source_format` is `ValueError`.
- No `schema=` argument, no `Document.from_mapping`. Nested `SocialProfile.from_mapping` / `Node.from_mapping` are allowed.
- Input is source **text**. No file I/O in parse.
- `SocialProfileType` stays `Literal["github", "linkedin"]`. Fields stay public (no underscores).
- Validation messages use schema field names (`phone_number`, `social_profiles`), never “frontmatter field `phone`/`links`”.
- Example JSON under `examples/cv_generator/document/*.json` is Content-shaped. There are **no** paired `.md` files, so do **not** invent markdown goldens. Use the JSON files as `Content.from_mapping` fixtures only.
- Out of scope / follow-up: point `generate_pdf` at `Document.parse`, then delete `frontmatter.py`. Do not break the current PDF command.

---

## File structure

| File | Responsibility after this work |
| --- | --- |
| `src/cv_generator/parse_markdown.py` | `ParseError`; `parse_markdown(text) -> dict[str, object]`; private YAML split, aliases, body walk. **No** import of `document.py`. Lists, not tuples. No `Content`/`Node`/`SocialProfile` instances. |
| `src/cv_generator/document.py` | `ValidationError`; `SocialProfile`, `Node`, `Content`, `Document`; `Content.from_mapping`; `Document.parse`; re-export `ParseError`. Delete `Data` and `validate_document`. |
| `tests/test_parse_markdown.py` | Dict shape, aliases, extra keys **kept**, body grammar, YAML/`ParseError` only. No model equality. |
| `tests/test_document.py` | Envelope construction, `from_mapping` schema, `Document.parse` orchestration, exception taxonomy. No grammar re-tests. |
| `src/cv_generator/__init__.py` | Unchanged (module docstring only). |
| `examples/cv_generator/document/*.json` | Unchanged fixtures for `from_mapping`. |

Do not create new modules.

**Exact public signatures** (locked; later tasks must use these names):

```python
# parse_markdown.py
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

    @classmethod
    def from_mapping(cls, raw: Mapping[str, object]) -> SocialProfile: ...

@dataclass(frozen=True, slots=True)
class Node:
    name: str
    nodes: tuple[NodeContent, ...]

    @classmethod
    def from_mapping(cls, raw: Mapping[str, object]) -> Node: ...

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

`SocialProfile.from_mapping` / `Node.from_mapping` are implementation helpers used by `Content.from_mapping`; tests may call them but are not required to.

**Exact exception messages** (use these strings in tests and implementation):

| Situation | Exception | `match=` / message |
| --- | --- | --- |
| `source_format != "markdown"` | `ValueError` | `Unsupported source_format: ` |
| Unclosed `---` | `ParseError` | `Unclosed YAML frontmatter` |
| `yaml.YAMLError` | `ParseError` | `Invalid YAML frontmatter` |
| Frontmatter loaded value not a mapping | `ParseError` | `Frontmatter must be a mapping` |
| ATX heading with empty name | `ParseError` | `Empty heading name` |
| `from_mapping` argument not a `Mapping` | `ValidationError` | `Expected a mapping` |
| Required header key missing | `ValidationError` | `Missing field '{key}'` |
| Header value not a `str` | `ValidationError` | `Field '{key}' must be a string` |
| Header empty after strip | `ValidationError` | `Field '{key}' must be a non-empty string` |
| `social_profiles` present but not a sequence (reject `str`/`bytes`) | `ValidationError` | `Field 'social_profiles' must be a sequence` |
| Profile element not a mapping | `ValidationError` | `Social profile must be a mapping` |
| Profile `type` not `"github"` or `"linkedin"` | `ValidationError` | `Unsupported social profile type: ` |
| Profile `url` not a `str` | `ValidationError` | `Field 'url' must be a string` |
| `nodes` present but not a sequence (reject `str`/`bytes`) | `ValidationError` | `Field 'nodes' must be a sequence` |
| Node mapping missing `name` | `ValidationError` | `Missing field 'name'` |
| Node `name` not a non-empty `str` after strip | `ValidationError` | `Field 'name' must be a string` or `Field 'name' must be a non-empty string` |
| Node child neither `str` nor mapping | `ValidationError` | `Node child must be a string or mapping` |

Sequence check: `isinstance(value, Sequence) and not isinstance(value, (str, bytes))` (`str` is a `Sequence`).

---

### Task 1: `ValidationError` and `Content.from_mapping`

**Files:**
- Modify: `src/cv_generator/document.py` (add `ValidationError`, `Content`, `from_mapping` helpers; leave `Data`, `Document`, `ParseError`, `validate_document` in place)
- Test: `tests/test_document.py` (add schema tests; do not rewrite envelope tests yet)

**Interfaces:**
- Consumes: existing `SocialProfile`, `Node`, `NodeContent` in `document.py`
- Produces: `ValidationError`; `Content` with the seven fields above; `Content.from_mapping(raw: Mapping[str, object]) -> Content`; `SocialProfile.from_mapping`; `Node.from_mapping`. `Data` still exists until Task 2.

- [ ] **Step 1: Write the failing schema tests**

In `tests/test_document.py`, **replace the existing import section** (do not append a second import block). Keep `parse_markdown` — the existing `Document.parse` tests still use it. Keep every existing `Data` / `Document.parse` test. Then append the helpers and schema tests below.

```python
import json
from pathlib import Path

from cv_generator.document import (
    Content,
    Data,
    Document,
    Node,
    ParseError,
    SocialProfile,
    ValidationError,
)
from cv_generator.parse_markdown import parse_markdown

_EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "cv_generator" / "document"

_VALID_HEADER = {
    "name": "Ada Lovelace",
    "title": "Software Engineer",
    "email": "ada@example.com",
    "phone_number": "+48 111 222 333",
    "location": "Warsaw, Poland",
}


def _header(**overrides: object) -> dict[str, object]:
    raw: dict[str, object] = dict(_VALID_HEADER)
    raw.update(overrides)
    return raw


def test_validation_error_is_a_sibling_of_parse_error():
    assert issubclass(ValidationError, Exception)
    assert not issubclass(ValidationError, ValueError)
    assert not issubclass(ValidationError, ParseError)
    assert not issubclass(ParseError, ValidationError)


def test_from_mapping_reads_required_header_fields():
    content = Content.from_mapping(_VALID_HEADER)
    assert content == Content(
        name="Ada Lovelace",
        title="Software Engineer",
        email="ada@example.com",
        phone_number="+48 111 222 333",
        location="Warsaw, Poland",
        social_profiles=(),
        nodes=(),
    )


def test_from_mapping_strips_header_strings():
    content = Content.from_mapping(
        _header(
            name="  Ada Lovelace  ",
            title="  Software Engineer  ",
            email="  ada@example.com  ",
            phone_number="  +48 111 222 333  ",
            location="  Warsaw, Poland  ",
        )
    )
    assert content.name == "Ada Lovelace"
    assert content.title == "Software Engineer"
    assert content.email == "ada@example.com"
    assert content.phone_number == "+48 111 222 333"
    assert content.location == "Warsaw, Poland"


def test_from_mapping_ignores_extra_keys_including_format():
    content = Content.from_mapping(
        _header(website="https://ada.dev", format="markdown", source_format="html")
    )
    assert content.name == "Ada Lovelace"
    assert not hasattr(content, "website")


def test_from_mapping_does_not_read_phone_or_links_aliases():
    raw = _header()
    del raw["phone_number"]
    raw["phone"] = "+48 111 222 333"
    with pytest.raises(ValidationError, match="Missing field 'phone_number'"):
        Content.from_mapping(raw)


@pytest.mark.parametrize("key", ["name", "title", "email", "phone_number", "location"])
def test_from_mapping_missing_header_field_raises(key: str):
    raw = _header()
    del raw[key]
    with pytest.raises(ValidationError, match=f"Missing field '{key}'"):
        Content.from_mapping(raw)


@pytest.mark.parametrize("key", ["name", "title", "email", "phone_number", "location"])
def test_from_mapping_empty_header_field_raises(key: str):
    with pytest.raises(ValidationError, match=f"Field '{key}' must be a non-empty string"):
        Content.from_mapping(_header(**{key: "   "}))


def test_from_mapping_non_string_title_raises():
    with pytest.raises(ValidationError, match="Field 'title' must be a string"):
        Content.from_mapping(_header(title=1))


def test_from_mapping_rejects_non_mapping():
    with pytest.raises(ValidationError, match="Expected a mapping"):
        Content.from_mapping(["not", "a", "mapping"])  # type: ignore[arg-type]


def test_from_mapping_absent_social_profiles_is_empty():
    assert Content.from_mapping(_VALID_HEADER).social_profiles == ()


def test_from_mapping_none_social_profiles_is_empty():
    assert Content.from_mapping(_header(social_profiles=None)).social_profiles == ()


def test_from_mapping_empty_social_profiles_sequence_is_empty():
    assert Content.from_mapping(_header(social_profiles=[])).social_profiles == ()
    assert Content.from_mapping(_header(social_profiles=())).social_profiles == ()


def test_from_mapping_social_profiles_preserve_list_order():
    content = Content.from_mapping(
        _header(
            social_profiles=[
                {"type": "linkedin", "url": "https://linkedin.com/in/ada"},
                {"type": "github", "url": "https://github.com/ada"},
            ]
        )
    )
    assert content.social_profiles == (
        SocialProfile(type="linkedin", url="https://linkedin.com/in/ada"),
        SocialProfile(type="github", url="https://github.com/ada"),
    )


def test_from_mapping_social_profiles_ignore_extra_keys():
    content = Content.from_mapping(
        _header(
            social_profiles=[
                {"type": "github", "url": "https://github.com/ada", "note": "personal"},
            ]
        )
    )
    assert content.social_profiles == (
        SocialProfile(type="github", url="https://github.com/ada"),
    )


def test_from_mapping_empty_url_is_allowed():
    content = Content.from_mapping(
        _header(social_profiles=[{"type": "github", "url": ""}])
    )
    assert content.social_profiles == (SocialProfile(type="github", url=""),)


def test_from_mapping_unknown_social_type_raises():
    with pytest.raises(ValidationError, match="Unsupported social profile type"):
        Content.from_mapping(
            _header(social_profiles=[{"type": "twitter", "url": "https://twitter.com/ada"}])
        )


def test_from_mapping_social_profiles_string_raises():
    with pytest.raises(ValidationError, match="Field 'social_profiles' must be a sequence"):
        Content.from_mapping(_header(social_profiles="https://github.com/ada"))


def test_from_mapping_nested_profile_url_raises():
    with pytest.raises(ValidationError, match="Field 'url' must be a string"):
        Content.from_mapping(
            _header(social_profiles=[{"type": "github", "url": {"href": "https://github.com/ada"}}])
        )


def test_from_mapping_profile_not_a_mapping_raises():
    with pytest.raises(ValidationError, match="Social profile must be a mapping"):
        Content.from_mapping(_header(social_profiles=["github"]))


def test_from_mapping_absent_nodes_is_empty():
    assert Content.from_mapping(_VALID_HEADER).nodes == ()


def test_from_mapping_none_nodes_is_empty():
    assert Content.from_mapping(_header(nodes=None)).nodes == ()


def test_from_mapping_nodes_accepts_tuple():
    content = Content.from_mapping(_header(nodes=("Intro",)))
    assert content.nodes == ("Intro",)


def test_from_mapping_nodes_mixed_children():
    content = Content.from_mapping(
        _header(
            nodes=[
                "Intro",
                {"name": "Experience", "nodes": ["Did a thing"]},
            ]
        )
    )
    assert content.nodes == (
        "Intro",
        Node(name="Experience", nodes=("Did a thing",)),
    )


def test_from_mapping_node_strips_name_and_defaults_missing_nodes():
    content = Content.from_mapping(
        _header(nodes=[{"name": "  Experience  ", "extra": True}])
    )
    assert content.nodes == (Node(name="Experience", nodes=()),)


def test_from_mapping_nodes_string_raises():
    with pytest.raises(ValidationError, match="Field 'nodes' must be a sequence"):
        Content.from_mapping(_header(nodes="Intro"))


def test_from_mapping_missing_node_name_raises():
    with pytest.raises(ValidationError, match="Missing field 'name'"):
        Content.from_mapping(_header(nodes=[{"nodes": ["Did a thing"]}]))


def test_from_mapping_empty_node_name_raises():
    with pytest.raises(ValidationError, match="Field 'name' must be a non-empty string"):
        Content.from_mapping(_header(nodes=[{"name": "   ", "nodes": []}]))


def test_from_mapping_non_string_node_name_raises():
    with pytest.raises(ValidationError, match="Field 'name' must be a string"):
        Content.from_mapping(_header(nodes=[{"name": 1, "nodes": []}]))


def test_from_mapping_node_child_neither_str_nor_mapping_raises():
    with pytest.raises(ValidationError, match="Node child must be a string or mapping"):
        Content.from_mapping(_header(nodes=[{"name": "Experience", "nodes": [1]}]))


def _node_to_json(node: Node | str) -> object:
    if isinstance(node, str):
        return node
    return {"name": node.name, "nodes": [_node_to_json(child) for child in node.nodes]}


def _content_to_json(content: Content) -> dict[str, object]:
    return {
        "name": content.name,
        "title": content.title,
        "email": content.email,
        "phone_number": content.phone_number,
        "location": content.location,
        "social_profiles": [
            {"type": profile.type, "url": profile.url} for profile in content.social_profiles
        ],
        "nodes": [_node_to_json(node) for node in content.nodes],
    }


@pytest.mark.parametrize(
    "filename",
    [
        "empty-social-profiles.json",
        "github-only.json",
        "linkedin-only.json",
        "mixed-children.json",
        "mixed-root.json",
        "nested-experience.json",
        "production-like.json",
        "root-strings.json",
    ],
)
def test_from_mapping_accepts_example_goldens(filename: str):
    raw = json.loads((_EXAMPLES / filename).read_text(encoding="utf-8"))
    assert _content_to_json(Content.from_mapping(raw)) == raw
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_document.py::test_from_mapping_reads_required_header_fields tests/test_document.py::test_validation_error_is_a_sibling_of_parse_error -v`

Expected: FAIL with `ImportError` / `cannot import name 'Content'` / `cannot import name 'ValidationError'`.

- [ ] **Step 3: Implement `ValidationError` and `from_mapping`**

Overwrite `src/cv_generator/document.py` with the file below. Do **not** import `parse_markdown` at module level in this task (`parse_markdown.py` still imports `ParseError` from `document.py`; a module-level reverse import would cycle). Keep `ParseError` defined here until Task 2 moves it. Keep `Data`, `Document.parse` (lazy import), and `validate_document` unchanged in behavior.

```python
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

type SocialProfileType = Literal["github", "linkedin"]
type NodeContent = Node | str

_SOCIAL_TYPES = frozenset({"github", "linkedin"})
_HEADER_FIELDS = ("name", "title", "email", "phone_number", "location")


class ParseError(Exception):
    """Invalid CV source text."""


class ValidationError(Exception):
    """Parsed mapping does not match the content schema."""


def _is_sequence(value: object) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes))


def _require_non_empty_str(raw: Mapping[object, object], key: str) -> str:
    if key not in raw:
        raise ValidationError(f"Missing field '{key}'")
    value = raw[key]
    if not isinstance(value, str):
        raise ValidationError(f"Field '{key}' must be a string")
    stripped = value.strip()
    if not stripped:
        raise ValidationError(f"Field '{key}' must be a non-empty string")
    return stripped


@dataclass(frozen=True, slots=True)
class SocialProfile:
    type: SocialProfileType
    url: str

    @classmethod
    def from_mapping(cls, raw: object) -> SocialProfile:
        if not isinstance(raw, Mapping):
            raise ValidationError("Social profile must be a mapping")
        profile_type = raw.get("type")
        if profile_type not in _SOCIAL_TYPES:
            raise ValidationError(f"Unsupported social profile type: {profile_type!r}")
        url = raw.get("url")
        if not isinstance(url, str):
            raise ValidationError("Field 'url' must be a string")
        return cls(type=profile_type, url=url)


@dataclass(frozen=True, slots=True)
class Node:
    name: str
    nodes: tuple[NodeContent, ...]

    @classmethod
    def from_mapping(cls, raw: Mapping[str, object]) -> Node:
        name = _require_non_empty_str(raw, "name")
        return cls(name=name, nodes=_parse_nodes(raw.get("nodes")))


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
    def from_mapping(cls, raw: Mapping[str, object]) -> Content:
        if not isinstance(raw, Mapping):
            raise ValidationError("Expected a mapping")
        header = {key: _require_non_empty_str(raw, key) for key in _HEADER_FIELDS}
        return cls(
            name=header["name"],
            title=header["title"],
            email=header["email"],
            phone_number=header["phone_number"],
            location=header["location"],
            social_profiles=_parse_social_profiles(raw.get("social_profiles")),
            nodes=_parse_nodes(raw.get("nodes")),
        )


@dataclass(frozen=True, slots=True)
class Data:
    name: str
    title: str
    email: str
    phone_number: str
    location: str
    social_profiles: tuple[SocialProfile, ...]
    nodes: tuple[NodeContent, ...]


@dataclass(frozen=True, slots=True)
class Document:
    format: Literal["markdown"]
    data: Data

    @staticmethod
    def parse(text: str, *, format: Literal["markdown"] = "markdown") -> Document:
        if format != "markdown":
            raise ValueError(f"Unsupported format: {format!r}")
        from cv_generator.parse_markdown import parse_markdown

        return Document(format=format, data=parse_markdown(text))


def validate_document(data: dict) -> Document:
    pass


def _parse_social_profiles(value: object) -> tuple[SocialProfile, ...]:
    if value is None:
        return ()
    if not _is_sequence(value):
        raise ValidationError("Field 'social_profiles' must be a sequence")
    return tuple(SocialProfile.from_mapping(item) for item in value)


def _parse_nodes(value: object) -> tuple[NodeContent, ...]:
    if value is None:
        return ()
    if not _is_sequence(value):
        raise ValidationError("Field 'nodes' must be a sequence")
    return tuple(_parse_node_content(item) for item in value)


def _parse_node_content(value: object) -> NodeContent:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        return Node.from_mapping(value)
    raise ValidationError("Node child must be a string or mapping")
```

`SocialProfile.from_mapping` uses `profile_type not in _SOCIAL_TYPES`, so a missing `type` key is `Unsupported social profile type: None`.

- [ ] **Step 4: Run schema tests to verify they pass**

Run: `uv run pytest tests/test_document.py tests/test_parse_markdown.py -v`

Expected: PASS (existing `Data`/`Document.parse` tests still pass; new `from_mapping` tests pass).

- [ ] **Step 5: Commit**

```bash
git add src/cv_generator/document.py tests/test_document.py
git commit -m "feat: add Content.from_mapping schema validation"
```

---

### Task 2: `parse_markdown` returns an open dict

**Files:**
- Modify: `src/cv_generator/parse_markdown.py` (move `ParseError` here; return `dict`; aliases; lists; no `document.py` import)
- Modify: `src/cv_generator/document.py` (re-export `ParseError`; `Document.parse` calls `Content.from_mapping`; `Document.data: Content`; delete `Data`)
- Test: `tests/test_parse_markdown.py` (replace file)
- Test: `tests/test_document.py` (replace `Data` with `Content` in construction tests; parse wrap uses `from_mapping`)

**Interfaces:**
- Consumes: `Content.from_mapping` from Task 1; `_split_frontmatter` delimiter rules already in `parse_markdown.py` (same as `parse_frontmatter`: opener is a line whose `strip()` is exactly `---`, not `----`)
- Produces: `parse_markdown(text: str) -> dict[str, object]`; `ParseError` in `parse_markdown.py`; `from cv_generator.document import ParseError` is the same class. Dict keys: YAML keys after aliases, plus always `nodes` (list). No model instances.

This task still uses `Document.format` / `Document.data` / `parse(..., format=)`. Task 3 renames those.

- [ ] **Step 1: Replace `tests/test_parse_markdown.py` with dict tests**

Overwrite `tests/test_parse_markdown.py` with:

```python
from pathlib import Path

import pytest

from cv_generator.parse_markdown import ParseError, parse_markdown

_HEADER = """---
name: Ada Lovelace
title: Software Engineer
email: ada@example.com
phone: "+48 111 222 333"
location: Warsaw, Poland
---
"""

_HEADER_DICT = {
    "name": "Ada Lovelace",
    "title": "Software Engineer",
    "email": "ada@example.com",
    "phone_number": "+48 111 222 333",
    "location": "Warsaw, Poland",
}


def _cv(body: str) -> str:
    return _HEADER + body


def test_parse_markdown_does_not_import_document():
    source = Path(__file__).resolve().parents[1] / "src" / "cv_generator" / "parse_markdown.py"
    text = source.read_text(encoding="utf-8")
    assert "cv_generator.document" not in text
    assert "from cv_generator import document" not in text


def test_header_only_maps_into_dict():
    assert parse_markdown(_HEADER) == {**_HEADER_DICT, "nodes": []}


def test_github_and_linkedin_preserve_yaml_order():
    md = """---
name: Ada Lovelace
title: Software Engineer
email: ada@example.com
phone: "+48 111 222 333"
location: Warsaw, Poland
links:
  linkedin: https://linkedin.com/in/ada
  github: https://github.com/ada
---
"""
    assert parse_markdown(md)["social_profiles"] == [
        {"type": "linkedin", "url": "https://linkedin.com/in/ada"},
        {"type": "github", "url": "https://github.com/ada"},
    ]


def test_missing_links_omits_social_profiles_key():
    raw = parse_markdown(_HEADER)
    assert "social_profiles" not in raw
    assert "links" not in raw


def test_null_links_yields_empty_social_profiles_list():
    md = """---
name: Ada Lovelace
title: Software Engineer
email: ada@example.com
phone: "+48 111 222 333"
location: Warsaw, Poland
links: null
---
"""
    assert parse_markdown(md)["social_profiles"] == []


def test_empty_links_mapping_yields_empty_social_profiles_list():
    md = """---
name: Ada Lovelace
title: Software Engineer
email: ada@example.com
phone: "+48 111 222 333"
location: Warsaw, Poland
links: {}
---
"""
    assert parse_markdown(md)["social_profiles"] == []


def test_links_as_string_is_copied_to_social_profiles():
    md = """---
name: Ada Lovelace
title: Software Engineer
email: ada@example.com
phone: "+48 111 222 333"
location: Warsaw, Poland
links: https://github.com/ada
---
"""
    assert parse_markdown(md)["social_profiles"] == "https://github.com/ada"


def test_unknown_link_type_is_kept():
    md = """---
name: Ada Lovelace
title: Software Engineer
email: ada@example.com
phone: "+48 111 222 333"
location: Warsaw, Poland
links:
  twitter: https://twitter.com/ada
---
"""
    assert parse_markdown(md)["social_profiles"] == [
        {"type": "twitter", "url": "https://twitter.com/ada"},
    ]


def test_nested_link_value_is_copied_as_is():
    md = """---
name: Ada Lovelace
title: Software Engineer
email: ada@example.com
phone: "+48 111 222 333"
location: Warsaw, Poland
links:
  github:
    url: https://github.com/ada
---
"""
    assert parse_markdown(md)["social_profiles"] == [
        {"type": "github", "url": {"url": "https://github.com/ada"}},
    ]


def test_phone_alias_wins_over_phone_number():
    md = """---
name: Ada Lovelace
title: Software Engineer
email: ada@example.com
phone: "+48 000 000 000"
phone_number: "+48 111 222 333"
location: Warsaw, Poland
---
"""
    raw = parse_markdown(md)
    assert raw["phone_number"] == "+48 000 000 000"
    assert "phone" not in raw


def test_phone_number_without_phone_is_kept():
    md = """---
name: Ada Lovelace
title: Software Engineer
email: ada@example.com
phone_number: "+48 111 222 333"
location: Warsaw, Poland
---
"""
    raw = parse_markdown(md)
    assert raw["phone_number"] == "+48 111 222 333"
    assert "phone" not in raw


def test_links_alias_wins_over_social_profiles():
    md = """---
name: Ada Lovelace
title: Software Engineer
email: ada@example.com
phone: "+48 111 222 333"
location: Warsaw, Poland
social_profiles:
  - type: github
    url: https://github.com/other
links:
  github: https://github.com/ada
---
"""
    raw = parse_markdown(md)
    assert raw["social_profiles"] == [
        {"type": "github", "url": "https://github.com/ada"},
    ]
    assert "links" not in raw


def test_extra_yaml_keys_are_kept():
    md = """---
name: Ada Lovelace
title: Software Engineer
email: ada@example.com
phone: "+48 111 222 333"
location: Warsaw, Poland
website: https://ada.dev
---
"""
    raw = parse_markdown(md)
    assert raw["website"] == "https://ada.dev"


def test_header_values_are_not_stripped_or_type_checked():
    md = """---
name: "  Ada Lovelace  "
title: 1
email: ada@example.com
phone: "  +48 111 222 333  "
location: Warsaw, Poland
---
"""
    raw = parse_markdown(md)
    assert raw["name"] == "  Ada Lovelace  "
    assert raw["title"] == 1
    assert raw["phone_number"] == "  +48 111 222 333  "


def test_missing_required_yaml_keys_are_absent():
    raw = parse_markdown("---\n---\n")
    assert raw == {"nodes": []}


def test_partial_header_does_not_raise():
    md = """---
title: Software Engineer
---
"""
    raw = parse_markdown(md)
    assert "name" not in raw
    assert raw["title"] == "Software Engineer"
    assert raw["nodes"] == []


def test_yaml_nodes_key_is_overwritten_by_body():
    md = """---
name: Ada Lovelace
title: Software Engineer
email: ada@example.com
phone: "+48 111 222 333"
location: Warsaw, Poland
nodes:
  - from yaml
---
Hello
"""
    raw = parse_markdown(md)
    assert raw["nodes"] == ["Hello"]


def test_unclosed_frontmatter_raises():
    md = """---
name: Ada Lovelace
title: Software Engineer
"""
    with pytest.raises(ParseError, match="Unclosed YAML frontmatter"):
        parse_markdown(md)


def test_invalid_yaml_raises():
    md = """---
name: [unclosed
---
"""
    with pytest.raises(ParseError, match="Invalid YAML frontmatter"):
        parse_markdown(md)


def test_non_mapping_frontmatter_raises():
    md = """---
- just a list
---
"""
    with pytest.raises(ParseError, match="Frontmatter must be a mapping"):
        parse_markdown(md)


def test_empty_source_returns_nodes_only():
    assert parse_markdown("") == {"nodes": []}


def test_body_without_frontmatter_keeps_nodes():
    assert parse_markdown("# Hello\n") == {
        "nodes": [{"name": "Hello", "nodes": []}],
    }


def test_bom_with_valid_frontmatter():
    assert parse_markdown("\ufeff" + _HEADER)["name"] == "Ada Lovelace"


def test_four_dashes_is_not_frontmatter():
    md = "----\nname: Ada Lovelace\n---\n"
    raw = parse_markdown(md)
    assert "name" not in raw
    assert raw["nodes"] == ["----\nname: Ada Lovelace\n---"]


def test_empty_body_has_no_nodes():
    assert parse_markdown(_HEADER)["nodes"] == []
    assert parse_markdown(_cv("\n\n"))["nodes"] == []


def test_root_paragraphs():
    assert parse_markdown(_cv("Python and Go.\n\nComfortable owning services.\n"))["nodes"] == [
        "Python and Go.",
        "Comfortable owning services.",
    ]


def test_multiline_paragraph_joins_with_newline():
    assert parse_markdown(_cv("Line one\nLine two\n"))["nodes"] == ["Line one\nLine two"]


def test_h2_without_h1_is_a_root_node():
    assert parse_markdown(_cv("## Experience\n\nDid a thing.\n"))["nodes"] == [
        {"name": "Experience", "nodes": ["Did a thing."]},
    ]


def test_nested_headings_follow_level():
    assert parse_markdown(
        _cv("## Experience\n\n### Northwind\n\n- Led checkout\n- Cut latency\n")
    )["nodes"] == [
        {
            "name": "Experience",
            "nodes": [
                {"name": "Northwind", "nodes": ["Led checkout", "Cut latency"]},
            ],
        },
    ]


def test_skipped_heading_level_nests_under_nearest_shallower():
    assert parse_markdown(_cv("## Experience\n\n#### Team\n\nHired people.\n"))["nodes"] == [
        {
            "name": "Experience",
            "nodes": [{"name": "Team", "nodes": ["Hired people."]}],
        },
    ]


def test_sibling_h2_closes_previous_branch():
    assert parse_markdown(_cv("## Experience\n\nAt Acme.\n\n## Education\n\nBSc CS.\n"))["nodes"] == [
        {"name": "Experience", "nodes": ["At Acme."]},
        {"name": "Education", "nodes": ["BSc CS."]},
    ]


def test_mixed_root_strings_and_sections():
    assert parse_markdown(
        _cv(
            "Builds payment systems.\n\n"
            "## Experience\n\n"
            "### Northwind\n\n"
            "- Led the checkout rewrite\n\n"
            "## Education\n\n"
            "BSc Computer Science, 2016\n"
        )
    )["nodes"] == [
        "Builds payment systems.",
        {
            "name": "Experience",
            "nodes": [
                {"name": "Northwind", "nodes": ["Led the checkout rewrite"]},
            ],
        },
        {"name": "Education", "nodes": ["BSc Computer Science, 2016"]},
    ]


def test_mixed_children_under_a_heading():
    assert parse_markdown(
        _cv(
            "## Skills\n\n"
            "TypeScript, Python, SQL\n\n"
            "### Platforms\n\n"
            "- AWS\n"
            "- GCP\n\n"
            "Spoken languages: English, Polish\n"
        )
    )["nodes"] == [
        {
            "name": "Skills",
            "nodes": [
                "TypeScript, Python, SQL",
                {"name": "Platforms", "nodes": ["AWS", "GCP"]},
                "Spoken languages: English, Polish",
            ],
        },
    ]


def test_nested_list_items_are_sibling_leaves():
    assert parse_markdown(_cv("- parent\n  - child\n"))["nodes"] == ["parent", "child"]


def test_inline_markdown_is_preserved():
    assert parse_markdown(_cv("A **bold** and `code` line.\n"))["nodes"] == [
        "A **bold** and `code` line.",
    ]


def test_hash_without_space_is_not_a_heading():
    assert parse_markdown(_cv("#not-a-heading\n"))["nodes"] == ["#not-a-heading"]


def test_empty_heading_name_raises():
    with pytest.raises(ParseError, match="Empty heading name"):
        parse_markdown(_cv("#\n"))
    with pytest.raises(ParseError, match="Empty heading name"):
        parse_markdown(_cv("#   \n"))


def test_closing_atx_hashes_are_stripped_from_name():
    assert parse_markdown(_cv("## Experience ##\n\nHello\n"))["nodes"] == [
        {"name": "Experience", "nodes": ["Hello"]},
    ]


def test_fenced_code_is_an_opaque_leaf():
    assert parse_markdown(_cv("## Notes\n\n```python\nx = 1\n```\n"))["nodes"] == [
        {"name": "Notes", "nodes": ["```python\nx = 1\n```"]},
    ]


def test_thematic_break_is_an_opaque_leaf():
    assert parse_markdown(_cv("## Notes\n\n---\n"))["nodes"] == [
        {"name": "Notes", "nodes": ["---"]},
    ]


def test_fence_after_list_stays_nested():
    assert parse_markdown(_cv("## Skills\n\n### Platforms\n\n- AWS\n\n```\ncode\n```\n"))["nodes"] == [
        {
            "name": "Skills",
            "nodes": [
                {
                    "name": "Platforms",
                    "nodes": ["AWS", "```\ncode\n```"],
                },
            ],
        },
    ]


def test_thematic_break_after_list_stays_nested():
    assert parse_markdown(_cv("## Skills\n\n### Platforms\n\n- AWS\n\n---\n"))["nodes"] == [
        {
            "name": "Skills",
            "nodes": [
                {"name": "Platforms", "nodes": ["AWS", "---"]},
            ],
        },
    ]
```

- [ ] **Step 2: Run parser tests to verify they fail**

Run: `uv run pytest tests/test_parse_markdown.py::test_header_only_maps_into_dict tests/test_parse_markdown.py::test_empty_source_returns_nodes_only tests/test_parse_markdown.py::test_parse_markdown_does_not_import_document -v`

Expected: FAIL (`Data` has no dict equality / `ParseError` missing `name` on empty source / import of `cv_generator.document` still present).

- [ ] **Step 3: Implement dict `parse_markdown`**

Overwrite `src/cv_generator/parse_markdown.py` with:

```python
import re

import yaml

class ParseError(Exception):
    """Invalid CV source text."""


def parse_markdown(text: str) -> dict[str, object]:
    working = text[1:] if text.startswith("\ufeff") else text
    meta, body = _split_frontmatter(working)
    result = _apply_aliases(meta)
    result["nodes"] = _parse_body(body)
    return result


def _split_frontmatter(text: str) -> tuple[dict[str, object], str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break
    if end_idx is None:
        raise ParseError("Unclosed YAML frontmatter")
    yaml_block = "\n".join(lines[1:end_idx])
    body = "\n".join(lines[end_idx + 1 :])
    if not yaml_block.strip():
        return {}, body
    try:
        loaded = yaml.safe_load(yaml_block)
    except yaml.YAMLError as exc:
        raise ParseError(f"Invalid YAML frontmatter: {exc}") from exc
    if loaded is None:
        return {}, body
    if not isinstance(loaded, dict):
        raise ParseError("Frontmatter must be a mapping")
    return loaded, body


def _apply_aliases(meta: dict[str, object]) -> dict[str, object]:
    result = dict(meta)
    if "phone" in result:
        result["phone_number"] = result.pop("phone")
    if "links" in result:
        result["social_profiles"] = _normalize_links(result.pop("links"))
    return result


def _normalize_links(links: object) -> object:
    if links is None or links == {}:
        return []
    if isinstance(links, dict):
        return [{"type": key, "url": value} for key, value in links.items()]
    return links


_ATX_START = re.compile(r"^(#{1,6})(?:\s|$)")
_ATX_LINE = re.compile(r"^(#{1,6})(?:[ \t]+(.*))?$")
_CLOSING_HASHES = re.compile(r"[ \t]+#+$")
_LIST_ITEM = re.compile(r"^[ \t]*(?:[-*+]|\d+\.)[ \t]+(.*)$")
_FENCE = re.compile(r"^([ \t]*)(```+|~~~+)")


def _parse_body(body: str) -> list[object]:
    root: list[object] = []
    stack: list[tuple[int, str, list[object]]] = []

    def close_until(level: int) -> None:
        while stack and stack[-1][0] >= level:
            _level, name, children = stack.pop()
            node = {"name": name, "nodes": children}
            if stack:
                stack[-1][2].append(node)
            else:
                root.append(node)

    def _is_fence_leaf(text: str) -> bool:
        stripped = text.lstrip()
        return stripped.startswith("```") or stripped.startswith("~~~")

    def _is_thematic_leaf(text: str) -> bool:
        return text.strip() == "---"

    prev_kind: str | None = None
    for kind, payload in _iter_blocks(body.splitlines()):
        if kind == "heading":
            level, name = payload
            if name == "":
                raise ParseError("Empty heading name")
            close_until(level)
            stack.append((level, name, []))
            prev_kind = "heading"
        elif kind == "list":
            if stack:
                stack[-1][2].append(payload)
            else:
                root.append(payload)
            prev_kind = "list"
        else:
            leaf = payload
            is_paragraph = not _is_fence_leaf(leaf) and not _is_thematic_leaf(leaf)
            if is_paragraph and prev_kind == "list" and len(stack) > 1:
                _level, name, children = stack.pop()
                node = {"name": name, "nodes": children}
                if stack:
                    stack[-1][2].append(node)
                else:
                    root.append(node)
            if stack:
                stack[-1][2].append(leaf)
            else:
                root.append(leaf)
            prev_kind = "leaf"
    close_until(0)
    return root


def _heading_name(line: str) -> tuple[int, str] | None:
    if not _ATX_START.match(line):
        return None
    match = _ATX_LINE.match(line)
    if match is None:
        return None
    level = len(match.group(1))
    rest = match.group(2) or ""
    name = _CLOSING_HASHES.sub("", rest).strip()
    return level, name


def _iter_blocks(lines: list[str]):
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        if not line.strip():
            i += 1
            continue

        fence = _FENCE.match(line)
        if fence is not None:
            marker_char = fence.group(2)[0]
            marker_len = len(fence.group(2))
            chunk = [line]
            i += 1
            while i < n:
                chunk.append(lines[i])
                closer = _FENCE.match(lines[i])
                if (
                    closer is not None
                    and closer.group(2)[0] == marker_char
                    and len(closer.group(2)) >= marker_len
                ):
                    i += 1
                    break
                i += 1
            yield "leaf", "\n".join(chunk)
            continue

        heading = _heading_name(line)
        if heading is not None:
            yield "heading", heading
            i += 1
            continue

        list_item = _LIST_ITEM.match(line)
        if list_item is not None:
            yield "list", list_item.group(1)
            i += 1
            continue

        chunk = [line]
        i += 1
        while i < n and lines[i].strip():
            if (
                _FENCE.match(lines[i]) is not None
                or _heading_name(lines[i]) is not None
                or _LIST_ITEM.match(lines[i]) is not None
            ):
                break
            chunk.append(lines[i])
            i += 1
        yield "leaf", "\n".join(chunk)
```

- [ ] **Step 4: Run parser tests**

Run: `uv run pytest tests/test_parse_markdown.py -v`

Expected: PASS.

- [ ] **Step 5: Point `Document.parse` at `Content.from_mapping` and delete `Data`**

`parse_markdown` now returns a dict, so `Document.parse` and any `Data(...)` tests will fail until this step.

Apply all five edits to `src/cv_generator/document.py` in the **same save**. After deleting `Data`, `Document.data` must already be typed `Content` or the module will not import.

1. Remove the `ParseError` class.
2. Add module-level: `from cv_generator.parse_markdown import ParseError, parse_markdown`.
3. Delete class `Data`.
4. Change `Document.data` type from `Data` to `Content`.
5. Replace `Document.parse` with:

```python
    @staticmethod
    def parse(text: str, *, format: Literal["markdown"] = "markdown") -> Document:
        if format != "markdown":
            raise ValueError(f"Unsupported format: {format!r}")
        return Document(format=format, data=Content.from_mapping(parse_markdown(text)))
```

No try/except around `parse_markdown` or `from_mapping`. No lazy import.

In `tests/test_document.py`, replace every `Data` with `Content`:

- Import: drop `Data`; keep `Content` (already added in Task 1).
- `_sample_data` → `_sample_content` returning `Content(...)`.
- `test_data_holds_all_header_fields_and_nodes` → `test_content_holds_all_header_fields_and_nodes` using `_sample_content`.
- `Document(format="markdown", data=data)` stays (rename is Task 3) but `data` is a `Content`.
- Replace `test_parse_wraps_parse_markdown_data` with:

```python
def test_parse_wraps_parse_markdown_via_from_mapping():
    document = Document.parse(_MD)
    assert document.format == "markdown"
    assert document.data == Content.from_mapping(parse_markdown(_MD))
    assert document.data.nodes[0].name == "Experience"
```

- `test_parse_explicit_markdown_format`: `assert document.data == Content.from_mapping(parse_markdown(_MD))`
- Replace `test_parse_does_not_turn_source_errors_into_value_error` so empty source is no longer a parse error:

```python
def test_parse_does_not_turn_source_errors_into_value_error():
    with pytest.raises(ParseError, match="Unclosed YAML frontmatter"):
        Document.parse("---\nname: Ada\n")
```

- [ ] **Step 6: Run document + parser tests**

Run: `uv run pytest tests/test_document.py tests/test_parse_markdown.py -v`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/cv_generator/parse_markdown.py src/cv_generator/document.py tests/test_parse_markdown.py tests/test_document.py
git commit -m "feat: parse markdown to an open dict and validate in Content.from_mapping"
```

---

### Task 3: Envelope rename and `Document.parse` dispatch

**Files:**
- Modify: `src/cv_generator/document.py` (`format`/`data` → `source_format`/`content`; `parse(..., source_format=)`; delete `validate_document`)
- Test: `tests/test_document.py` (construction, dispatch, exception taxonomy, empty source)

**Interfaces:**
- Consumes: `parse_markdown` and `Content.from_mapping` from Tasks 1–2
- Produces: `Document(source_format: Literal["markdown"], content: Content)`; `Document.parse(text, *, source_format="markdown") -> Document`. No `Data`, no `format` field, no `format=` argument, no `validate_document`.

- [ ] **Step 1: Write the failing envelope tests**

In `tests/test_document.py`, replace the remaining `format`/`data` tests with:

```python
def test_document_exposes_public_source_format_and_content():
    content = _sample_content()
    document = Document(source_format="markdown", content=content)
    assert document.source_format == "markdown"
    assert document.content is content


def test_parse_equals_from_mapping_of_parse_markdown():
    document = Document.parse(_MD)
    assert document == Document(
        source_format="markdown",
        content=Content.from_mapping(parse_markdown(_MD)),
    )
    assert document.source_format == "markdown"
    assert document.content.nodes[0].name == "Experience"


def test_parse_default_source_format_is_markdown():
    assert Document.parse(_MD).source_format == "markdown"


def test_parse_explicit_markdown_source_format_matches_default():
    default = Document.parse(_MD)
    explicit = Document.parse(_MD, source_format="markdown")
    assert default == explicit
    assert explicit.source_format == "markdown"


def test_parse_unsupported_source_format_raises_value_error():
    with pytest.raises(ValueError, match="Unsupported source_format"):
        Document.parse(_MD, source_format="html")  # type: ignore[arg-type]


def test_parse_value_error_is_not_parse_or_validation_error():
    with pytest.raises(ValueError) as excinfo:
        Document.parse(_MD, source_format="html")  # type: ignore[arg-type]
    assert not isinstance(excinfo.value, ParseError)
    assert not isinstance(excinfo.value, ValidationError)


def test_parse_empty_source_raises_validation_error():
    with pytest.raises(ValidationError, match="Missing field 'name'"):
        Document.parse("")


def test_parse_body_without_frontmatter_raises_validation_error():
    with pytest.raises(ValidationError, match="Missing field 'name'"):
        Document.parse("# Hello\n")


def test_parse_unclosed_yaml_raises_parse_error():
    with pytest.raises(ParseError, match="Unclosed YAML frontmatter"):
        Document.parse("---\nname: Ada\n")


def test_parse_does_not_convert_parse_error_into_validation_error():
    with pytest.raises(ParseError):
        Document.parse("---\nname: Ada\n")


def test_parse_error_is_reexported_from_document():
    from cv_generator.parse_markdown import ParseError as ParserParseError

    assert ParseError is ParserParseError


def test_validate_document_is_gone():
    import cv_generator.document as document_module

    assert not hasattr(document_module, "validate_document")
    assert not hasattr(document_module, "Data")
```

Delete the old tests they replace (`test_document_exposes_public_format_and_data`, `test_parse_wraps_parse_markdown_via_from_mapping`, `test_parse_default_format_is_markdown`, `test_parse_explicit_markdown_format`, `test_parse_unsupported_format_raises_value_error`, `test_parse_does_not_turn_source_errors_into_value_error`).

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_document.py::test_document_exposes_public_source_format_and_content tests/test_document.py::test_parse_empty_source_raises_validation_error tests/test_document.py::test_validate_document_is_gone -v`

Expected: FAIL (`Document.__init__() got an unexpected keyword argument 'source_format'` / `validate_document` still present).

- [ ] **Step 3: Rename the envelope and delete the stub**

In `src/cv_generator/document.py`, replace `Document` and delete `validate_document`:

```python
@dataclass(frozen=True, slots=True)
class Document:
    source_format: Literal["markdown"]
    content: Content

    @staticmethod
    def parse(
        text: str,
        *,
        source_format: Literal["markdown"] = "markdown",
    ) -> Document:
        if source_format != "markdown":
            raise ValueError(f"Unsupported source_format: {source_format!r}")
        return Document(
            source_format=source_format,
            content=Content.from_mapping(parse_markdown(text)),
        )
```

In `src/cv_generator/document.py` and `tests/test_document.py`, confirm there is no `class Data`, `Data(`, `validate_document`, `document.format`, `document.data`, or `parse(..., format=)`.

These hits are expected and must stay: `source_format`; `test_from_mapping_ignores_extra_keys_including_format` (it passes a mapping key `format="markdown"`, not the envelope field).

- [ ] **Step 4: Run the parse/document tests**

Run: `uv run pytest tests/test_document.py tests/test_parse_markdown.py -v`

Expected: PASS.

- [ ] **Step 5: Full suite (PDF path must still pass unchanged)**

Run: `uv run pytest -v`

Expected: PASS, including `tests/test_frontmatter.py`, `tests/test_generate_pdf.py`, `tests/test_cli.py`. If those fail, you modified something out of scope — revert that, do not “fix” PDF code in this work.

Also confirm:

```bash
rg "from cv_generator.document import|from cv_generator.parse_markdown import" src tests
rg "parse_markdown" src/cv_generator/__init__.py
```

Expected: no `Data`; no `parse_markdown` export in `__init__.py`; `generate_pdf.py` still imports `parse_frontmatter` only.

- [ ] **Step 6: Commit**

```bash
git add src/cv_generator/document.py tests/test_document.py
git commit -m "feat: rename Document envelope to source_format and content"
```

---

## Self-review (author)

**Spec coverage**

| Spec requirement | Task |
| --- | --- |
| Rename `Data` → `Content`, `data` → `content`, `format` → `source_format` | 1 (Content type), 3 (envelope fields) |
| `parse_markdown` returns open dict, no `document.py` import | 2 |
| Aliases `phone`/`links`; extra keys kept; values unstripped; missing keys absent | 2 |
| `links` null/`{}` → `[]`; mapping → list of `{type,url}`; other values copied | 2 |
| `nodes` always from body, never YAML | 2 |
| Body grammar, outline stack, paragraph-after-list heuristic, opaque leaves | 2 (existing tests rewritten to dicts) + fence/`---` after list stay nested |
| Empty source `{"nodes": []}`; `Document.parse("")` → `ValidationError` | 2 + 3 |
| `Content.from_mapping` header/social/nodes rules, extra keys ignored | 1 |
| `Document.parse` dispatch → parse → from_mapping → wrap; no catch | 2 (wired) + 3 (final names) |
| `ParseError` vs `ValidationError` vs `ValueError` | 1 + 3 |
| Re-export `ParseError`; do not export `parse_markdown` from `__init__.py` | 2 + 3 |
| Remove `validate_document`; no `Data` | 3 |
| Do not touch `generate_pdf` / `frontmatter` / HTML/PDF tests | 3 full-suite check |
| JSON goldens Content-shaped | 1 `from_mapping` parametrize (no invented `.md`) |

**Placeholders:** none.

**Type consistency:** `parse_markdown` → `dict[str, object]`; `Content.from_mapping` → `Content`; `Document.content: Content`; `Document.parse(..., source_format=)`; social/nodes stored as tuples, parser lists.

---

## Execution notes for the one agent

- Work on the current branch (`feat/markdown-to-pdf`). Do not create a new worktree unless asked.
- TDD: red → implement → green → commit, per task.
- After Task 2, `Document` still uses `format`/`data` until Task 3. That is a temporary name; do not stop after Task 2.
- If `uv run pytest` shows failures in `test_generate_pdf.py` / `test_frontmatter.py` / `test_cli.py`, those files were not supposed to change — stop and revert.
