"""Fetch releases from GitHub and pick the ones that still need a notification."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from notifier.http import GITHUB_API, HttpError, Response, github_headers, request

RELEASES_PER_PAGE = 50


@dataclass(frozen=True)
class Release:
    tag: str
    name: str
    body: str
    url: str
    published_at: str
    prerelease: bool


def parse_releases(items: Sequence[dict[str, Any]], include_prereleases: bool) -> list[Release]:
    """Convert GitHub API items, dropping drafts, unpublished and (optionally) pre-releases."""
    return [
        Release(
            tag=entry["tag_name"],
            name=entry.get("name") or entry["tag_name"],
            body=entry.get("body") or "",
            url=entry.get("html_url") or "",
            published_at=entry["published_at"],
            prerelease=bool(entry.get("prerelease")),
        )
        for entry in items
        if not entry.get("draft")
        and entry.get("published_at")
        and (include_prereleases or not entry.get("prerelease"))
    ]


def fetch_releases(
    source_repo: str,
    token: str,
    include_prereleases: bool,
    *,
    http: Callable[..., Response] = request,
) -> list[Release]:
    url = f"{GITHUB_API}/repos/{source_repo}/releases?per_page={RELEASES_PER_PAGE}"
    response = http("GET", url, headers=github_headers(token))
    if response.status != 200:
        raise HttpError(
            f"Listing releases of {source_repo} failed with HTTP {response.status}",
            status=response.status,
        )
    return parse_releases(response.json(), include_prereleases)


def select_new(
    releases: Sequence[Release], last_published_at: str | None, max_releases: int
) -> list[Release]:
    """Releases newer than the last notified one, oldest first, at most `max_releases`.

    Without previous state only the newest release is returned, so a fresh fork does not
    flood the channel with history.
    """
    ordered = sorted(releases, key=lambda r: (r.published_at, r.tag))
    if last_published_at is None:
        return ordered[-1:]
    newer = [r for r in ordered if r.published_at > last_published_at]
    return newer[:max_releases]
