"""
Command-line entry point for the Intelix static analysis assignment.

Responsibilities:
- Parse CLI arguments for the three input files (exe/word/pdf).
- Validate required configuration and input file existence/extensions.
- Submit each file to Intelix and save the returned JSON as a `.txt` file.
- Log all activity and errors to standard output.
"""

import logging
import sys
import argparse
from pathlib import Path

from client import IntelixClient
from reporter import ReportManager
from config import validate_required_config


logging.basicConfig(
    # Configure global logging format and direct logs to stdout.
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)


def parse_args() -> argparse.Namespace:
    """
    Parse required CLI arguments for the assignment run.

    The script requires exactly three file types:
    - Windows executable
    - Word document
    - PDF document
    """
    # Parse command line arguments for the three required files.
    parser = argparse.ArgumentParser(
        description="Submit .exe, .doc/.docx, and .pdf files to SophosLabs Intelix static analysis."
    )
    """
    Input contract:
    - `--exe`: one Windows executable
    - `--word`: one Word document
    - `--pdf`: one PDF
    - `--output-dir`: where report TXT files are written
    """
    parser.add_argument("--exe", required=True, help="Path to Windows executable file")
    parser.add_argument("--word", required=True, help="Path to Word document (.doc or .docx)")
    parser.add_argument("--pdf", required=True, help="Path to PDF document")
    parser.add_argument(
        "--output-dir",
        default="reports",
        help="Directory to save JSON reports as .txt files (default: reports)",
    )
    return parser.parse_args()


def validate_input_file(file_path: Path, allowed_suffixes: tuple[str, ...]) -> bool:
    """
    Validate a single input file path against existence and extension rules.

    Returns True when valid, False otherwise.
    """
    # Validate that a file exists and has one of the allowed extensions.
    if not file_path.exists() or not file_path.is_file():
        logging.error("Input file does not exist: %s", file_path)
        return False
    if file_path.suffix.lower() not in allowed_suffixes:
        logging.error(
            "Invalid extension for %s. Allowed: %s",
            file_path,
            ", ".join(allowed_suffixes),
        )
        return False
    return True


def main() -> int:
    """
    Program entry workflow for analysis and report generation.

    Returns process exit codes:
    - 0: all reports generated
    - 1: invalid input/config detected before submission
    - 2: partial or total processing failure
    """
    # Run the analysis for the three input files and persist the reports.
    args = parse_args()

    # Critical early guard to avoid confusing downstream auth failures.
    validate_required_config()

    # Process all three required file categories in a fixed order.
    # Each tuple: (label, path, allowed_extensions).
    files = [
        ("exe", Path(args.exe), (".exe",)),
        ("word", Path(args.word), (".doc", ".docx")),
        ("pdf", Path(args.pdf), (".pdf",)),
    ]

    # Validate local input first, then start network calls.
    if not all(validate_input_file(path, suffixes) for _, path, suffixes in files):
        return 1

    """
    Main workflow:
    1) submit file for analysis
    2) receive report JSON (direct or polled)
    3) save JSON into `.txt`
    Continue processing remaining files even when one fails.
    """
    client = IntelixClient()
    reporter = ReportManager(output_dir=args.output_dir)
    success_count = 0

    # Process each required file category independently.
    for label, file_path, _ in files:
        logging.info("Starting analysis (%s): %s", label, file_path)
        result = client.analyze_file(file_path)

        if result is None:
            logging.error("Analysis failed (%s): %s", label, file_path.name)
            continue

        output_name = f"{label}_{file_path.stem}"
        report_file = reporter.save(output_name, result)
        if report_file is None:
            logging.error("Report save failed (%s): %s", label, file_path.name)
            continue
        success_count += 1
        logging.info("Completed (%s): %s", label, report_file)

    # Return success only when all three reports are produced.
    logging.info("Finished. %d/%d report(s) saved.", success_count, len(files))
    return 0 if success_count == len(files) else 2


if __name__ == "__main__":
    """
    Execute CLI entrypoint and convert exceptions to a consistent exit code.
    """
    try:
        sys.exit(main())
    except Exception:
        # Fallback guard for unexpected runtime exceptions.
        logging.exception("Fatal error")
        sys.exit(99)