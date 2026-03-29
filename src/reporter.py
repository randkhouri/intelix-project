"""
Report saving utilities.

Intelix returns analysis results as JSON. For this assignment we persist each
report into a `.txt` file containing JSON (pretty-printed).
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional


class ReportManager:
    """
    Persist Intelix report payloads to disk.

    Reports are saved as `.txt` files (containing JSON text) to satisfy
    assignment output requirements.
    """
    def __init__(self, output_dir="reports"):
        """
        Initialize output directory path and ensure it exists.
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def save(self, file_name: str, data: Dict[str, Any]) -> Optional[Path]:
        """
        Save one report payload to `<output_dir>/<file_name>.txt`.

        Returns the written path on success; returns None if writing fails.
        """
        output_file = self.output_dir / f"{file_name}.txt"

        try:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)

            logging.info("Saved report: %s", output_file)
            return output_file

        except Exception:
            logging.exception("Failed to save report: %s", file_name)
            return None