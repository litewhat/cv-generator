from pathlib import Path

from lib.convert import html_to_pdf, markdown_to_html

_FENCE = chr(96) * 3

_MINIMAL_HTML = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>t</title></head>
<body><h1>Hello</h1></body>
</html>
"""


class TestMarkdownToHtml:
    def test_heading_becomes_h1(self):
        html = markdown_to_html("# Hello")
        assert "<h1>Hello</h1>" in html
        assert "<html" not in html.lower()
        assert "<body" not in html.lower()

    def test_fenced_code_becomes_pre_code(self):
        html = markdown_to_html(f"{_FENCE}python\nx = 1\n{_FENCE}")
        assert "<pre>" in html
        assert '<code class="language-python">' in html
        assert "x = 1" in html
        assert "codehilite" not in html
        assert "<span" not in html

    def test_table_becomes_table_tags(self):
        html = markdown_to_html("| A | B |\n| --- | --- |\n| 1 | 2 |\n")
        assert "<table>" in html
        assert "<th>A</th>" in html
        assert "<td>1</td>" in html

    def test_unordered_list_becomes_ul(self):
        html = markdown_to_html("- a\n- b\n")
        assert "<ul>" in html
        assert "<li>a</li>" in html
        assert "<li>b</li>" in html


class TestHtmlToPdf:
    def test_returns_pdf_bytes(self, tmp_path: Path):
        pdf = html_to_pdf(_MINIMAL_HTML, base_url=tmp_path)
        assert isinstance(pdf, bytes)
        assert pdf.startswith(b"%PDF")
        assert len(pdf) > 0

    def test_accepts_string_base_url(self, tmp_path: Path):
        pdf = html_to_pdf(_MINIMAL_HTML, base_url=str(tmp_path))
        assert pdf.startswith(b"%PDF")
