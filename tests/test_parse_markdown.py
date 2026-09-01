import pytest

from cv_generator.document import Data, Node, ParseError, SocialProfile
from cv_generator.parse_markdown import parse_markdown

_HEADER = """---
name: Ada Lovelace
title: Software Engineer
email: ada@example.com
phone: "+48 111 222 333"
location: Warsaw, Poland
---
"""


def test_header_only_maps_into_data():
    data = parse_markdown(_HEADER)
    assert data == Data(
        name="Ada Lovelace",
        title="Software Engineer",
        email="ada@example.com",
        phone_number="+48 111 222 333",
        location="Warsaw, Poland",
        social_profiles=(),
        nodes=(),
    )


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
    data = parse_markdown(md)
    assert data.social_profiles == (
        SocialProfile(type="linkedin", url="https://linkedin.com/in/ada"),
        SocialProfile(type="github", url="https://github.com/ada"),
    )


def test_missing_links_yields_empty_social_profiles():
    data = parse_markdown(_HEADER)
    assert data.social_profiles == ()


def test_null_links_yields_empty_social_profiles():
    md = """---
name: Ada Lovelace
title: Software Engineer
email: ada@example.com
phone: "+48 111 222 333"
location: Warsaw, Poland
links: null
---
"""
    assert parse_markdown(md).social_profiles == ()


def test_empty_links_mapping_yields_empty_social_profiles():
    md = """---
name: Ada Lovelace
title: Software Engineer
email: ada@example.com
phone: "+48 111 222 333"
location: Warsaw, Poland
links: {}
---
"""
    assert parse_markdown(md).social_profiles == ()


def test_extra_yaml_keys_are_ignored():
    md = """---
name: Ada Lovelace
title: Software Engineer
email: ada@example.com
phone: "+48 111 222 333"
location: Warsaw, Poland
website: https://ada.dev
---
"""
    data = parse_markdown(md)
    assert data.name == "Ada Lovelace"
    assert not hasattr(data, "website")


def test_header_values_are_stripped():
    md = """---
name: "  Ada Lovelace  "
title: "  Software Engineer  "
email: "  ada@example.com  "
phone: "  +48 111 222 333  "
location: "  Warsaw, Poland  "
---
"""
    data = parse_markdown(md)
    assert data.name == "Ada Lovelace"
    assert data.title == "Software Engineer"
    assert data.email == "ada@example.com"
    assert data.phone_number == "+48 111 222 333"
    assert data.location == "Warsaw, Poland"


@pytest.mark.parametrize("key", ["name", "title", "email", "phone", "location"])
def test_missing_required_field_raises(key):
    fields = {
        "name": "Ada Lovelace",
        "title": "Software Engineer",
        "email": "ada@example.com",
        "phone": '"+48 111 222 333"',
        "location": "Warsaw, Poland",
    }
    del fields[key]
    yaml_block = "\n".join(f"{k}: {v}" for k, v in fields.items())
    md = f"---\n{yaml_block}\n---\n"
    with pytest.raises(ParseError, match=f"Missing frontmatter field '{key}'"):
        parse_markdown(md)


@pytest.mark.parametrize("key", ["name", "title", "email", "phone", "location"])
def test_empty_required_field_raises(key):
    fields = {
        "name": "Ada Lovelace",
        "title": "Software Engineer",
        "email": "ada@example.com",
        "phone": '"+48 111 222 333"',
        "location": "Warsaw, Poland",
    }
    fields[key] = '""'
    yaml_block = "\n".join(f"{k}: {v}" for k, v in fields.items())
    md = f"---\n{yaml_block}\n---\n"
    with pytest.raises(ParseError, match=f"Frontmatter field '{key}' must be a non-empty string"):
        parse_markdown(md)


def test_non_string_title_raises():
    md = """---
name: Ada Lovelace
title: 1
email: ada@example.com
phone: "+48 111 222 333"
location: Warsaw, Poland
---
"""
    with pytest.raises(ParseError, match="Frontmatter field 'title' must be a string"):
        parse_markdown(md)


def test_unknown_link_type_raises():
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
    with pytest.raises(ParseError, match="Unsupported social profile type"):
        parse_markdown(md)


def test_links_as_string_raises():
    md = """---
name: Ada Lovelace
title: Software Engineer
email: ada@example.com
phone: "+48 111 222 333"
location: Warsaw, Poland
links: https://github.com/ada
---
"""
    with pytest.raises(ParseError, match="Frontmatter field 'links' must be a mapping"):
        parse_markdown(md)


def test_nested_link_value_raises():
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
    with pytest.raises(ParseError, match="Frontmatter field 'links' values must be strings"):
        parse_markdown(md)


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


def test_empty_source_raises():
    with pytest.raises(ParseError, match="Missing frontmatter field 'name'"):
        parse_markdown("")


def test_body_without_frontmatter_raises():
    with pytest.raises(ParseError, match="Missing frontmatter field 'name'"):
        parse_markdown("# Hello\n")


def test_bom_with_valid_frontmatter():
    data = parse_markdown("\ufeff" + _HEADER)
    assert data.name == "Ada Lovelace"


def test_four_dashes_is_not_frontmatter():
    md = "----\nname: Ada Lovelace\n---\n"
    with pytest.raises(ParseError, match="Missing frontmatter field 'name'"):
        parse_markdown(md)


def _cv(body: str) -> str:
    return (
        "---\n"
        "name: Ada Lovelace\n"
        "title: Software Engineer\n"
        "email: ada@example.com\n"
        'phone: "+48 111 222 333"\n'
        "location: Warsaw, Poland\n"
        "---\n"
        f"{body}"
    )


def test_empty_body_has_no_nodes():
    assert parse_markdown(_HEADER).nodes == ()
    assert parse_markdown(_cv("\n\n")).nodes == ()


def test_root_paragraphs():
    data = parse_markdown(_cv("Python and Go.\n\nComfortable owning services.\n"))
    assert data.nodes == (
        "Python and Go.",
        "Comfortable owning services.",
    )


def test_multiline_paragraph_joins_with_newline():
    data = parse_markdown(_cv("Line one\nLine two\n"))
    assert data.nodes == ("Line one\nLine two",)


def test_h2_without_h1_is_a_root_node():
    data = parse_markdown(_cv("## Experience\n\nDid a thing.\n"))
    assert data.nodes == (
        Node(name="Experience", nodes=("Did a thing.",)),
    )


def test_nested_headings_follow_level():
    data = parse_markdown(
        _cv("## Experience\n\n### Northwind\n\n- Led checkout\n- Cut latency\n")
    )
    assert data.nodes == (
        Node(
            name="Experience",
            nodes=(
                Node(
                    name="Northwind",
                    nodes=("Led checkout", "Cut latency"),
                ),
            ),
        ),
    )


def test_skipped_heading_level_nests_under_nearest_shallower():
    data = parse_markdown(_cv("## Experience\n\n#### Team\n\nHired people.\n"))
    assert data.nodes == (
        Node(
            name="Experience",
            nodes=(Node(name="Team", nodes=("Hired people.",)),),
        ),
    )


def test_sibling_h2_closes_previous_branch():
    data = parse_markdown(
        _cv("## Experience\n\nAt Acme.\n\n## Education\n\nBSc CS.\n")
    )
    assert data.nodes == (
        Node(name="Experience", nodes=("At Acme.",)),
        Node(name="Education", nodes=("BSc CS.",)),
    )


def test_mixed_root_strings_and_sections():
    data = parse_markdown(
        _cv(
            "Builds payment systems.\n\n"
            "## Experience\n\n"
            "### Northwind\n\n"
            "- Led the checkout rewrite\n\n"
            "## Education\n\n"
            "BSc Computer Science, 2016\n"
        )
    )
    assert data.nodes == (
        "Builds payment systems.",
        Node(
            name="Experience",
            nodes=(
                Node(
                    name="Northwind",
                    nodes=("Led the checkout rewrite",),
                ),
            ),
        ),
        Node(name="Education", nodes=("BSc Computer Science, 2016",)),
    )


def test_mixed_children_under_a_heading():
    data = parse_markdown(
        _cv(
            "## Skills\n\n"
            "TypeScript, Python, SQL\n\n"
            "### Platforms\n\n"
            "- AWS\n"
            "- GCP\n\n"
            "Spoken languages: English, Polish\n"
        )
    )
    assert data.nodes == (
        Node(
            name="Skills",
            nodes=(
                "TypeScript, Python, SQL",
                Node(name="Platforms", nodes=("AWS", "GCP")),
                "Spoken languages: English, Polish",
            ),
        ),
    )


def test_nested_list_items_are_sibling_leaves():
    data = parse_markdown(_cv("- parent\n  - child\n"))
    assert data.nodes == ("parent", "child")


def test_inline_markdown_is_preserved():
    data = parse_markdown(_cv("A **bold** and `code` line.\n"))
    assert data.nodes == ("A **bold** and `code` line.",)


def test_hash_without_space_is_not_a_heading():
    data = parse_markdown(_cv("#not-a-heading\n"))
    assert data.nodes == ("#not-a-heading",)


def test_empty_heading_name_raises():
    with pytest.raises(ParseError, match="Empty heading name"):
        parse_markdown(_cv("#\n"))
    with pytest.raises(ParseError, match="Empty heading name"):
        parse_markdown(_cv("#   \n"))


def test_closing_atx_hashes_are_stripped_from_name():
    data = parse_markdown(_cv("## Experience ##\n\nHello\n"))
    assert data.nodes == (Node(name="Experience", nodes=("Hello",)),)


def test_fenced_code_is_an_opaque_leaf():
    data = parse_markdown(_cv("## Notes\n\n```python\nx = 1\n```\n"))
    assert data.nodes == (
        Node(name="Notes", nodes=("```python\nx = 1\n```",)),
    )


def test_thematic_break_is_an_opaque_leaf():
    data = parse_markdown(_cv("## Notes\n\n---\n"))
    assert data.nodes == (Node(name="Notes", nodes=("---",)),)
