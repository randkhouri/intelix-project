"""
Intelix report persistence.

Writes each API response (JSON) to a `.txt` file with UTF-8 encoding and pretty
printing. Failed writes are logged; callers treat None as non-fatal.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional


class ReportManager:
    """
    Save analysis reports to disk.

    Responsibilities:
    - Ensure the output directory exists.
    - Write one `.txt` file per successful analysis.
    """

    def __init__(self, output_dir="reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # Pretty JSON to <file_name>.txt; None on IO error.
    def save(self, file_name: str, data: Dict[str, Any]) -> Optional[Path]:
        output_file = self.output_dir / f"{file_name}.txt"

        try:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)

            logging.info("Saved report: %s", output_file)
            return output_file

        except Exception:
            logging.exception("Failed to save report: %s", file_name)
            return None
