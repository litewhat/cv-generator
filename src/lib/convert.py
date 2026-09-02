from pathlib import Path

import markdown
from weasyprint import HTML

_EXTENSIONS = ["fenced_code", "tables", "sane_lists"]


def markdown_to_html(markdown_text: str) -> str:
    return markdown.markdown(markdown_text, extensions=_EXTENSIONS)


def html_to_pdf(html: str, *, base_url: str | Path) -> bytes:
    pdf = HTML(string=html, base_url=str(base_url)).write_pdf()
    if not pdf:
        raise RuntimeError("WeasyPrint returned no PDF bytes")
    return pdf
