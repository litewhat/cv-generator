import argparse
import sys
from pathlib import Path

from cv_generator.generate_pdf import CvGeneratorError, generate_pdf


def create_parser():
    parser = argparse.ArgumentParser(prog="cv-generator")
    subparsers = parser.add_subparsers(dest="command", required=True)
    pdf_parser = subparsers.add_parser(
        "generate-pdf",
        help="Convert a Markdown file to a PDF",
    )
    pdf_parser.add_argument(
        "-i",
        "--input",
        required=True,
        type=Path,
        help="Markdown file to convert",
    )
    pdf_parser.add_argument(
        "-o",
        "--output",
        required=True,
        type=Path,
        help="PDF file to write",
    )
    return parser


def execute(argv: list[str]) -> int:
    parser = create_parser()

    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 0

    try:
        generate_pdf(args.input, args.output)
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 1
    except IsADirectoryError as exc:
        print(exc, file=sys.stderr)
        return 1
    except UnicodeDecodeError:
        print("Input is not valid UTF-8.", file=sys.stderr)
        return 1
    except CvGeneratorError as exc:
        print(exc, file=sys.stderr)
        return 1
    except OSError as exc:
        print(exc, file=sys.stderr)
        return 1
    return 0


def main() -> int:
    return execute(sys.argv[1:])
