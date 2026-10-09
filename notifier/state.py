"""Persist "last notified release" in state.json on a dedicated orphan branch."""

from __future__ import annotations

import base64
import json
from collections.abc import Callable
from dataclasses import asdict, dataclass
from typing import Any
from urllib.parse import quote

from notifier.http import GITHUB_API, Response, github_headers, request
from notifier.releases import Release

STATE_FILE = "state.json"

Http = Callable[..., Response]


class StateError(Exception):
    """Raised when state cannot be read or written."""


@dataclass(frozen=True)
class State:
    last_tag: str
    last_published_at: str
    updated_at: str


def state_from_release(release: Release, now: str) -> State:
    return State(last_tag=release.tag, last_published_at=release.published_at, updated_at=now)


def read_state(repository: str, branch: str, token: str, *, http: Http = request) -> State | None:
    """Return the stored state, or None when the branch or file does not exist yet."""
    response = _get_contents(repository, branch, token, http)
    if response.status == 404:
        return None
    _expect(response, "Reading state")
    try:
        raw = base64.b64decode(response.json()["content"])
        data = json.loads(raw)
        return State(
            last_tag=data["last_tag"],
            last_published_at=data["last_published_at"],
            updated_at=data["updated_at"],
        )
    except (KeyError, TypeError, ValueError) as err:
        raise StateError(f"{STATE_FILE} on branch {branch!r} is malformed: {err}") from None


def write_state(
    repository: str,
    branch: str,
    token: str,
    state: State,
    *,
    sha: str | None = None,
    http: Http = request,
) -> str:
    """Write state and return the new blob sha of state.json.

    Pass the sha returned by the previous call to skip the lookups; the contents API can
    serve a stale sha right after a write, which would make the next PUT fail.
    """
    content = json.dumps(asdict(state), indent=2, ensure_ascii=False) + "\n"
    message = f"chore(state): record {state.last_tag}"
    if sha is not None:
        return _put_file(repository, branch, token, content, message, sha, http)
    if not _branch_exists(repository, branch, token, http):
        return _create_orphan_branch(repository, branch, token, content, message, http)
    existing = _get_contents(repository, branch, token, http)
    if existing.status == 404:
        return _put_file(repository, branch, token, content, message, None, http)
    _expect(existing, "Reading state")
    return _put_file(repository, branch, token, content, message, existing.json()["sha"], http)


def _get_contents(repository: str, branch: str, token: str, http: Http) -> Response:
    url = f"{GITHUB_API}/repos/{repository}/contents/{STATE_FILE}?ref={quote(branch, safe='')}"
    return http("GET", url, headers=github_headers(token))


def _branch_exists(repository: str, branch: str, token: str, http: Http) -> bool:
    url = f"{GITHUB_API}/repos/{repository}/git/ref/heads/{quote(branch, safe='/')}"
    response = http("GET", url, headers=github_headers(token))
    if response.status == 404:
        return False
    _expect(response, "Looking up state branch")
    return True


def _put_file(
    repository: str,
    branch: str,
    token: str,
    content: str,
    message: str,
    sha: str | None,
    http: Http,
) -> str:
    body: dict[str, Any] = {
        "message": message,
        "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
        "branch": branch,
    }
    if sha is not None:
        body = {**body, "sha": sha}
    url = f"{GITHUB_API}/repos/{repository}/contents/{STATE_FILE}"
    response = http("PUT", url, headers=github_headers(token), json_body=body)
    _expect(response, "Writing state")
    return response.json()["content"]["sha"]


def _create_orphan_branch(
    repository: str, branch: str, token: str, content: str, message: str, http: Http
) -> str:
    git_api = f"{GITHUB_API}/repos/{repository}/git"
    headers = github_headers(token)

    def post(path: str, body: dict[str, Any]) -> Any:
        response = http("POST", f"{git_api}/{path}", headers=headers, json_body=body)
        _expect(response, f"Creating state branch ({path})")
        return response.json()

    blob = post("blobs", {"content": content, "encoding": "utf-8"})
    tree = post(
        "trees",
        {"tree": [{"path": STATE_FILE, "mode": "100644", "type": "blob", "sha": blob["sha"]}]},
    )
    commit = post("commits", {"message": message, "tree": tree["sha"], "parents": []})
    post("refs", {"ref": f"refs/heads/{branch}", "sha": commit["sha"]})
    return blob["sha"]


def _expect(response: Response, action: str) -> None:
    if not 200 <= response.status < 300:
        raise StateError(f"{action} failed with HTTP {response.status}")
