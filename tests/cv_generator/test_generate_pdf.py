import shutil
import subprocess
from pathlib import Path

import pytest

from cv_generator.document import ValidationError
from cv_generator.formatter import to_html
from cv_generator.generate_pdf import CvGeneratorError, generate_pdf

_VALID_HEADER = """\
---
name: Ada Lovelace
title: Software Engineer
email: ada@example.com
phone: "+48 111 222 333"
location: Warsaw, Poland
links:
  github: https://github.com/ada
---
"""


def _write_cv(path: Path, body: str = "Hello\n") -> Path:
    path.write_text(_VALID_HEADER + "\n" + body, encoding="utf-8")
    return path


class TestPdfOutput:
    def test_writes_valid_pdf(self, tmp_path: Path):
        source = _write_cv(tmp_path / "cv.md")
        output = tmp_path / "cv.pdf"
        generate_pdf(source, output)
        data = output.read_bytes()
        assert data.startswith(b"%PDF")
        assert output.stat().st_size > 0

    def test_overwrites_existing_output(self, tmp_path: Path):
        source = _write_cv(tmp_path / "cv.md", "First\n")
        output = tmp_path / "cv.pdf"
        generate_pdf(source, output)
        first = output.read_bytes()
        _write_cv(source, "Second\n\n" + ("word " * 400) + "\n")
        generate_pdf(source, output)
        second = output.read_bytes()
        assert second.startswith(b"%PDF")
        assert second != first

    def test_creates_missing_output_parent_dirs(self, tmp_path: Path):
        source = _write_cv(tmp_path / "cv.md")
        output = tmp_path / "nested" / "dir" / "cv.pdf"
        generate_pdf(source, output)
        assert output.is_file()
        assert output.read_bytes().startswith(b"%PDF")

    def test_calls_to_html_with_parsed_document(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        captured: dict[str, object] = {}
        real = to_html

        def fake(document):
            captured["name"] = document.content.name
            captured["title"] = document.content.title
            captured["html"] = real(document)
            return captured["html"]

        monkeypatch.setattr("cv_generator.generate_pdf.to_html", fake)
        source = _write_cv(tmp_path / "cv.md", "Builds payment systems.\n")
        generate_pdf(source, tmp_path / "cv.pdf")
        assert captured["name"] == "Ada Lovelace"
        assert captured["title"] == "Software Engineer"
        html = captured["html"]
        assert "<title>Ada Lovelace - Software Engineer</title>" in html
        assert "<title>cv</title>" not in html

    def test_html_to_pdf_base_url_is_markdown_parent(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        captured: dict[str, object] = {}

        def fake(html: str, *, base_url: str | Path) -> bytes:
            captured["base_url"] = base_url
            return b"%PDF-fake"

        monkeypatch.setattr("cv_generator.generate_pdf.html_to_pdf", fake)
        source = _write_cv(tmp_path / "cv.md")
        generate_pdf(source, tmp_path / "cv.pdf")
        assert Path(captured["base_url"]) == tmp_path

    @pytest.mark.skipif(shutil.which("pdftotext") is None, reason="pdftotext not installed")
    def test_pdf_text_is_linear_top_to_bottom(self, tmp_path: Path):
        source = _write_cv(
            tmp_path / "cv.md",
            "Builds payment systems.\n\n"
            "## Experience\n\n"
            "### Northwind\n\n"
            "- Led the checkout rewrite\n",
        )
        output = tmp_path / "cv.pdf"
        generate_pdf(source, output)
        assert output.read_bytes().startswith(b"%PDF")
        text = subprocess.check_output(
            ["pdftotext", "-layout", str(output), "-"],
            text=True,
        )
        positions = [
            text.index("Ada Lovelace"),
            text.index("Software Engineer"),
            text.index("Builds payment systems"),
            text.index("Experience"),
            text.index("Northwind"),
            text.index("Led the checkout rewrite"),
        ]
        assert positions == sorted(positions)


class TestInputValidation:
    def test_missing_input_raises_file_not_found(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            generate_pdf(tmp_path / "missing.md", tmp_path / "out.pdf")

    def test_input_directory_raises_is_a_directory(self, tmp_path: Path):
        with pytest.raises(IsADirectoryError):
            generate_pdf(tmp_path, tmp_path / "out.pdf")

    def test_output_directory_raises_is_a_directory(self, tmp_path: Path):
        source = _write_cv(tmp_path / "cv.md")
        with pytest.raises(IsADirectoryError):
            generate_pdf(source, tmp_path)

    def test_non_utf8_input_raises_unicode_decode_error(self, tmp_path: Path):
        source = tmp_path / "bad.md"
        source.write_bytes(b"\xff\xfe")
        with pytest.raises(UnicodeDecodeError):
            generate_pdf(source, tmp_path / "out.pdf")


class TestParseFailures:
    def test_unclosed_yaml_raises_and_writes_no_output(self, tmp_path: Path):
        source = tmp_path / "cv.md"
        source.write_text("---\nname: Ada\n# Summary\n", encoding="utf-8")
        output = tmp_path / "out.pdf"
        with pytest.raises(CvGeneratorError, match="Unclosed YAML frontmatter"):
            generate_pdf(source, output)
        assert not output.exists()

    def test_invalid_yaml_raises_and_keeps_old_output(self, tmp_path: Path):
        source = _write_cv(tmp_path / "cv.md")
        output = tmp_path / "out.pdf"
        generate_pdf(source, output)
        original = output.read_bytes()
        source.write_text("---\nname: [unclosed\n---\n# Summary\n", encoding="utf-8")
        with pytest.raises(CvGeneratorError, match="Invalid YAML frontmatter"):
            generate_pdf(source, output)
        assert output.read_bytes() == original

    def test_empty_file_raises_validation_error_and_writes_no_output(
        self, tmp_path: Path
    ):
        source = tmp_path / "empty.md"
        source.write_text("", encoding="utf-8")
        output = tmp_path / "empty.pdf"
        with pytest.raises(CvGeneratorError) as excinfo:
            generate_pdf(source, output)
        assert isinstance(excinfo.value.__cause__, ValidationError)
        assert not output.exists()

    def test_incomplete_header_raises_validation_error_and_writes_no_output(
        self, tmp_path: Path
    ):
        source = tmp_path / "cv.md"
        source.write_text(
            "---\nname: Ada Lovelace\ntitle: Software Engineer\n"
            "email: ada@example.com\n---\n\nHello\n",
            encoding="utf-8",
        )
        output = tmp_path / "out.pdf"
        with pytest.raises(CvGeneratorError) as excinfo:
            generate_pdf(source, output)
        assert isinstance(excinfo.value.__cause__, ValidationError)
        assert not output.exists()

    def test_heading_only_markdown_writes_no_output(self, tmp_path: Path):
        source = tmp_path / "cv.md"
        source.write_text("# Hello\n", encoding="utf-8")
        output = tmp_path / "out.pdf"
        with pytest.raises(CvGeneratorError) as excinfo:
            generate_pdf(source, output)
        assert isinstance(excinfo.value.__cause__, ValidationError)
        assert not output.exists()

    def test_empty_heading_name_raises_and_writes_no_output(self, tmp_path: Path):
        source = tmp_path / "cv.md"
        source.write_text(_VALID_HEADER + "\n##\n", encoding="utf-8")
        output = tmp_path / "out.pdf"
        with pytest.raises(CvGeneratorError, match="Empty heading name"):
            generate_pdf(source, output)
        assert not output.exists()


class TestAtomicWrite:
    def test_html_to_pdf_failure_does_not_write_output(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        source = _write_cv(tmp_path / "cv.md")
        output = tmp_path / "out.pdf"

        def boom(html: str, *, base_url: str | Path) -> bytes:
            raise RuntimeError("cairo missing")

        monkeypatch.setattr("cv_generator.generate_pdf.html_to_pdf", boom)
        with pytest.raises(CvGeneratorError, match="cairo missing"):
            generate_pdf(source, output)
        assert not output.exists()

    def test_replace_failure_deletes_temp_and_keeps_old_output(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        import os

        source = _write_cv(tmp_path / "cv.md")
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
