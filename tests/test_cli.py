import subprocess
import sys
from pathlib import Path

from cv_generator.cli import execute
from cv_generator.generate_pdf import CvGeneratorError


def test_success_returns_0_and_writes_pdf_silently(tmp_path: Path, capsys):
    source = tmp_path / "cv.md"
    source.write_text("# Hello\n", encoding="utf-8")
    output = tmp_path / "cv.pdf"
    code = execute(["generate-pdf", "-i", str(source), "-o", str(output)])
    captured = capsys.readouterr()
    assert code == 0
    assert captured.out == ""
    assert output.read_bytes().startswith(b"%PDF")


def test_long_flags_work(tmp_path: Path):
    source = tmp_path / "cv.md"
    source.write_text("# Hello\n", encoding="utf-8")
    output = tmp_path / "cv.pdf"
    code = execute(["generate-pdf", "--input", str(source), "--output", str(output)])
    assert code == 0
    assert output.is_file()


def test_missing_flags_returns_2():
    assert execute(["generate-pdf"]) == 2


def test_missing_subcommand_returns_2():
    assert execute([]) == 2


def test_unknown_command_returns_2():
    assert execute(["not-a-command"]) == 2


def test_help_returns_0(capsys):
    assert execute(["--help"]) == 0
    assert "generate-pdf" in capsys.readouterr().out


def test_generate_pdf_help_returns_0(capsys):
    assert execute(["generate-pdf", "--help"]) == 0
    out = capsys.readouterr().out
    assert "--input" in out
    assert "--output" in out


def test_missing_input_file_returns_1(tmp_path: Path, capsys):
    missing = tmp_path / "nope.md"
    code = execute(["generate-pdf", "-i", str(missing), "-o", str(tmp_path / "out.pdf")])
    err = capsys.readouterr().err
    assert code == 1
    assert str(missing) in err


def test_output_directory_returns_1(tmp_path: Path, capsys):
    source = tmp_path / "cv.md"
    source.write_text("# Hi\n", encoding="utf-8")
    code = execute(["generate-pdf", "-i", str(source), "-o", str(tmp_path)])
    err = capsys.readouterr().err
    assert code == 1
    assert err.strip() != ""


def test_non_utf8_input_returns_1(tmp_path: Path, capsys):
    source = tmp_path / "bad.md"
    source.write_bytes(b"\xff\xfe")
    code = execute(["generate-pdf", "-i", str(source), "-o", str(tmp_path / "out.pdf")])
    err = capsys.readouterr().err
    assert code == 1
    assert "UTF-8" in err


def test_cv_generator_error_returns_1(tmp_path: Path, capsys, monkeypatch):
    source = tmp_path / "cv.md"
    source.write_text("# Hi\n", encoding="utf-8")

    def boom(input_path: Path, output_path: Path) -> None:
        raise CvGeneratorError("cairo missing")

    monkeypatch.setattr("cv_generator.cli.generate_pdf", boom)
    code = execute(["generate-pdf", "-i", str(source), "-o", str(tmp_path / "out.pdf")])
    err = capsys.readouterr().err
    assert code == 1
    assert "cairo missing" in err


def test_os_error_returns_1(tmp_path: Path, capsys, monkeypatch):
    source = tmp_path / "cv.md"
    source.write_text("# Hi\n", encoding="utf-8")

    def boom(input_path: Path, output_path: Path) -> None:
        raise OSError("disk full")

    monkeypatch.setattr("cv_generator.cli.generate_pdf", boom)
    code = execute(["generate-pdf", "-i", str(source), "-o", str(tmp_path / "out.pdf")])
    err = capsys.readouterr().err
    assert code == 1
    assert "disk full" in err


def test_os_error_from_replace_returns_1(tmp_path: Path, capsys, monkeypatch):
    # Mirrors generate_pdf's real OSError path: os.replace failure propagates as OSError
    # but CLI must map it to exit 1, not traceback.
    source = tmp_path / "cv.md"
    source.write_text("# Hi\n", encoding="utf-8")

    def boom_replace(input_path: Path, output_path: Path) -> None:
        raise OSError("boom")

    monkeypatch.setattr("cv_generator.cli.generate_pdf", boom_replace)
    code = execute(["generate-pdf", "-i", str(source), "-o", str(tmp_path / "out.pdf")])
    err = capsys.readouterr().err
    assert code == 1
    assert "boom" in err


def test_permission_error_returns_1(tmp_path: Path, capsys, monkeypatch):
    # PermissionError is a subclass of OSError; ensure it is also mapped.
    source = tmp_path / "cv.md"
    source.write_text("# Hi\n", encoding="utf-8")

    def boom_perm(input_path: Path, output_path: Path) -> None:
        raise PermissionError("permission denied")

    monkeypatch.setattr("cv_generator.cli.generate_pdf", boom_perm)
    code = execute(["generate-pdf", "-i", str(source), "-o", str(tmp_path / "out.pdf")])
    err = capsys.readouterr().err
    assert code == 1
    assert "permission denied" in err


def test_importing_cli_does_not_import_weasyprint():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import cv_generator.cli, sys; "
            "raise SystemExit(0 if 'weasyprint' not in sys.modules else 1)",
        ],
        check=False,
    )
    assert result.returncode == 0


def test_importing_cli_does_not_import_yaml():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import cv_generator.cli, sys; "
            "raise SystemExit(0 if 'yaml' not in sys.modules else 1)",
        ],
        check=False,
    )
    assert result.returncode == 0
