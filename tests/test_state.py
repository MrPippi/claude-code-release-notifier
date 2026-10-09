import base64
import json

import pytest

from notifier.http import Response
from notifier.releases import Release
from notifier.state import State, StateError, read_state, state_from_release, write_state

STATE = State(
    last_tag="v2", last_published_at="2026-01-02T00:00:00Z", updated_at="2026-01-03T00:00:00Z"
)
CONTENTS_URL = "https://api.github.com/repos/me/fork/contents/state.json"


def encoded(payload: object) -> str:
    return base64.b64encode(json.dumps(payload).encode()).decode()


class FakeHttp:
    def __init__(self, routes: dict[tuple[str, str], Response]) -> None:
        self.routes = routes
        self.calls: list[tuple[str, str, object]] = []

    def __call__(self, method: str, url: str, **kwargs: object) -> Response:
        self.calls.append((method, url, kwargs.get("json_body")))
        return self.routes[(method, url)]


def test_read_state_ok() -> None:
    body = {"content": encoded({"last_tag": "v2", "last_published_at": "x", "updated_at": "y"})}
    http = FakeHttp({("GET", f"{CONTENTS_URL}?ref=state"): Response(200, json.dumps(body).encode())})

    assert read_state("me/fork", "state", "tok", http=http) == State("v2", "x", "y")


def test_read_state_missing_returns_none() -> None:
    http = FakeHttp({("GET", f"{CONTENTS_URL}?ref=state"): Response(404, b"{}")})

    assert read_state("me/fork", "state", "tok", http=http) is None


def test_read_state_malformed_raises() -> None:
    body = {"content": encoded({"unexpected": True})}
    http = FakeHttp({("GET", f"{CONTENTS_URL}?ref=state"): Response(200, json.dumps(body).encode())})

    with pytest.raises(StateError, match="malformed"):
        read_state("me/fork", "state", "tok", http=http)


def test_read_state_server_error_raises() -> None:
    http = FakeHttp({("GET", f"{CONTENTS_URL}?ref=state"): Response(403, b"{}")})

    with pytest.raises(StateError, match="403"):
        read_state("me/fork", "state", "tok", http=http)


def test_write_state_updates_existing_file() -> None:
    http = FakeHttp(
        {
            ("GET", "https://api.github.com/repos/me/fork/git/ref/heads/state"): Response(200, b"{}"),
            ("GET", f"{CONTENTS_URL}?ref=state"): Response(200, b'{"sha": "abc"}'),
            ("PUT", CONTENTS_URL): Response(200, b"{}"),
        }
    )

    write_state("me/fork", "state", "tok", STATE, http=http)

    method, _, body = http.calls[-1]
    assert method == "PUT"
    assert body["sha"] == "abc"
    assert body["branch"] == "state"
    assert json.loads(base64.b64decode(body["content"])) == {
        "last_tag": "v2",
        "last_published_at": "2026-01-02T00:00:00Z",
        "updated_at": "2026-01-03T00:00:00Z",
    }


def test_write_state_creates_file_on_existing_branch() -> None:
    http = FakeHttp(
        {
            ("GET", "https://api.github.com/repos/me/fork/git/ref/heads/state"): Response(200, b"{}"),
            ("GET", f"{CONTENTS_URL}?ref=state"): Response(404, b"{}"),
            ("PUT", CONTENTS_URL): Response(201, b"{}"),
        }
    )

    write_state("me/fork", "state", "tok", STATE, http=http)

    assert "sha" not in http.calls[-1][2]


def test_write_state_creates_orphan_branch() -> None:
    api = "https://api.github.com/repos/me/fork/git"
    http = FakeHttp(
        {
            ("GET", f"{api}/ref/heads/state"): Response(404, b"{}"),
            ("POST", f"{api}/blobs"): Response(201, b'{"sha": "blob1"}'),
            ("POST", f"{api}/trees"): Response(201, b'{"sha": "tree1"}'),
            ("POST", f"{api}/commits"): Response(201, b'{"sha": "commit1"}'),
            ("POST", f"{api}/refs"): Response(201, b"{}"),
        }
    )

    write_state("me/fork", "state", "tok", STATE, http=http)

    posts = {url.rsplit("/", 1)[-1]: body for method, url, body in http.calls if method == "POST"}
    assert posts["trees"]["tree"][0] == {
        "path": "state.json",
        "mode": "100644",
        "type": "blob",
        "sha": "blob1",
    }
    assert posts["commits"]["parents"] == []
    assert posts["commits"]["tree"] == "tree1"
    assert posts["refs"] == {"ref": "refs/heads/state", "sha": "commit1"}


def test_write_state_failure_raises() -> None:
    http = FakeHttp(
        {
            ("GET", "https://api.github.com/repos/me/fork/git/ref/heads/state"): Response(200, b"{}"),
            ("GET", f"{CONTENTS_URL}?ref=state"): Response(404, b"{}"),
            ("PUT", CONTENTS_URL): Response(409, b"{}"),
        }
    )

    with pytest.raises(StateError, match="409"):
        write_state("me/fork", "state", "tok", STATE, http=http)


def test_state_from_release() -> None:
    rel = Release("v9", "v9", "", "u", "2026-02-01T00:00:00Z", False)

    assert state_from_release(rel, "now") == State("v9", "2026-02-01T00:00:00Z", "now")
