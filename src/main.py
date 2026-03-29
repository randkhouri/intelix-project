"""
Intelix static analysis — CLI entry point.

Flow:
1. Parse arguments (--files-dir, --output-dir, --max-per-type, --log-dir, --log-file).
2. Configure the root logger: same messages go to stdout and to a UTF-8 log file under logs/.
3. Validate required env vars via config.validate_required_config().
4. Scan --files-dir (non-recursive): collect .exe / .doc / .docx / .pdf up to --max-per-type
   per category; log ERROR for any other regular file in that folder (skipped).
5. For each collected file: IntelixClient.analyze_file() then ReportManager.save() to .txt.

See README.md for folder layout and full option list.
"""

import argparse
import logging
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

from client import IntelixClient
from config import validate_required_config
from reporter import ReportManager


def configure_logging(log_file_path: Path) -> None:
    """
    Attach two handlers to the root logger: StreamHandler (stdout) and FileHandler (UTF-8).

    Clears previous root handlers so a second run in the same process does not duplicate lines.
    """
    log_file_path.parent.mkdir(parents=True, exist_ok=True)
    log_format = "%(asctime)s [%(levelname)s] %(message)s"
    formatter = logging.Formatter(log_format)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    for existing in root.handlers[:]:
        root.removeHandler(existing)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    root.addHandler(stream_handler)

    file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    # First line in the file confirms where logs are written.
    logging.info("Log file: %s", log_file_path.resolve())


def parse_args() -> argparse.Namespace:
    """Define and parse all command-line flags (see README.md)."""
    parser = argparse.ArgumentParser(
        description=(
            "Submit all .exe, .doc/.docx, and .pdf files from a directory "
            "to SophosLabs Intelix static analysis (per-type limit applies)."
        )
    )
    parser.add_argument(
        "--files-dir",
        default="files",
        help="Directory containing input files (default: files)",
    )
    parser.add_argument(
        "--output-dir",
        default="reports",
        help="Directory for JSON reports saved as .txt (default: reports)",
    )
    parser.add_argument(
        "--max-per-type",
        type=int,
        default=20,
        help="Max files to analyze per category: exe, word, pdf (default: 20)",
    )
    parser.add_argument(
        "--log-dir",
        default="logs",
        help="Directory for log files (default: logs)",
    )
    parser.add_argument(
        "--log-file",
        default=None,
        help=(
            "Log filename inside --log-dir (default: intelix_YYYYMMDD_HHMMSS.log)"
        ),
    )
    return parser.parse_args()


def _classify_file(path: Path) -> str | None:
    """
    Map a file path to bucket exe | word | pdf, or None if unsupported.

    Returns None if the path is not a file or the extension is not allowed.
    """
    if not path.is_file():
        return None
    ext = path.suffix.lower()
    if ext == ".exe":
        return "exe"
    if ext in (".doc", ".docx"):
        return "word"
    if ext == ".pdf":
        return "pdf"
    return None


def collect_files_from_directory(
    directory: Path,
    max_per_type: int,
) -> Tuple[List[Tuple[str, Path]], Dict[str, int]]:
    """
    List files in `directory` (top level only; no subfolders).

    - Regular files with allowed extensions go into exe / word / pdf buckets.
    - Any other regular file: log ERROR and skip (not sent to Intelix).
    - Each bucket is sorted by name, then capped at max_per_type (WARNING if truncated).

    Returns:
        (list of (type_label, path) in order exe, then word, then pdf),
        dict of counts per type after capping.
    """
    if not directory.exists():
        logging.error("Directory does not exist: %s", directory)
        return [], {}

    if not directory.is_dir():
        logging.error("Not a directory: %s", directory)
        return [], {}

    buckets: Dict[str, List[Path]] = {"exe": [], "word": [], "pdf": []}

    for entry in directory.iterdir():
        if not entry.is_file():
            continue
        label = _classify_file(entry)
        if label is not None:
            buckets[label].append(entry)
        else:
            logging.error(
                "Unsupported file (skipped): %s — allowed extensions: .exe, .doc, .docx, .pdf",
                entry.name,
            )

    for label in buckets:
        buckets[label].sort(key=lambda p: p.name.lower())

    files: List[Tuple[str, Path]] = []
    counts: Dict[str, int] = {}

    for label in ("exe", "word", "pdf"):
        all_for_type = buckets[label]
        if len(all_for_type) > max_per_type:
            logging.warning(
                "Found %d %s file(s); analyzing first %d (--max-per-type)",
                len(all_for_type),
                label,
                max_per_type,
            )
        selected = all_for_type[:max_per_type]
        counts[label] = len(selected)
        for path in selected:
            files.append((label, path))

    logging.info(
        "Discovered in %s: %d exe, %d word, %d pdf (max %d per type)",
        directory,
        counts.get("exe", 0),
        counts.get("word", 0),
        counts.get("pdf", 0),
        max_per_type,
    )

    return files, counts


def main() -> int:
    """
    Run one full scan + analysis pass.

    Exit codes:
        0 — every queued supported file got a saved report
        1 — invalid args/config/path, or zero supported files after scan
        2 — one or more analyses or saves failed
    """
    args = parse_args()

    # Logging must be configured before validate_required_config() so failures are captured.
    log_dir = Path(args.log_dir)
    log_name = args.log_file or datetime.now().strftime("intelix_%Y%m%d_%H%M%S.log")
    configure_logging(log_dir / log_name)

    validate_required_config()

    files_dir = Path(args.files_dir)
    max_per_type = max(0, args.max_per_type)

    if max_per_type == 0:
        logging.error("--max-per-type must be at least 1")
        return 1

    files, _counts = collect_files_from_directory(files_dir, max_per_type)

    if not files:
        logging.error(
            "No .exe, .doc/.docx, or .pdf files found under %s",
            files_dir.resolve(),
        )
        return 1

    client = IntelixClient()
    reporter = ReportManager(output_dir=args.output_dir)
    success_count = 0
    total = len(files)

    # Same stem + type twice in one folder (e.g. copies) → pdf_foo.txt, pdf_foo_2.txt
    stem_serial: defaultdict[str, int] = defaultdict(int)

    for file_type, file_path in files:
        logging.info("Starting analysis (%s): %s", file_type, file_path)
        result = client.analyze_file(file_path)

        if result is None:
            logging.error("Analysis failed (%s): %s", file_type, file_path.name)
            continue

        base_name = f"{file_type}_{file_path.stem}"
        stem_serial[base_name] += 1
        serial = stem_serial[base_name]
        output_name = base_name if serial == 1 else f"{base_name}_{serial}"

        report_path = reporter.save(output_name, result)
        if report_path is None:
            logging.error("Report save failed (%s): %s", file_type, file_path.name)
            continue

        success_count += 1
        logging.info("Completed (%s): %s", file_type, report_path)

    logging.info("Finished. %d/%d report(s) saved.", success_count, total)
    return 0 if success_count == total else 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # If logging was never configured (e.g. crash in parse_args), Python may use lastResort.
        logging.exception("Fatal error")
        sys.exit(99)
