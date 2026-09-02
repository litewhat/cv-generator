import json
from pathlib import Path

import pytest

from cv_generator.document import (
    Content,
    Document,
    Node,
    SocialProfile,
    ValidationError,
)
from cv_generator.parser import ParseError, from_markdown

_EXAMPLES = (
    Path(__file__).resolve().parents[2] / "examples" / "cv_generator" / "document"
)

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
            {"type": profile.type, "url": profile.url}
            for profile in content.social_profiles
        ],
        "nodes": [_node_to_json(node) for node in content.nodes],
    }


def _sample_content() -> Content:
    return Content(
        name="Ada Lovelace",
        title="Software Engineer",
        email="ada@example.com",
        phone_number="+48 111 222 333",
        location="Warsaw, Poland",
        social_profiles=(SocialProfile(type="github", url="https://github.com/ada"),),
        nodes=(
            "Intro",
            Node(name="Experience", nodes=("Did a thing",)),
        ),
    )


_MD = """---
name: Ada Lovelace
title: Software Engineer
email: ada@example.com
phone: "+48 111 222 333"
location: Warsaw, Poland
---

## Experience

Did a thing.
"""


class TestExceptions:
    def test_validation_error_is_a_sibling_of_parse_error(self):
        assert issubclass(ValidationError, Exception)
        assert not issubclass(ValidationError, ValueError)
        assert not issubclass(ValidationError, ParseError)
        assert not issubclass(ParseError, ValidationError)

    def test_parse_error_is_an_exception(self):
        assert issubclass(ParseError, Exception)
        assert not issubclass(ParseError, ValueError)

    def test_parse_value_error_is_not_parse_or_validation_error(self):
        with pytest.raises(ValueError) as excinfo:
            Document.parse(_MD, format="html")
        assert not isinstance(excinfo.value, ParseError)
        assert not isinstance(excinfo.value, ValidationError)


class TestContentFromMappingHeader:
    def test_from_mapping_reads_required_header_fields(self):
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

    def test_from_mapping_strips_header_strings(self):
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

    def test_from_mapping_ignores_extra_keys_including_format(self):
        content = Content.from_mapping(
            _header(website="https://ada.dev", format="markdown")
        )
        assert content.name == "Ada Lovelace"
        assert not hasattr(content, "website")

    def test_from_mapping_does_not_read_phone_or_links_aliases(self):
        raw = _header()
        del raw["phone_number"]
        raw["phone"] = "+48 111 222 333"
        with pytest.raises(ValidationError, match="Missing field 'phone_number'"):
            Content.from_mapping(raw)

    @pytest.mark.parametrize(
        "key", ["name", "title", "email", "phone_number", "location"]
    )
    def test_from_mapping_missing_header_field_raises(self, key: str):
        raw = _header()
        del raw[key]
        with pytest.raises(ValidationError, match=f"Missing field '{key}'"):
            Content.from_mapping(raw)

    @pytest.mark.parametrize(
        "key", ["name", "title", "email", "phone_number", "location"]
    )
    def test_from_mapping_empty_header_field_raises(self, key: str):
        with pytest.raises(
            ValidationError, match=f"Field '{key}' must be a non-empty string"
        ):
            Content.from_mapping(_header(**{key: "   "}))

    def test_from_mapping_non_string_title_raises(self):
        with pytest.raises(ValidationError, match="Field 'title' must be a string"):
            Content.from_mapping(_header(title=1))

    def test_from_mapping_rejects_non_mapping(self):
        with pytest.raises(ValidationError, match="Expected a mapping"):
            Content.from_mapping(["not", "a", "mapping"])


class TestContentFromMappingSocial:
    def test_from_mapping_absent_social_profiles_is_empty(self):
        assert Content.from_mapping(_VALID_HEADER).social_profiles == ()

    def test_from_mapping_none_social_profiles_is_empty(self):
        assert Content.from_mapping(_header(social_profiles=None)).social_profiles == ()

    def test_from_mapping_empty_social_profiles_sequence_is_empty(self):
        assert Content.from_mapping(_header(social_profiles=[])).social_profiles == ()
        assert Content.from_mapping(_header(social_profiles=())).social_profiles == ()

    def test_from_mapping_social_profiles_preserve_list_order(self):
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

    def test_from_mapping_social_profiles_ignore_extra_keys(self):
        content = Content.from_mapping(
            _header(
                social_profiles=[
                    {
                        "type": "github",
                        "url": "https://github.com/ada",
                        "note": "personal",
                    },
                ]
            )
        )
        assert content.social_profiles == (
            SocialProfile(type="github", url="https://github.com/ada"),
        )

    def test_from_mapping_empty_url_is_allowed(self):
        content = Content.from_mapping(
            _header(social_profiles=[{"type": "github", "url": ""}])
        )
        assert content.social_profiles == (SocialProfile(type="github", url=""),)

    def test_from_mapping_unknown_social_type_raises(self):
        with pytest.raises(ValidationError, match="Unsupported social profile type"):
            Content.from_mapping(
                _header(
                    social_profiles=[
                        {"type": "twitter", "url": "https://twitter.com/ada"}
                    ]
                )
            )

    def test_from_mapping_social_profiles_string_raises(self):
        with pytest.raises(
            ValidationError, match="Field 'social_profiles' must be a sequence"
        ):
            Content.from_mapping(_header(social_profiles="https://github.com/ada"))

    def test_from_mapping_nested_profile_url_raises(self):
        with pytest.raises(ValidationError, match="Field 'url' must be a string"):
            Content.from_mapping(
                _header(
                    social_profiles=[
                        {"type": "github", "url": {"href": "https://github.com/ada"}}
                    ]
                )
            )

    def test_from_mapping_profile_not_a_mapping_raises(self):
        with pytest.raises(ValidationError, match="Social profile must be a mapping"):
            Content.from_mapping(_header(social_profiles=["github"]))


class TestContentFromMappingNodes:
    def test_from_mapping_absent_nodes_is_empty(self):
        assert Content.from_mapping(_VALID_HEADER).nodes == ()

    def test_from_mapping_none_nodes_is_empty(self):
        assert Content.from_mapping(_header(nodes=None)).nodes == ()

    def test_from_mapping_nodes_accepts_tuple(self):
        content = Content.from_mapping(_header(nodes=("Intro",)))
        assert content.nodes == ("Intro",)

    def test_from_mapping_nodes_mixed_children(self):
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

    def test_from_mapping_node_strips_name_and_defaults_missing_nodes(self):
        content = Content.from_mapping(
            _header(nodes=[{"name": "  Experience  ", "extra": True}])
        )
        assert content.nodes == (Node(name="Experience", nodes=()),)

    def test_from_mapping_nodes_string_raises(self):
        with pytest.raises(ValidationError, match="Field 'nodes' must be a sequence"):
            Content.from_mapping(_header(nodes="Intro"))

    def test_from_mapping_missing_node_name_raises(self):
        with pytest.raises(ValidationError, match="Missing field 'name'"):
            Content.from_mapping(_header(nodes=[{"nodes": ["Did a thing"]}]))

    def test_from_mapping_empty_node_name_raises(self):
        with pytest.raises(
            ValidationError, match="Field 'name' must be a non-empty string"
        ):
            Content.from_mapping(_header(nodes=[{"name": "   ", "nodes": []}]))

    def test_from_mapping_non_string_node_name_raises(self):
        with pytest.raises(ValidationError, match="Field 'name' must be a string"):
            Content.from_mapping(_header(nodes=[{"name": 1, "nodes": []}]))

    def test_from_mapping_node_child_neither_str_nor_mapping_raises(self):
        with pytest.raises(
            ValidationError, match="Node child must be a string or mapping"
        ):
            Content.from_mapping(_header(nodes=[{"name": "Experience", "nodes": [1]}]))

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
    def test_from_mapping_accepts_example_goldens(self, filename: str):
        raw = json.loads((_EXAMPLES / filename).read_text(encoding="utf-8"))
        assert _content_to_json(Content.from_mapping(raw)) == raw


class TestDocumentModel:
    def test_content_holds_all_header_fields_and_nodes(self):
        data = _sample_content()
        assert data.name == "Ada Lovelace"
        assert data.title == "Software Engineer"
        assert data.email == "ada@example.com"
        assert data.phone_number == "+48 111 222 333"
        assert data.location == "Warsaw, Poland"
        assert data.social_profiles[0].type == "github"
        assert data.nodes[0] == "Intro"
        assert data.nodes[1].name == "Experience"

    def test_document_exposes_public_source_format_and_content(self):
        content = _sample_content()
        document = Document(source_format="markdown", content=content)
        assert document.source_format == "markdown"
        assert document.content is content


class TestDocumentParse:
    def test_parse_equals_from_mapping_of_from_markdown(self):
        document = Document.parse(_MD)
        assert document == Document(
            source_format="markdown",
            content=Content.from_mapping(from_markdown(_MD)),
        )
        assert document.source_format == "markdown"
        assert document.content.nodes[0].name == "Experience"

    def test_parse_default_source_format_is_markdown(self):
        assert Document.parse(_MD).source_format == "markdown"

    def test_parse_explicit_markdown_source_format_matches_default(self):
        default = Document.parse(_MD)
        explicit = Document.parse(_MD, format="markdown")
        assert default == explicit
        assert explicit.source_format == "markdown"

    def test_parse_unsupported_source_format_raises_value_error(self):
        with pytest.raises(ValueError, match="Unsupported source_format"):
            Document.parse(_MD, format="html")

    def test_parse_empty_source_raises_validation_error(self):
        with pytest.raises(ValidationError, match="Missing field 'name'"):
            Document.parse("")

    def test_parse_body_without_frontmatter_raises_validation_error(self):
        with pytest.raises(ValidationError, match="Missing field 'name'"):
            Document.parse("# Hello\n")

    def test_parse_unclosed_yaml_raises_parse_error(self):
        with pytest.raises(ParseError, match="Unclosed YAML frontmatter"):
            Document.parse("---\nname: Ada\n")

    def test_parse_does_not_convert_parse_error_into_validation_error(self):
        with pytest.raises(ParseError):
            Document.parse("---\nname: Ada\n")
