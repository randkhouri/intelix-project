"""
Intelix OAuth authentication client.

Intelix uses OAuth2 client-credentials authentication. We request an access token using
the configured `INTELIX_CLIENT_ID`/`INTELIX_CLIENT_SECRET`, then reuse it for
subsequent API requests.
"""

import base64
import logging
import time
from typing import Optional
import requests
from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import (
    INTELIX_BASE_URL,
    INTELIX_CLIENT_ID,
    INTELIX_CLIENT_SECRET,
    INTELIX_TIMEOUT_SECONDS,
)

class AuthClient:
    """
    Handle OAuth token lifecycle for Intelix.

    Responsibilities:
    - Request OAuth access token using client credentials.
    - Cache token in memory.
    - Refresh token when expired.
    - Apply basic retry behavior for transient network issues.
    """
    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
        session: Optional[Session] = None,
    ):
        """
        Initialize auth dependencies and runtime state.

        Optional arguments make this class easier to test by allowing callers
        to inject fake credentials/session objects.
        """
        # Config is injectable for easier tests, while defaults preserve current behavior.
        self.client_id = (client_id or INTELIX_CLIENT_ID).strip()
        self.client_secret = (client_secret or INTELIX_CLIENT_SECRET).strip()
        self.base_url = (base_url or INTELIX_BASE_URL).strip()
        self.timeout_seconds = timeout_seconds or INTELIX_TIMEOUT_SECONDS
        self.token: Optional[str] = None
        self.token_expiry_epoch: Optional[float] = None
        self.session = session or self._build_retry_session()

    @staticmethod
    def _build_retry_session() -> Session:
        """
        Create an HTTP session with retry policy.

        Retries only cover transient conditions (e.g. 429/5xx) to improve
        resilience without hiding persistent failures.
        """
        retry = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=frozenset(["POST"]),
        )
        adapter = HTTPAdapter(max_retries=retry)
        session = requests.Session()
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def get_access_token(self) -> str:
        """
        Return a valid access token.

        If a cached token exists and has not expired, reuse it.
        Otherwise request a new token from Intelix OAuth endpoint.
        """
        # Reuse token only while it is still valid.
        if (
            self.token
            and self.token_expiry_epoch is not None
            and time.time() < self.token_expiry_epoch
        ):
            return self.token

        # Build OAuth request payload:
        # - Basic auth header with base64(client_id:client_secret)
        # - grant_type=client_credentials as form data
        url = f"{self.base_url}/oauth2/token"

        # Prepare OAuth credentials for Basic authentication.
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded = base64.b64encode(credentials.encode()).decode()

        # Build required headers and form body.
        headers = {
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {"grant_type": "client_credentials"}
        try:
            # Send token request with retries and timeout.
            response = self.session.post(
                url,
                headers=headers,
                data=data,
                timeout=self.timeout_seconds,
            )
        except requests.RequestException as exc:
            # Normalize network exceptions to a clear auth-specific runtime error.
            logging.error("Auth request failed due to network error: %s", exc)
            raise RuntimeError("Intelix authentication network failure") from exc

        # Non-200 indicates auth failure (bad credentials, endpoint issue, etc.).
        if response.status_code != 200:
            logging.error("Auth failed: status=%s", response.status_code)
            raise RuntimeError("Intelix authentication failed")

        # Critical check: without access_token we cannot call analysis APIs.
        body = response.json()
        access_token = body.get("access_token", "").strip()
        if not access_token:
            raise RuntimeError("Intelix auth response missing access_token")

        # Use `expires_in` and refresh 60 seconds early to avoid edge-expiry failures.
        expires_in_seconds = int(body.get("expires_in", 3600))
        self.token_expiry_epoch = time.time() + max(expires_in_seconds - 60, 1)

        # Intelix expects this token string directly in Authorization header.
        self.token = access_token
        logging.info("Access token acquired")
        return self.token