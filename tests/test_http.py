import json
import urllib.error
import urllib.request

import pytest

from notifier.http import HttpError, Response, request


class FakeTransport:
    def __init__(self, *outcomes: Response | Exception) -> None:
        self._outcomes = list(outcomes)
        self.requests: list[urllib.request.Request] = []

    def __call__(self, req: urllib.request.Request, timeout: float) -> Response:
        self.requests.append(req)
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def no_sleep(_: float) -> None:
    return None


def test_success_passthrough() -> None:
    transport = FakeTransport(Response(200, b'{"ok": true}'))

    response = request("GET", "https://api.example.com/x", transport=transport, sleep=no_sleep)

    assert response.status == 200
    assert response.json() == {"ok": True}
    assert transport.requests[0].get_method() == "GET"


def test_json_body_is_encoded_with_content_type() -> None:
    transport = FakeTransport(Response(201, b""))

    request(
        "POST",
        "https://api.example.com/x",
        headers={"Authorization": "Bearer t"},
        json_body={"text": "中文"},
        transport=transport,
        sleep=no_sleep,
    )

    sent = transport.requests[0]
    assert json.loads(sent.data) == {"text": "中文"}
    assert sent.get_header("Content-type") == "application/json"
    assert sent.get_header("Authorization") == "Bearer t"


def test_empty_body_json_is_none() -> None:
    assert Response(204, b"").json() is None


def test_retries_server_errors_with_backoff() -> None:
    sleeps: list[float] = []
    transport = FakeTransport(Response(500, b""), Response(502, b""), Response(200, b"{}"))

    response = request("GET", "https://x", transport=transport, sleep=sleeps.append)

    assert response.status == 200
    assert sleeps == [1, 2]


def test_rate_limit_uses_retry_after_from_body() -> None:
    sleeps: list[float] = []
    transport = FakeTransport(Response(429, b'{"retry_after": 1.5}'), Response(204, b""))

    response = request("POST", "https://x", transport=transport, sleep=sleeps.append)

    assert response.status == 204
    assert sleeps == [1.5]


def test_rate_limit_retry_after_is_capped() -> None:
    sleeps: list[float] = []
    transport = FakeTransport(Response(429, b'{"retry_after": 999}'), Response(200, b""))

    request("POST", "https://x", transport=transport, sleep=sleeps.append)

    assert sleeps == [60]


def test_client_errors_are_returned_without_retry() -> None:
    transport = FakeTransport(Response(404, b"{}"))

    response = request("GET", "https://x", transport=transport, sleep=no_sleep)

    assert response.status == 404
    assert len(transport.requests) == 1


def test_exhausted_retries_raise() -> None:
    transport = FakeTransport(*[Response(503, b"")] * 4)

    with pytest.raises(HttpError) as excinfo:
        request("GET", "https://x", transport=transport, sleep=no_sleep, retries=3)

    assert excinfo.value.status == 503
    assert len(transport.requests) == 4


def test_network_error_raises_without_url_leak() -> None:
    transport = FakeTransport(urllib.error.URLError("boom"))

    with pytest.raises(HttpError) as excinfo:
        request("GET", "https://secret.example/hook", transport=transport, sleep=no_sleep)

    assert excinfo.value.status is None
    assert "secret.example" not in str(excinfo.value)
