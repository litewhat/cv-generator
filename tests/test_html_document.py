from cv_generator.html_document import html_document


def test_html_document_is_full_page_with_title_and_content():
    html = html_document("<p>Hello</p>", "My Title")
    stripped = html.lstrip()
    assert stripped.startswith("<!DOCTYPE html>") or stripped.lower().startswith("<!doctype html>")
    assert "<title>My Title</title>" in html
    assert "<p>Hello</p>" in html


def test_html_document_does_not_escape_content_tags():
    html = html_document("<h1>X</h1>", "t")
    assert "<h1>X</h1>" in html
    assert "&lt;h1&gt;" not in html


def test_html_document_escapes_title():
    html = html_document("<p>x</p>", "A < B")
    assert "A &lt; B" in html


def test_html_document_includes_a4_page_css():
    html = html_document("<p>x</p>", "t")
    assert "@page" in html
    assert "A4" in html


def test_html_document_uses_elegant_v1_tokens():
    html = html_document("<p>Hello</p>", "t")
    assert "--accent: #2f5d62" in html
    assert "font-variant-ligatures: none" in html
    assert "Palatino" in html
    assert 'class="cv-body"' in html
    assert "@page" in html
    assert "A4" in html


def test_html_document_omits_header_without_meta():
    html = html_document("<h1>Summary</h1>", "t")
    assert 'class="cv-header"' not in html
    assert "<h1>Summary</h1>" in html
    assert 'class="cv-body"' in html


def test_html_document_renders_meta_header():
    html = html_document(
        "<h1>Summary</h1><p>Profile</p>",
        "ignored-title",
        meta={
            "name": "Ada Lovelace",
            "title": "Software Engineer",
            "email": "ada@example.com",
            "phone": "+48 000 000 000",
            "location": "Warsaw, Poland",
            "links": {
                "linkedin": "https://linkedin.com/in/ada",
                "github": "https://github.com/ada",
            },
        },
    )
    assert 'class="cv-header"' in html
    assert "<h1>Ada Lovelace</h1>" in html
    assert "Software Engineer" in html
    assert "ada@example.com" in html
    assert "+48 000 000 000" in html
    assert "Warsaw, Poland" in html
    assert 'href="https://linkedin.com/in/ada"' in html
    assert "linkedin" in html
    assert 'href="https://github.com/ada"' in html
    assert "<h1>Summary</h1>" in html
    assert "<p>Profile</p>" in html


def test_html_document_escapes_meta_name():
    html = html_document("<p>x</p>", "t", meta={"name": "A < B"})
    assert "<h1>A &lt; B</h1>" in html
    assert "<h1>A < B</h1>" not in html


def test_html_document_escapes_link_url():
    html = html_document(
        "<p>x</p>",
        "t",
        meta={
            "name": "N",
            "links": {"x": 'https://example.com/">xss'},
        },
    )
    assert "https://example.com/&#34;&gt;xss" in html or "https://example.com/&quot;&gt;xss" in html
    assert 'href="https://example.com/">xss"' not in html


def test_html_document_shell_is_not_multi_column():
    html = html_document("<p>x</p>", "t")
    assert "display: grid" not in html
    assert "display:grid" not in html
    assert "display: flex" not in html
    assert "display:flex" not in html
    assert "position: absolute" not in html
    assert "position:absolute" not in html


def test_html_document_does_not_invent_name_from_title():
    html = html_document(
        "<p>x</p>",
        "Doc Title",
        meta={"title": "Software Engineer", "email": "a@b.c"},
    )
    header = html.split("<main")[0]
    assert 'class="cv-header"' in header
    assert "Software Engineer" in header
    assert "a@b.c" in header
    assert "<h1>" not in header
    assert "<title>Doc Title</title>" in html
