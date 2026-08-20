from pathlib import Path


def html_to_pdf(html: str, *, base_url: str | Path) -> bytes:
    from weasyprint import HTML

    pdf = HTML(string=html, base_url=str(base_url)).write_pdf()
    if not pdf:
        raise RuntimeError("WeasyPrint returned no PDF bytes")
    return pdf
