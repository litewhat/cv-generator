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
