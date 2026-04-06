from unittest.mock import Mock, patch

from client import IntelixClient
from pathlib import Path


def _resp(status_code: int, payload=None, text: str = "") -> Mock:
    response = Mock()
    response.status_code = status_code
    response.text = text
    response.json.return_value = payload if payload is not None else {}
    return response


def test_build_regional_url_variants() -> None:
    assert (
        IntelixClient._build_regional_url("https://api.labs.sophos.com", "us")
        == "https://us.api.labs.sophos.com"
    )
    assert (
        IntelixClient._build_regional_url("https://de.api.labs.sophos.com", "de")
        == "https://de.api.labs.sophos.com"
    )
    assert (
        IntelixClient._build_regional_url("api.labs.sophos.com", "us")
        == "https://us.api.labs.sophos.com"
    )


def test_handle_analysis_response_200_returns_body() -> None:
    client = IntelixClient()
    response = _resp(200, {"result": "ok"})
    assert client._handle_analysis_response("a.exe", response, {"Authorization": "x"}) == {
        "result": "ok"
    }


def test_handle_analysis_response_202_polls_with_job_id() -> None:
    client = IntelixClient()
    response = _resp(202, {"jobId": "job-1"})
    with patch.object(client, "_poll_report", return_value={"done": True}) as poll:
        result = client._handle_analysis_response("a.exe", response, {"Authorization": "x"})
    assert result == {"done": True}
    poll.assert_called_once_with("job-1", {"Authorization": "x"})


def test_handle_analysis_response_202_without_job_id_returns_none() -> None:
    client = IntelixClient()
    response = _resp(202, {})
    assert client._handle_analysis_response("a.exe", response, {"Authorization": "x"}) is None


def test_handle_analysis_response_non_200_202_returns_none() -> None:
    client = IntelixClient()
    response = _resp(400, {"error": "bad request"}, text="bad request")
    assert client._handle_analysis_response("a.exe", response, {"Authorization": "x"}) is None


def test_poll_report_retries_202_then_returns_200() -> None:
    client = IntelixClient()
    with (
        patch("client.requests.get") as get_mock,
        patch("client.time.sleep") as sleep_mock,
    ):
        get_mock.side_effect = [
            _resp(202, {}),
            _resp(202, {}),
            _resp(200, {"verdict": "clean"}),
        ]
        result = client._poll_report("job-1", {"Authorization": "x"})

    assert result == {"verdict": "clean"}
    assert sleep_mock.call_count == 2


def test_poll_report_returns_none_on_unexpected_status() -> None:
    client = IntelixClient()
    with patch("client.requests.get", return_value=_resp(500, text="server error")):
        result = client._poll_report("job-1", {"Authorization": "x"})
    assert result is None


def test_poll_report_returns_none_on_timeout() -> None:
    client = IntelixClient()
    with (
        patch("client.INTELIX_MAX_POLL_ATTEMPTS", 3),
        patch("client.requests.get", return_value=_resp(202)),
        patch("client.time.sleep") as sleep_mock,
    ):
        result = client._poll_report("job-1", {"Authorization": "x"})
    assert result is None
    assert sleep_mock.call_count == 3


def test_analyze_file_returns_none_when_post_raises() -> None:
    client = IntelixClient()
    client.auth = Mock()
    client.auth.get_access_token.return_value = "token"

    test_file = Path(__file__).resolve()
    with patch("client.requests.post", side_effect=RuntimeError("boom")):
        result = client.analyze_file(test_file)
    assert result is None
