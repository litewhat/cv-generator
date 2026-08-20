from cv_generator.markdown_to_html import markdown_to_html

_FENCE = chr(96) * 3


def test_heading_becomes_h1():
    html = markdown_to_html("# Hello")
    assert "<h1>Hello</h1>" in html
    assert "<html" not in html.lower()
    assert "<body" not in html.lower()


def test_fenced_code_becomes_pre_code():
    html = markdown_to_html(f"{_FENCE}python\nx = 1\n{_FENCE}")
    assert "<pre>" in html
    assert '<code class="language-python">' in html
    assert "x = 1" in html
    assert "codehilite" not in html
    assert "<span" not in html


def test_table_becomes_table_tags():
    html = markdown_to_html("| A | B |\n| --- | --- |\n| 1 | 2 |\n")
    assert "<table>" in html
    assert "<th>A</th>" in html
    assert "<td>1</td>" in html


def test_unordered_list_becomes_ul():
    html = markdown_to_html("- a\n- b\n")
    assert "<ul>" in html
    assert "<li>a</li>" in html
    assert "<li>b</li>" in html
