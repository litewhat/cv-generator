from pathlib import Path

from cv_generator.cli import execute
from cv_generator.generate_pdf import CvGeneratorError

_VALID_CV = """\
---
name: Ada Lovelace
title: Software Engineer
email: ada@example.com
phone: "+48 111 222 333"
location: Warsaw, Poland
---

Hello
"""


class TestCliSuccess:
    def test_success_returns_0_and_writes_pdf_silently(self, tmp_path: Path, capsys):
        source = tmp_path / "cv.md"
        source.write_text(_VALID_CV, encoding="utf-8")
        output = tmp_path / "cv.pdf"
        code = execute(["generate-pdf", "-i", str(source), "-o", str(output)])
        captured = capsys.readouterr()
        assert code == 0
        assert captured.out == ""
        assert output.read_bytes().startswith(b"%PDF")

    def test_long_flags_work(self, tmp_path: Path):
        source = tmp_path / "cv.md"
        source.write_text(_VALID_CV, encoding="utf-8")
        output = tmp_path / "cv.pdf"
        code = execute(
            ["generate-pdf", "--input", str(source), "--output", str(output)]
        )
        assert code == 0
        assert output.is_file()


class TestCliArgparse:
    def test_missing_flags_returns_2(self):
        assert execute(["generate-pdf"]) == 2

    def test_missing_subcommand_returns_2(self):
        assert execute([]) == 2

    def test_unknown_command_returns_2(self):
        assert execute(["not-a-command"]) == 2

    def test_help_returns_0(self, capsys):
        assert execute(["--help"]) == 0
        assert "generate-pdf" in capsys.readouterr().out

    def test_generate_pdf_help_returns_0(self, capsys):
        assert execute(["generate-pdf", "--help"]) == 0
        out = capsys.readouterr().out
        assert "--input" in out
        assert "--output" in out


class TestCliFailureExitCodes:
    def test_missing_input_file_returns_1(self, tmp_path: Path, capsys):
        missing = tmp_path / "nope.md"
        code = execute(
            ["generate-pdf", "-i", str(missing), "-o", str(tmp_path / "out.pdf")]
        )
        err = capsys.readouterr().err
        assert code == 1
        assert str(missing) in err

    def test_output_directory_returns_1(self, tmp_path: Path, capsys):
        source = tmp_path / "cv.md"
        source.write_text(_VALID_CV, encoding="utf-8")
        code = execute(["generate-pdf", "-i", str(source), "-o", str(tmp_path)])
        err = capsys.readouterr().err
        assert code == 1
        assert err.strip() != ""

    def test_non_utf8_input_returns_1(self, tmp_path: Path, capsys):
        source = tmp_path / "bad.md"
        source.write_bytes(b"\xff\xfe")
        code = execute(
            ["generate-pdf", "-i", str(source), "-o", str(tmp_path / "out.pdf")]
        )
        err = capsys.readouterr().err
        assert code == 1
        assert "UTF-8" in err

    def test_cv_generator_error_returns_1(self, tmp_path: Path, capsys, monkeypatch):
        source = tmp_path / "cv.md"
        source.write_text(_VALID_CV, encoding="utf-8")

        def boom(input_path: Path, output_path: Path) -> None:
            raise CvGeneratorError("cairo missing")

        monkeypatch.setattr("cv_generator.cli.generate_pdf", boom)
        code = execute(
            ["generate-pdf", "-i", str(source), "-o", str(tmp_path / "out.pdf")]
        )
        err = capsys.readouterr().err
        assert code == 1
        assert "cairo missing" in err

    def test_os_error_returns_1(self, tmp_path: Path, capsys, monkeypatch):
        source = tmp_path / "cv.md"
        source.write_text(_VALID_CV, encoding="utf-8")

        def boom(input_path: Path, output_path: Path) -> None:
            raise OSError("disk full")

        monkeypatch.setattr("cv_generator.cli.generate_pdf", boom)
        code = execute(
            ["generate-pdf", "-i", str(source), "-o", str(tmp_path / "out.pdf")]
        )
        err = capsys.readouterr().err
        assert code == 1
        assert "disk full" in err

    def test_os_error_from_replace_returns_1(self, tmp_path: Path, capsys, monkeypatch):
        source = tmp_path / "cv.md"
        source.write_text(_VALID_CV, encoding="utf-8")

        def boom_replace(input_path: Path, output_path: Path) -> None:
            raise OSError("boom")

        monkeypatch.setattr("cv_generator.cli.generate_pdf", boom_replace)
        code = execute(
            ["generate-pdf", "-i", str(source), "-o", str(tmp_path / "out.pdf")]
        )
        err = capsys.readouterr().err
        assert code == 1
        assert "boom" in err

    def test_permission_error_returns_1(self, tmp_path: Path, capsys, monkeypatch):
        source = tmp_path / "cv.md"
        source.write_text(_VALID_CV, encoding="utf-8")

        def boom_perm(input_path: Path, output_path: Path) -> None:
            raise PermissionError("permission denied")

        monkeypatch.setattr("cv_generator.cli.generate_pdf", boom_perm)
        code = execute(
            ["generate-pdf", "-i", str(source), "-o", str(tmp_path / "out.pdf")]
        )
        err = capsys.readouterr().err
        assert code == 1
        assert "permission denied" in err
