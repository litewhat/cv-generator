import pytest

from cv_generator.frontmatter import parse_frontmatter


def test_no_frontmatter_returns_empty_meta_and_original_text():
    text = "# Hello\n\n- item\n"
    meta, body = parse_frontmatter(text)
    assert meta == {}
    assert body == text


def test_frontmatter_not_at_start_is_not_frontmatter():
    md = "Intro\n---\nname: Ada\n---\n# Summary\n"
    meta, body = parse_frontmatter(md)
    assert meta == {}
    assert body == md


def test_four_dashes_is_not_an_opener():
    md = "----\nname: Ada\n---\n# Summary\n"
    meta, body = parse_frontmatter(md)
    assert meta == {}
    assert body == md


def test_valid_frontmatter_extracted():
    md = """---
name: Ada Lovelace
title: Software Engineer
email: ada@example.com
location: Warsaw, Poland
links:
  github: https://github.com/ada
---
# Summary
Hello
"""
    meta, body = parse_frontmatter(md)
    assert meta["name"] == "Ada Lovelace"
    assert meta["title"] == "Software Engineer"
    assert meta["email"] == "ada@example.com"
    assert meta["location"] == "Warsaw, Poland"
    assert meta["links"]["github"] == "https://github.com/ada"
    assert body.startswith("# Summary")
    assert "---" not in body


def test_unknown_keys_are_kept():
    md = "---\nname: Ada\nextra: keep-me\n---\n# Summary\n"
    meta, body = parse_frontmatter(md)
    assert meta["name"] == "Ada"
    assert meta["extra"] == "keep-me"
    assert body.startswith("# Summary")


def test_empty_frontmatter_returns_empty_dict():
    md = "---\n---\n# Summary\n"
    meta, body = parse_frontmatter(md)
    assert meta == {}
    assert body.startswith("# Summary")


def test_whitespace_only_frontmatter_returns_empty_dict():
    md = "---\n  \n---\n# Summary\n"
    meta, body = parse_frontmatter(md)
    assert meta == {}
    assert body.startswith("# Summary")


def test_yaml_null_frontmatter_returns_empty_dict():
    md = "---\nnull\n---\n# Summary\n"
    meta, body = parse_frontmatter(md)
    assert meta == {}
    assert body.startswith("# Summary")


def test_missing_closing_delimiter_raises():
    md = "---\nname: Ada\n# Summary\nHello\n"
    with pytest.raises(ValueError, match="Unclosed YAML frontmatter"):
        parse_frontmatter(md)


def test_invalid_yaml_raises_value_error():
    md = "---\nname: [unclosed\n---\n# Summary\n"
    with pytest.raises(ValueError, match="Invalid YAML frontmatter"):
        parse_frontmatter(md)


def test_non_mapping_raises():
    md = "---\n- just a list\n---\n# Summary\n"
    with pytest.raises(ValueError, match="Frontmatter must be a mapping"):
        parse_frontmatter(md)


def test_crlf_and_whitespace_after_dashes():
    md = "---  \r\nname: Ada\r\n---\r\n# Summary\r\n"
    meta, body = parse_frontmatter(md)
    assert meta["name"] == "Ada"
    assert body.startswith("# Summary")


def test_bom_with_frontmatter_is_parsed():
    md = "\ufeff---\nname: Ada\n---\n# Summary\n"
    meta, body = parse_frontmatter(md)
    assert meta["name"] == "Ada"
    assert body.startswith("# Summary")
    assert not body.startswith("\ufeff")


def test_bom_without_frontmatter_returns_original():
    md = "\ufeff# Hello\n"
    meta, body = parse_frontmatter(md)
    assert meta == {}
    assert body == md


def test_non_scalar_name_raises():
    md = "---\nname:\n  first: Ada\n---\n# Summary\n"
    with pytest.raises(ValueError, match="Frontmatter field 'name' must be a scalar"):
        parse_frontmatter(md)


def test_null_name_is_allowed():
    md = "---\nname: null\ntitle: Engineer\n---\n# Summary\n"
    meta, body = parse_frontmatter(md)
    assert meta["name"] is None
    assert meta["title"] == "Engineer"


def test_links_as_string_raises():
    md = "---\nname: Ada\nlinks: https://github.com/ada\n---\n# Summary\n"
    with pytest.raises(ValueError, match="Frontmatter field 'links' must be a mapping"):
        parse_frontmatter(md)


def test_links_nested_value_raises():
    md = "---\nlinks:\n  github:\n    url: https://github.com/ada\n---\n# Summary\n"
    with pytest.raises(ValueError, match="Frontmatter field 'links' must be a mapping of scalars"):
        parse_frontmatter(md)


def test_null_links_is_allowed():
    md = "---\nname: Ada\nlinks: null\n---\n# Summary\n"
    meta, _body = parse_frontmatter(md)
    assert meta["name"] == "Ada"
    assert meta["links"] is None


def test_unknown_nested_key_is_not_type_checked():
    md = "---\nextra:\n  nested: 1\n---\n# Summary\n"
    meta, body = parse_frontmatter(md)
    assert meta["extra"] == {"nested": 1}
    assert body.startswith("# Summary")
