"""
Command-line entry point for the Intelix static analysis client.

Responsibilities:
- Read configuration from the environment (.env).
- Discover .exe, .doc/.docx, and .pdf files under a configurable directory (default: ./files).
- Respect a per-category cap (default: 20 files each for exe, word, pdf).
- Submit each file to SophosLabs Intelix static analysis and save JSON reports as .txt.
- Log activity and errors to standard output.
"""

import argparse
import logging
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

from client import IntelixClient
from config import validate_required_config
from reporter import ReportManager


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)


def parse_args() -> argparse.Namespace:
    """
    Parse CLI arguments.

    By default the program scans ./files. Override with --files-dir.
    """
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
    return parser.parse_args()


def _classify_file(path: Path) -> str | None:
    """Return bucket name exe | word | pdf, or None if not a supported type."""
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
    Scan a single directory (non-recursive) and collect supported files.

    Each category is sorted by path name, then truncated to max_per_type.
    Returns (ordered list of (type_label, path), counts per type after limiting).
    """
    if not directory.exists():
        logging.error("Directory does not exist: %s", directory)
        return [], {}

    if not directory.is_dir():
        logging.error("Not a directory: %s", directory)
        return [], {}

    buckets: Dict[str, List[Path]] = {"exe": [], "word": [], "pdf": []}

    for entry in directory.iterdir():
        label = _classify_file(entry)
        if label is not None:
            buckets[label].append(entry)

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
    Exit codes:
    0 — every discovered file produced a saved report
    1 — bad config, missing directory, or no supported files
    2 — one or more files failed (partial success)
    """
    args = parse_args()
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

    # Avoid overwriting reports when two files share the same stem (e.g. two PDFs named report.pdf in different runs — rare in one folder).
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
