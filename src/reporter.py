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
    # Manages writing Intelix reports to disk.
    def __init__(self, output_dir="reports"):
        """
        Initialize output directory path and ensure it exists.
        """
        # Create the output directory once; safe if it already exists
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def save(self, file_name: str, data: Dict[str, Any]) -> Optional[Path]:
        """
        Save one report payload to `<output_dir>/<file_name>.txt`.

        Returns the written path on success; returns None if writing fails.
        """
        # Write the JSON report payload to `<output_dir>/<file_name>.txt`.
        output_file = self.output_dir / f"{file_name}.txt"

        try:
            # Save JSON to `.txt` while keeping the structure readable via indentation.
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)

            # Log output path to stdout for assignment activity evidence.
            logging.info("Saved report: %s", output_file)
            return output_file

        except Exception:
            # Important: one write failure should not crash the entire run.
            logging.exception("Failed to save report: %s", file_name)
            return None