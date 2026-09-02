from cv_generator.document import Content, Document
from cv_generator.formatter import to_html

_HEADER = {
    "name": "Ada Lovelace",
    "title": "Software Engineer",
    "email": "ada@example.com",
    "phone_number": "+48 111 222 333",
    "location": "Warsaw, Poland",
}


def _document(**overrides: object) -> Document:
    raw: dict[str, object] = dict(_HEADER)
    raw.update(overrides)
    return Document(source_format="markdown", content=Content.from_mapping(raw))


_MD_HEADER = """\
---
name: Ada Lovelace
title: Software Engineer
email: ada@example.com
phone: "+48 111 222 333"
location: Warsaw, Poland
---

"""

_FENCE = chr(96) * 3


def _parse(body: str) -> Document:
    return Document.parse(_MD_HEADER + body, format="markdown")


def _body(html: str) -> str:
    start = html.index('<main class="cv-body">')
    end = html.index("</main>", start)
    return html[start:end]


class TestPageShell:
    def test_doctype_and_title(self):
        html = to_html(_document())
        stripped = html.lstrip()
        assert stripped.startswith("<!DOCTYPE html>") or stripped.lower().startswith(
            "<!doctype html>"
        )
        assert "<title>Ada Lovelace - Software Engineer</title>" in html

    def test_title_escapes_name_and_job_title(self):
        html = to_html(_document(name="Ada < X", title="Engineer & Manager"))
        assert "<title>Ada &lt; X - Engineer &amp; Manager</title>" in html

    def test_elegant_v1_tokens_and_a4(self):
        html = to_html(_document())
        assert "--accent: #2f5d62" in html
        assert "font-variant-ligatures: none" in html
        assert "Palatino" in html
        assert 'class="cv-body"' in html
        assert "@page" in html
        assert "A4" in html

    def test_shell_is_not_multi_column(self):
        html = to_html(_document())
        assert "display: grid" not in html
        assert "display:grid" not in html
        assert "display: flex" not in html
        assert "display:flex" not in html
        assert "position: absolute" not in html
        assert "position:absolute" not in html


class TestHeader:
    def test_required_fields_mailto_and_contacts(self):
        html = to_html(_document())
        header = html.split("<main")[0]
        assert 'class="cv-header"' in header
        assert "<h1>Ada Lovelace</h1>" in header
        assert 'class="cv-title"' in header
        assert "Software Engineer" in header
        assert 'href="mailto:ada@example.com"' in header
        assert "ada@example.com" in header
        assert "+48 111 222 333" in header
        assert "Warsaw, Poland" in header
        assert 'class="cv-sep"' in header

    def test_social_profiles_labels_and_urls(self):
        html = to_html(
            _document(
                social_profiles=[
                    {"type": "github", "url": "https://github.com/ada"},
                    {"type": "linkedin", "url": "https://linkedin.com/in/ada"},
                ]
            )
        )
        header = html.split("<main")[0]
        assert 'class="cv-links"' in header
        assert 'href="https://github.com/ada"' in header
        assert ">github</a>" in header
        assert 'href="https://linkedin.com/in/ada"' in header
        assert ">linkedin</a>" in header

    def test_omits_links_row_when_social_profiles_empty(self):
        html = to_html(_document())
        header = html.split("<main")[0]
        assert 'class="cv-links"' not in header

    def test_escapes_name_email_and_url(self):
        html = to_html(
            _document(
                name="A < B",
                email='x@y.com"><img>',
                social_profiles=[
                    {"type": "github", "url": 'https://example.com/">xss'},
                ],
            )
        )
        header = html.split("<main")[0]
        assert "<h1>A &lt; B</h1>" in header
        assert "<h1>A < B</h1>" not in header
        assert "https://example.com/&#34;&gt;xss" in header or "https://example.com/&quot;&gt;xss" in header
        assert 'href="https://example.com/">xss"' not in header


class TestBodyHeadings:
    def test_root_h2_becomes_h1(self):
        html = _body(to_html(_parse("## Experience\n")))
        assert "<h1>Experience</h1>" in html
        assert "<h2>Experience</h2>" not in html

    def test_nested_headings_follow_tree_depth(self):
        html = _body(
            to_html(
                _parse(
                    "## Experience\n\n### Northwind\n\n#### Checkout\n"
                )
            )
        )
        assert "<h1>Experience</h1>" in html
        assert "<h2>Northwind</h2>" in html
        assert "<h3>Checkout</h3>" in html

    def test_heading_depth_caps_at_h6(self):
        node: dict[str, object] = {"name": "L7", "nodes": []}
        for name in ("L6", "L5", "L4", "L3", "L2", "L1"):
            node = {"name": name, "nodes": [node]}
        html = _body(to_html(_document(nodes=[node])))
        assert "<h1>L1</h1>" in html
        assert "<h6>L6</h6>" in html
        assert "<h6>L7</h6>" in html
        assert "<h7" not in html

    def test_empty_node_still_emits_heading(self):
        html = _body(to_html(_parse("## Experience\n")))
        assert "<h1>Experience</h1>" in html

    def test_heading_names_are_escaped_not_markdown(self):
        html = _body(to_html(_parse("## A < B **x**\n")))
        assert "<h1>A &lt; B **x**</h1>" in html
        assert "<strong>" not in html


class TestBodyRoot:
    def test_root_plains_are_paragraphs(self):
        html = _body(
            to_html(_parse("Builds payment systems.\n\nPrefers small teams.\n"))
        )
        assert "<p>Builds payment systems.</p>" in html
        assert "<p>Prefers small teams.</p>" in html
        assert "<ul>" not in html

    def test_root_plain_keeps_inline_markdown(self):
        html = _body(to_html(_parse("Hello **Ada**\n")))
        assert "<p>Hello <strong>Ada</strong></p>" in html


class TestBodyLists:
    def test_consecutive_plains_under_heading_are_one_ul(self):
        html = _body(
            to_html(
                _parse(
                    "## Experience\n\n"
                    "### Northwind\n\n"
                    "- Led the checkout rewrite\n"
                    "- Shipped **v2**\n"
                )
            )
        )
        assert "<h1>Experience</h1>" in html
        assert "<h2>Northwind</h2>" in html
        assert html.count("<ul>") == 1
        assert "<li>Led the checkout rewrite</li>" in html
        assert "<li>Shipped <strong>v2</strong></li>" in html
        assert "<li><p>" not in html

    def test_single_plain_under_heading_is_still_a_ul(self):
        html = _body(to_html(_parse("## Education\n\nBSc Computer Science\n")))
        assert "<h1>Education</h1>" in html
        assert "<ul>" in html
        assert "<li>BSc Computer Science</li>" in html

    def test_mixed_children_flush_and_restart(self):
        html = _body(
            to_html(
                Document(
                    source_format="markdown",
                    content=Content.from_mapping(
                        {
                            **_HEADER,
                            "nodes": [
                                {
                                    "name": "Skills",
                                    "nodes": [
                                        "TypeScript, Python, SQL",
                                        {"name": "Platforms", "nodes": ["AWS", "GCP"]},
                                        "Spoken languages: English, Polish",
                                    ],
                                }
                            ],
                        }
                    ),
                )
            )
        )
        assert "<h1>Skills</h1>" in html
        assert "<h2>Platforms</h2>" in html
        assert html.count("<ul>") == 3
        assert "<li>TypeScript, Python, SQL</li>" in html
        assert "<li>AWS</li>" in html
        assert "<li>GCP</li>" in html
        assert "<li>Spoken languages: English, Polish</li>" in html

    def test_spec_worked_example_body_structure(self):
        html = _body(
            to_html(
                _parse(
                    "Builds payment systems.\n\n"
                    "## Experience\n\n"
                    "### Northwind\n\n"
                    "- Led the checkout rewrite\n"
                    "- Shipped **v2**\n"
                )
            )
        )
        assert "<p>Builds payment systems.</p>" in html
        assert "<h1>Experience</h1>" in html
        assert "<h2>Northwind</h2>" in html
        assert "<li>Led the checkout rewrite</li>" in html
        assert "<li>Shipped <strong>v2</strong></li>" in html


class TestBodyBlocks:
    def test_root_fence_is_pre_not_list(self):
        html = _body(to_html(_parse(f"{_FENCE}python\nx = 1\n{_FENCE}\n")))
        assert "<pre>" in html
        assert "<ul>" not in html
        assert "<li>" not in html

    def test_fence_is_sibling_block_not_li(self):
        html = _body(
            to_html(
                _parse(
                    f"## Code\n\n{_FENCE}python\nx = 1\n{_FENCE}\n"
                )
            )
        )
        assert "<h1>Code</h1>" in html
        assert "<pre>" in html
        assert "x = 1" in html
        assert "<li>" not in html

    def test_tilde_fence_is_classified_as_fence(self):
        html = _body(to_html(_parse("## Code\n\n~~~\nx = 1\n~~~\n")))
        assert "<pre>" in html
        assert "<li>" not in html

    def test_table_is_sibling_block_not_li(self):
        html = _body(
            to_html(_parse("## Skills\n\n| A | B |\n| --- | --- |\n| 1 | 2 |\n"))
        )
        assert "<table>" in html
        assert "<th>A</th>" in html
        assert "<td>1</td>" in html
        assert "<li>" not in html

    def test_thematic_break_is_sibling_block_not_li(self):
        html = _body(to_html(_parse("## Experience\n\n---\n")))
        assert "<h1>Experience</h1>" in html
        assert "<hr" in html
        assert "<li>" not in html
