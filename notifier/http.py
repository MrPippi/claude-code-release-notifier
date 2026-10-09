"""Minimal JSON-over-HTTP helper with retries for 429 and 5xx responses."""

from __future__ import annotations

import http.client
import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

MAX_RETRY_AFTER_SECONDS = 60.0
DEFAULT_TIMEOUT_SECONDS = 30.0
USER_AGENT = "claude-code-release-notifier"
# Network failures worth retrying. Only idempotent GETs are retried: a POST that timed
# out may already have been delivered, and retrying it could post to Discord twice.
NETWORK_ERRORS = (urllib.error.URLError, TimeoutError, ConnectionError, http.client.HTTPException)


class HttpError(Exception):
    """Raised when a request cannot be completed. Never includes the URL."""

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


@dataclass(frozen=True)
class Response:
    status: int
    body: bytes

    def json(self) -> Any:
        return json.loads(self.body) if self.body else None


Transport = Callable[[urllib.request.Request, float], Response]


def default_transport(req: urllib.request.Request, timeout: float) -> Response:
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return Response(resp.status, resp.read())
    except urllib.error.HTTPError as err:
        return Response(err.code, err.read())


def request(
    method: str,
    url: str,
    *,
    headers: Mapping[str, str] | None = None,
    json_body: Any = None,
    transport: Transport = default_transport,
    sleep: Callable[[float], None] = time.sleep,
    retries: int = 3,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> Response:
    """Send a request; retry 429/5xx up to `retries` times, return any other response."""
    data = None if json_body is None else json.dumps(json_body).encode("utf-8")
    all_headers = {"User-Agent": USER_AGENT, **(headers or {})}
    if data is not None:
        all_headers["Content-Type"] = "application/json"

    for attempt in range(retries + 1):
        req = urllib.request.Request(url, data=data, headers=all_headers, method=method)
        try:
            response = transport(req, timeout)
        except NETWORK_ERRORS as err:
            if method != "GET" or attempt == retries:
                raise HttpError(f"{method} request failed: {_describe(err)}") from None
            sleep(float(2**attempt))
            continue

        if not _is_retryable(response.status):
            return response
        if attempt == retries:
            break
        sleep(_retry_delay(response, attempt))

    raise HttpError(
        f"{method} request failed with HTTP {response.status} after {retries} retries",
        status=response.status,
    )


def _describe(err: Exception) -> str:
    reason = err.reason if isinstance(err, urllib.error.URLError) else err
    return f"{type(err).__name__}: {reason}"


def _is_retryable(status: int) -> bool:
    return status == 429 or status >= 500


def _retry_delay(response: Response, attempt: int) -> float:
    if response.status == 429:
        retry_after = _retry_after_from_body(response)
        if retry_after is not None:
            return min(retry_after, MAX_RETRY_AFTER_SECONDS)
    return float(2**attempt)


def _retry_after_from_body(response: Response) -> float | None:
    try:
        payload = response.json()
    except ValueError:
        return None
    if isinstance(payload, dict) and isinstance(payload.get("retry_after"), int | float):
        return float(payload["retry_after"])
    return None


GITHUB_API = "https://api.github.com"


def github_headers(token: str) -> dict[str, str]:
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }
