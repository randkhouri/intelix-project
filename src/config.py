"""
Intelix configuration and environment loading.

Settings are read from the environment; a project-root `.env` is loaded with
python-dotenv so credentials are not hard-coded. Call validate_required_config()
before any HTTP requests so missing keys fail fast.
"""

import os

from dotenv import load_dotenv

load_dotenv()

# OAuth and API routing (override per environment).
INTELIX_CLIENT_ID = os.getenv("INTELIX_CLIENT_ID", "").strip()
INTELIX_CLIENT_SECRET = os.getenv("INTELIX_CLIENT_SECRET", "").strip()
INTELIX_BASE_URL = os.getenv("INTELIX_BASE_URL", "https://api.labs.sophos.com").rstrip("/")
INTELIX_REGION = os.getenv("INTELIX_REGION", "us").strip().lower()
INTELIX_STATIC_ANALYSIS_PATH = os.getenv(
    "INTELIX_STATIC_ANALYSIS_PATH", "/analysis/file/static/v1"
)

# HTTP timeout and 202 job polling.
INTELIX_TIMEOUT_SECONDS = int(os.getenv("INTELIX_TIMEOUT_SECONDS", "60"))
INTELIX_MAX_POLL_ATTEMPTS = int(os.getenv("INTELIX_MAX_POLL_ATTEMPTS", "120"))
INTELIX_POLL_INTERVAL_SECONDS = int(os.getenv("INTELIX_POLL_INTERVAL_SECONDS", "5"))


def validate_required_config() -> None:
    # Require client id and secret before calling Intelix.
    if not INTELIX_CLIENT_ID or not INTELIX_CLIENT_SECRET:
        raise ValueError(
            "Missing Intelix credentials. Set INTELIX_CLIENT_ID and INTELIX_CLIENT_SECRET in .env."
        )
