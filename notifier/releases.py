"""Fetch releases from GitHub and pick the ones that still need a notification."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from notifier.http import GITHUB_API, HttpError, Response, github_headers, request

RELEASES_PER_PAGE = 100
# Upper bound on pagination: 1,000 releases is far more than any realistic backlog.
MAX_PAGES = 10

# Position of a release in the notification order: (published_at, tag).
Cursor = tuple[str, str]


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
    stop_after: str | None,
    http: Callable[..., Response] = request,
) -> list[Release]:
    """List releases newest first, paging until one published at or before `stop_after`.

    With `stop_after=None` (no state yet) only the first page is needed.
    """
    items: list[dict[str, Any]] = []
    for page in range(1, MAX_PAGES + 1):
        batch = _fetch_page(source_repo, token, page, http)
        items = [*items, *batch]
        reached_state = stop_after is None or any(
            entry.get("published_at") and entry["published_at"] <= stop_after for entry in batch
        )
        if reached_state or len(batch) < RELEASES_PER_PAGE:
            break
    return parse_releases(items, include_prereleases)


def _fetch_page(
    source_repo: str, token: str, page: int, http: Callable[..., Response]
) -> list[dict[str, Any]]:
    url = f"{GITHUB_API}/repos/{source_repo}/releases?per_page={RELEASES_PER_PAGE}&page={page}"
    response = http("GET", url, headers=github_headers(token))
    if response.status != 200:
        raise HttpError(
            f"Listing releases of {source_repo} failed with HTTP {response.status}",
            status=response.status,
        )
    return response.json()


def select_new(
    releases: Sequence[Release], last: Cursor | None, max_releases: int
) -> list[Release]:
    """Releases after `last`, oldest first, at most `max_releases`.

    Releases are ordered by (published_at, tag) so two releases published in the same
    second are never lost when the per-run cap falls between them. Without previous
    state only the newest release is returned, so a fresh fork does not flood the
    channel with history.
    """
    ordered = sorted(releases, key=cursor_of)
    if last is None:
        return ordered[-1:]
    newer = [r for r in ordered if cursor_of(r) > last]
    return newer[:max_releases]


def cursor_of(release: Release) -> Cursor:
    return (release.published_at, release.tag)
