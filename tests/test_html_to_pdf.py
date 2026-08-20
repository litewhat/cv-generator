from pathlib import Path

from cv_generator.html_to_pdf import html_to_pdf

_MINIMAL_HTML = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>t</title></head>
<body><h1>Hello</h1></body>
</html>
"""


def test_html_to_pdf_returns_pdf_bytes(tmp_path: Path):
    pdf = html_to_pdf(_MINIMAL_HTML, base_url=tmp_path)
    assert isinstance(pdf, bytes)
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 0


def test_html_to_pdf_accepts_string_base_url(tmp_path: Path):
    pdf = html_to_pdf(_MINIMAL_HTML, base_url=str(tmp_path))
    assert pdf.startswith(b"%PDF")
