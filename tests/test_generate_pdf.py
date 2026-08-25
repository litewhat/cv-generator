import shutil
import subprocess
from pathlib import Path

import pytest

from cv_generator.generate_pdf import CvGeneratorError, generate_pdf
from cv_generator.html_document import html_document

_FENCE = chr(96) * 3
_MD = (
    "# Hello\n\n"
    "- one\n"
    "- two\n\n"
    f"{_FENCE}python\n"
    "x = 1\n"
    f"{_FENCE}\n\n"
    "| A | B |\n"
    "| --- | --- |\n"
    "| 1 | 2 |\n"
)


def test_generate_pdf_writes_valid_pdf(tmp_path: Path):
    source = tmp_path / "cv.md"
    source.write_text(_MD, encoding="utf-8")
    output = tmp_path / "cv.pdf"
    generate_pdf(source, output)
    data = output.read_bytes()
    assert data.startswith(b"%PDF")
    assert output.stat().st_size > 0


def test_empty_markdown_writes_valid_pdf(tmp_path: Path):
    source = tmp_path / "empty.md"
    source.write_text("", encoding="utf-8")
    output = tmp_path / "empty.pdf"
    generate_pdf(source, output)
    assert output.read_bytes().startswith(b"%PDF")


def test_creates_missing_output_parent_dirs(tmp_path: Path):
    source = tmp_path / "cv.md"
    source.write_text("# Hi\n", encoding="utf-8")
    output = tmp_path / "nested" / "dir" / "cv.pdf"
    generate_pdf(source, output)
    assert output.is_file()
    assert output.read_bytes().startswith(b"%PDF")


def test_overwrites_existing_output(tmp_path: Path):
    source = tmp_path / "cv.md"
    source.write_text("# First\n", encoding="utf-8")
    output = tmp_path / "cv.pdf"
    generate_pdf(source, output)
    first = output.read_bytes()
    source.write_text("# Second\n\n" + ("word " * 400) + "\n", encoding="utf-8")
    generate_pdf(source, output)
    second = output.read_bytes()
    assert second.startswith(b"%PDF")
    assert second != first


def test_missing_input_raises_file_not_found(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        generate_pdf(tmp_path / "missing.md", tmp_path / "out.pdf")


def test_input_directory_raises_is_a_directory(tmp_path: Path):
    with pytest.raises(IsADirectoryError):
        generate_pdf(tmp_path, tmp_path / "out.pdf")


def test_output_directory_raises_is_a_directory(tmp_path: Path):
    source = tmp_path / "cv.md"
    source.write_text("# Hi\n", encoding="utf-8")
    with pytest.raises(IsADirectoryError):
        generate_pdf(source, tmp_path)


def test_non_utf8_input_raises_unicode_decode_error(tmp_path: Path):
    source = tmp_path / "bad.md"
    source.write_bytes(b"\xff\xfe")
    with pytest.raises(UnicodeDecodeError):
        generate_pdf(source, tmp_path / "out.pdf")


def test_render_failure_does_not_write_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    source = tmp_path / "cv.md"
    source.write_text("# Hi\n", encoding="utf-8")
    output = tmp_path / "out.pdf"

    def boom(html: str, *, base_url: str | Path) -> bytes:
        raise RuntimeError("cairo missing")

    monkeypatch.setattr("cv_generator.generate_pdf.html_to_pdf", boom)
    with pytest.raises(CvGeneratorError, match="cairo missing"):
        generate_pdf(source, output)
    assert not output.exists()


def test_replace_failure_deletes_temp_and_keeps_old_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    import os

    source = tmp_path / "cv.md"
    source.write_text("# Hi\n", encoding="utf-8")
    output = tmp_path / "out.pdf"
    generate_pdf(source, output)
    original = output.read_bytes()

    def fail_replace(src: str | os.PathLike[str], dst: str | os.PathLike[str]) -> None:
        raise OSError("boom")

    monkeypatch.setattr("cv_generator.generate_pdf.os.replace", fail_replace)
    with pytest.raises(OSError, match="boom"):
        generate_pdf(source, output)
    assert output.read_bytes() == original
    leftovers = list(tmp_path.glob(".cv-generator-*.pdf"))
    assert leftovers == []


_FRONTMATTER_MD = (
    "---\n"
    "name: Ada Lovelace\n"
    "title: Software Engineer\n"
    "email: ada@example.com\n"
    "links:\n"
    "  github: https://github.com/ada\n"
    "---\n"
    "# Summary\n\n"
    "Profile line.\n"
)


def test_generate_pdf_with_frontmatter_writes_valid_pdf(tmp_path: Path):
    source = tmp_path / "cv.md"
    source.write_text(_FRONTMATTER_MD, encoding="utf-8")
    output = tmp_path / "cv.pdf"
    generate_pdf(source, output)
    assert output.read_bytes().startswith(b"%PDF")
    assert output.stat().st_size > 0


def test_generate_pdf_passes_meta_and_stem_title(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    captured: dict = {}
    real_html_document = html_document

    def fake_html_document(content: str, title: str, meta: dict | None = None) -> str:
        captured["content"] = content
        captured["title"] = title
        captured["meta"] = meta
        captured["html"] = real_html_document(content, title, meta=meta)
        return captured["html"]

    monkeypatch.setattr("cv_generator.generate_pdf.html_document", fake_html_document)
    source = tmp_path / "cv.md"
    source.write_text(_FRONTMATTER_MD, encoding="utf-8")
    generate_pdf(source, tmp_path / "cv.pdf")
    assert captured["title"] == "cv"
    assert captured["meta"]["name"] == "Ada Lovelace"
    assert captured["meta"]["title"] == "Software Engineer"
    assert "---" not in captured["content"]
    assert "<h1>Ada Lovelace</h1>" in captured["html"]
    assert "<title>cv</title>" in captured["html"]


def test_generate_pdf_without_frontmatter_still_writes_pdf(tmp_path: Path):
    source = tmp_path / "plain.md"
    source.write_text("# Summary\n\nHello\n", encoding="utf-8")
    output = tmp_path / "plain.pdf"
    generate_pdf(source, output)
    assert output.read_bytes().startswith(b"%PDF")


def test_generate_pdf_unclosed_frontmatter_raises_and_writes_no_output(
    tmp_path: Path,
):
    source = tmp_path / "cv.md"
    source.write_text("---\nname: Ada\n# Summary\n", encoding="utf-8")
    output = tmp_path / "out.pdf"
    with pytest.raises(CvGeneratorError, match="Unclosed YAML frontmatter"):
        generate_pdf(source, output)
    assert not output.exists()


def test_generate_pdf_invalid_yaml_raises_and_keeps_old_output(
    tmp_path: Path,
):
    source = tmp_path / "cv.md"
    source.write_text("# First\n", encoding="utf-8")
    output = tmp_path / "out.pdf"
    generate_pdf(source, output)
    original = output.read_bytes()
    source.write_text("---\nname: [unclosed\n---\n# Summary\n", encoding="utf-8")
    with pytest.raises(CvGeneratorError, match="Invalid YAML frontmatter"):
        generate_pdf(source, output)
    assert output.read_bytes() == original


@pytest.mark.skipif(shutil.which("pdftotext") is None, reason="pdftotext not installed")
def test_pdf_text_is_linear_top_to_bottom(tmp_path: Path):
    source = tmp_path / "cv.md"
    source.write_text(
        "# Summary\n\nProfile line.\n\n# Experience\n\n## Flexiana\n\n- Built a service\n",
        encoding="utf-8",
    )
    output = tmp_path / "cv.pdf"
    generate_pdf(source, output)
    assert output.read_bytes().startswith(b"%PDF")
    text = subprocess.check_output(
        ["pdftotext", "-layout", str(output), "-"],
        text=True,
    )
    i_summary = text.index("Summary")
    i_exp = text.index("Experience")
    i_flex = text.index("Flexiana")
    i_built = text.index("Built a service")
    assert i_summary < i_exp < i_flex < i_built
