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
