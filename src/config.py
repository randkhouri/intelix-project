"""
Intelix client configuration (credentials and runtime tuning).

Loads variables from the process environment. A project-root `.env` file is
applied via `load_dotenv()` so local secrets are not hard-coded.
"""

import os

from dotenv import load_dotenv

load_dotenv()

# --- Connection & auth (from .env) ---
INTELIX_CLIENT_ID = os.getenv("INTELIX_CLIENT_ID", "").strip()
INTELIX_CLIENT_SECRET = os.getenv("INTELIX_CLIENT_SECRET", "").strip()
INTELIX_BASE_URL = os.getenv("INTELIX_BASE_URL", "https://api.labs.sophos.com").rstrip("/")
INTELIX_REGION = os.getenv("INTELIX_REGION", "us").strip().lower()
INTELIX_STATIC_ANALYSIS_PATH = os.getenv(
    "INTELIX_STATIC_ANALYSIS_PATH", "/analysis/file/static/v1"
)

# --- HTTP timeouts and async job polling (from .env) ---
INTELIX_TIMEOUT_SECONDS = int(os.getenv("INTELIX_TIMEOUT_SECONDS", "60"))
INTELIX_MAX_POLL_ATTEMPTS = int(os.getenv("INTELIX_MAX_POLL_ATTEMPTS", "120"))
INTELIX_POLL_INTERVAL_SECONDS = int(os.getenv("INTELIX_POLL_INTERVAL_SECONDS", "5"))


def validate_required_config() -> None:
    """
    Ensure OAuth credentials exist before any Intelix API call.

    Raises ValueError with a clear message if `INTELIX_CLIENT_ID` or
    `INTELIX_CLIENT_SECRET` is missing.
    """
    if not INTELIX_CLIENT_ID or not INTELIX_CLIENT_SECRET:
        raise ValueError(
            "Missing Intelix credentials. Set INTELIX_CLIENT_ID and INTELIX_CLIENT_SECRET in .env."
        )
