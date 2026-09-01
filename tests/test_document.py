import pytest

from cv_generator.document import Data, Document, Node, ParseError, SocialProfile
from cv_generator.parse_markdown import parse_markdown


def _sample_data() -> Data:
    return Data(
        name="Ada Lovelace",
        title="Software Engineer",
        email="ada@example.com",
        phone_number="+48 111 222 333",
        location="Warsaw, Poland",
        social_profiles=(
            SocialProfile(type="github", url="https://github.com/ada"),
        ),
        nodes=(
            "Intro",
            Node(name="Experience", nodes=("Did a thing",)),
        ),
    )


def test_parse_error_is_an_exception():
    assert issubclass(ParseError, Exception)
    assert not issubclass(ParseError, ValueError)


def test_data_holds_all_header_fields_and_nodes():
    data = _sample_data()
    assert data.name == "Ada Lovelace"
    assert data.title == "Software Engineer"
    assert data.email == "ada@example.com"
    assert data.phone_number == "+48 111 222 333"
    assert data.location == "Warsaw, Poland"
    assert data.social_profiles[0].type == "github"
    assert data.nodes[0] == "Intro"
    assert data.nodes[1].name == "Experience"


def test_document_exposes_public_format_and_data():
    data = _sample_data()
    document = Document(format="markdown", data=data)
    assert document.format == "markdown"
    assert document.data is data


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


def test_parse_wraps_parse_markdown_data():
    document = Document.parse(_MD)
    assert document.format == "markdown"
    assert document.data == parse_markdown(_MD)
    assert document.data.nodes[0].name == "Experience"


def test_parse_default_format_is_markdown():
    document = Document.parse(_MD)
    assert document.format == "markdown"


def test_parse_explicit_markdown_format():
    document = Document.parse(_MD, format="markdown")
    assert document.format == "markdown"
    assert document.data == parse_markdown(_MD)


def test_parse_unsupported_format_raises_value_error():
    with pytest.raises(ValueError, match="Unsupported format"):
        Document.parse(_MD, format="html")  # type: ignore[arg-type]


def test_parse_does_not_turn_source_errors_into_value_error():
    with pytest.raises(ParseError, match="Missing frontmatter field 'name'"):
        Document.parse("")
