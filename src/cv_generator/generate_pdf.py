import os
import tempfile
from pathlib import Path

from cv_generator.frontmatter import parse_frontmatter
from cv_generator.html_document import html_document
from cv_generator.html_to_pdf import html_to_pdf
from cv_generator.markdown_to_html import markdown_to_html


class CvGeneratorError(Exception):
    """Render or conversion failure for the CLI to report (exit 1)."""


def generate_pdf(input_path: Path, output_path: Path) -> None:
    input_path = Path(input_path)
    output_path = Path(output_path)

    if not input_path.exists():
        raise FileNotFoundError(f"Input not found: {input_path}")
    if input_path.is_dir():
        raise IsADirectoryError(f"Input is a directory: {input_path}")
    if not input_path.is_file():
        raise FileNotFoundError(f"Input is not a file: {input_path}")
    if output_path.exists() and output_path.is_dir():
        raise IsADirectoryError(f"Output is a directory: {output_path}")

    text = input_path.read_text(encoding="utf-8")

    try:
        meta, body = parse_frontmatter(text)
        fragment = markdown_to_html(body)
        document = html_document(fragment, title=input_path.stem, meta=meta)
        pdf_bytes = html_to_pdf(document, base_url=input_path.parent)
    except Exception as exc:
        raise CvGeneratorError(str(exc)) from exc

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=".cv-generator-",
        suffix=".pdf",
        dir=output_path.parent,
    )
    try:
        with os.fdopen(fd, "wb") as tmp_file:
            tmp_file.write(pdf_bytes)
        os.replace(tmp_name, output_path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise
