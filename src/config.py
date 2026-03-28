"""
Configuration for the Intelix client (settings + credentials)

This module reads credentials and tuning parameters from environment variables
(loaded from `.env`). 
"""

import os
from dotenv import load_dotenv

# Load variables from `.env` into process environment.
load_dotenv()

"""
Core connection/auth settings for Intelix.

These values come from `.env` so credentials/endpoints can be changed
without modifying source code.
"""
# Core connection/auth settings for Intelix.
# These values come from `.env` because credentials and endpoints can change anytime.
INTELIX_CLIENT_ID = os.getenv("INTELIX_CLIENT_ID", "").strip()
INTELIX_CLIENT_SECRET = os.getenv("INTELIX_CLIENT_SECRET", "").strip()
INTELIX_BASE_URL = os.getenv("INTELIX_BASE_URL", "https://api.labs.sophos.com").rstrip("/")
INTELIX_REGION = os.getenv("INTELIX_REGION", "us").strip().lower()
INTELIX_STATIC_ANALYSIS_PATH = os.getenv(
    "INTELIX_STATIC_ANALYSIS_PATH", "/analysis/file/static/v1"
)

"""
Runtime tuning parameters.

These values control timeout and async polling behavior for network calls.
"""
# Runtime tuning parameters.
# These control request timeout and async polling behavior for analysis jobs.
INTELIX_TIMEOUT_SECONDS = int(os.getenv("INTELIX_TIMEOUT_SECONDS", "60"))
INTELIX_MAX_POLL_ATTEMPTS = int(os.getenv("INTELIX_MAX_POLL_ATTEMPTS", "120"))
INTELIX_POLL_INTERVAL_SECONDS = int(os.getenv("INTELIX_POLL_INTERVAL_SECONDS", "5"))


def validate_required_config() -> None:
    """
    Validate required authentication values before API calls.

    Fail fast if credentials are missing so the user gets a clear error
    instead of a confusing downstream HTTP failure.
    """
    # Fail fast if required credentials are missing.
    if not INTELIX_CLIENT_ID or not INTELIX_CLIENT_SECRET:
        raise ValueError(
            "Missing Intelix credentials. Set INTELIX_CLIENT_ID and INTELIX_CLIENT_SECRET in .env."
        )