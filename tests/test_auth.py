from unittest.mock import Mock

import pytest
import requests

from auth import AuthClient


def _client_with_session(session: Mock) -> AuthClient:
    return AuthClient(
        client_id="id",
        client_secret="secret",
        base_url="https://api.labs.sophos.com",
        timeout_seconds=5,
        session=session,
    )


def test_get_access_token_caches_and_reuses_token() -> None:
    session = Mock()
    response = Mock()
    response.status_code = 200
    response.json.return_value = {"access_token": "token-123", "expires_in": 3600}
    session.post.return_value = response

    client = _client_with_session(session)

    token = client.get_access_token()
    cached = client.get_access_token()

    assert token == "token-123"
    assert cached == token
    assert session.post.call_count == 1


def test_get_access_token_raises_on_network_error() -> None:
    session = Mock()
    session.post.side_effect = requests.RequestException("network down")
    client = _client_with_session(session)

    with pytest.raises(RuntimeError, match="network failure"):
        client.get_access_token()


def test_get_access_token_raises_when_missing_access_token() -> None:
    session = Mock()
    response = Mock()
    response.status_code = 200
    response.json.return_value = {"expires_in": 3600}
    session.post.return_value = response

    client = _client_with_session(session)

    with pytest.raises(RuntimeError, match="missing access_token"):
        client.get_access_token()
