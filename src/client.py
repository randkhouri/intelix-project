"""
Intelix static analysis client.

This module is responsible for:
1) Submitting a file to the Intelix static analysis endpoint.
2) Handling both synchronous responses (HTTP 200) and async jobs (HTTP 202).
3) Polling the job report endpoint until the final report JSON is available.
4) Returning the decoded JSON payload to the caller.
"""

import logging
import time
import requests
from pathlib import Path
from typing import Any, Dict, Optional

from auth import AuthClient
from config import (
    INTELIX_BASE_URL,
    INTELIX_MAX_POLL_ATTEMPTS,
    INTELIX_POLL_INTERVAL_SECONDS,
    INTELIX_REGION,
    INTELIX_STATIC_ANALYSIS_PATH,
    INTELIX_TIMEOUT_SECONDS,
)


class IntelixClient:
    """
    Coordinate Intelix static analysis API requests.

    Responsibilities:
    - Build final regional endpoint URL.
    - Submit files for static analysis.
    - Handle immediate and asynchronous responses.
    - Poll report endpoint until final result is ready.
    """
    def __init__(self):
        """
        Prepare reusable API state:
        - auth helper
        - region-adjusted base URL
        - final static analysis endpoint
        """
        self.auth = AuthClient()
        self.base_url = INTELIX_BASE_URL
        self.analysis_base_url = self._build_regional_url(self.base_url, INTELIX_REGION)
        self.static_analysis_url = f"{self.analysis_base_url}{INTELIX_STATIC_ANALYSIS_PATH}"

    @staticmethod
    def _build_regional_url(base_url: str, region: str) -> str:
        """
        Convert a generic Intelix host into a region-specific host.

        Example:
        - input:  https://api.labs.sophos.com, region=us
        - output: https://us.api.labs.sophos.com
        """
        if "://" not in base_url:
            return f"https://{region}.{base_url}"
        scheme, host = base_url.split("://", 1)
        if host.startswith(f"{region}."):
            return base_url
        return f"{scheme}://{region}.{host}"

    def analyze_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Submit one file to Intelix static analysis.

        Returns final report JSON as dict when successful, otherwise None.
        """
        token = self.auth.get_access_token()

        # Intelix uses the raw access token in Authorization (not "Bearer …").
        headers = {
            "Authorization": token
        }

        logging.info("Submitting file: %s", file_path.name)

        try:
            with open(file_path, "rb") as f:
                files = {"file": (file_path.name, f)}
                response = requests.post(
                    self.static_analysis_url,
                    headers=headers,
                    files=files,
                    timeout=INTELIX_TIMEOUT_SECONDS,
                )
            return self._handle_analysis_response(file_path.name, response, headers)

        except Exception:
            logging.exception("Failed processing file: %s", file_path.name)
            return None

    def _handle_analysis_response(
        self,
        file_name: str,
        response: requests.Response,
        headers: Dict[str, str],
    ) -> Optional[Dict[str, Any]]:
        """
        Interpret submit response and return final report if available.

        - 200: report is already available
        - 202: job accepted; poll until report ready
        - other: treat as failure
        """
        if response.status_code == 200:
            logging.info("Received report immediately for %s", file_name)
            return response.json()

        if response.status_code == 202:
            body = response.json()
            job_id = body.get("jobId")
            if not job_id:
                logging.error("Intelix returned 202 without jobId for %s", file_name)
                return None
            logging.info("Intelix accepted %s (jobId=%s). Polling...", file_name, job_id)
            return self._poll_report(job_id, headers)

        logging.error(
            "Intelix API error for %s: %s - %s",
            file_name,
            response.status_code,
            response.text,
        )
        return None

    def _poll_report(self, job_id: str, headers: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """
        Poll Intelix report endpoint for an asynchronous job.

        The polling loop stops when:
        - report is ready (HTTP 200),
        - an unrecoverable status is returned, or
        - max attempts are exhausted.

        Polling contract per GET: 200 = done, 202 = wait and retry, anything else = fail.
        """
        report_url = f"{self.static_analysis_url}/reports/{job_id}"

        for attempt in range(1, INTELIX_MAX_POLL_ATTEMPTS + 1):
            response = requests.get(report_url, headers=headers, timeout=INTELIX_TIMEOUT_SECONDS)

            if response.status_code == 200:
                logging.info("Report ready for jobId=%s after %d poll(s)", job_id, attempt)
                return response.json()

            if response.status_code != 202:
                logging.error(
                    "Polling failed for jobId=%s: %s - %s",
                    job_id,
                    response.status_code,
                    response.text,
                )
                return None

            logging.info(
                "Report not ready for jobId=%s (attempt %d/%d)",
                job_id,
                attempt,
                INTELIX_MAX_POLL_ATTEMPTS,
            )
            time.sleep(INTELIX_POLL_INTERVAL_SECONDS)

        logging.error("Timed out waiting for report, jobId=%s", job_id)
        return None