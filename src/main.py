"""
Intelix batch static analysis CLI.

Scans a folder for supported file types, submits each to Intelix static analysis,
writes JSON reports as `.txt`, and logs to stdout and a file under `logs/`.
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


# Log to stdout and a UTF-8 file; reset root handlers to avoid duplicate lines.
def configure_logging(log_file_path: Path) -> None:
    log_file_path.parent.mkdir(parents=True, exist_ok=True)
    fmt = "%(asctime)s [%(levelname)s] %(message)s"
    formatter = logging.Formatter(fmt)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    for h in root.handlers[:]:
        root.removeHandler(h)

    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(formatter)
    root.addHandler(sh)

    fh = logging.FileHandler(log_file_path, encoding="utf-8")
    fh.setFormatter(formatter)
    root.addHandler(fh)

    logging.info("Log file: %s", log_file_path.resolve())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Submit .exe, .doc/.docx, and .pdf from a directory to Intelix "
            "(cap per file type)."
        )
    )
    parser.add_argument(
        "--files-dir",
        default="files",
        help="Input folder (default: files)",
    )
    parser.add_argument(
        "--output-dir",
        default="reports",
        help="Where to write report .txt files (default: reports)",
    )
    parser.add_argument(
        "--max-per-type",
        type=int,
        default=20,
        help="Max files per category: exe, word, pdf (default: 20)",
    )
    parser.add_argument(
        "--log-dir",
        default="logs",
        help="Log directory (default: logs)",
    )
    parser.add_argument(
        "--log-file",
        default=None,
        help="Log filename inside log-dir (default: intelix_YYYYMMDD_HHMMSS.log)",
    )
    return parser.parse_args()


# exe | word | pdf, or None.
def _classify_file(path: Path) -> str | None:
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


# Top-level files only; bucket, cap per type, ERROR unsupported extensions.
def collect_files_from_directory(
    directory: Path,
    max_per_type: int,
) -> Tuple[List[Tuple[str, Path]], Dict[str, int]]:
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
                "Unsupported file (skipped): %s — allowed: .exe, .doc, .docx, .pdf",
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


# Exit 0 = all ok, 1 = setup/empty, 2 = partial failure.
def main() -> int:
    args = parse_args()

    # Configure logging before validate so credential errors hit the log file too.
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

    # Duplicate stem + type → pdf_foo_2.txt.
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
        logging.exception("Fatal error")
        sys.exit(99)
