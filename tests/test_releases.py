import pytest

from notifier.http import HttpError, Response
from notifier.releases import Release, fetch_releases, parse_releases, select_new


def item(tag: str, published_at: str | None, **extra: object) -> dict:
    return {
        "tag_name": tag,
        "name": tag,
        "body": f"notes for {tag}",
        "html_url": f"https://github.com/o/r/releases/tag/{tag}",
        "published_at": published_at,
        "prerelease": False,
        "draft": False,
        **extra,
    }


def release(tag: str, published_at: str, prerelease: bool = False) -> Release:
    return Release(
        tag=tag,
        name=tag,
        body=f"notes for {tag}",
        url=f"https://github.com/o/r/releases/tag/{tag}",
        published_at=published_at,
        prerelease=prerelease,
    )


def test_parse_maps_fields() -> None:
    assert parse_releases([item("v1", "2026-01-01T00:00:00Z")], True) == [
        release("v1", "2026-01-01T00:00:00Z")
    ]


def test_parse_drops_drafts_and_unpublished() -> None:
    items = [item("v1", "2026-01-01T00:00:00Z", draft=True), item("v2", None)]

    assert parse_releases(items, True) == []


def test_parse_filters_prereleases_when_disabled() -> None:
    items = [item("v1", "2026-01-01T00:00:00Z", prerelease=True)]

    assert parse_releases(items, False) == []
    assert parse_releases(items, True)[0].prerelease is True


def test_parse_null_body_becomes_empty_string() -> None:
    assert parse_releases([item("v1", "2026-01-01T00:00:00Z", body=None)], True)[0].body == ""


def test_select_first_run_returns_newest_only() -> None:
    releases = [release("v2", "2026-01-02T00:00:00Z"), release("v1", "2026-01-01T00:00:00Z")]

    assert select_new(releases, None, 5) == [release("v2", "2026-01-02T00:00:00Z")]


def test_select_empty() -> None:
    assert select_new([], None, 5) == []
    assert select_new([], "2026-01-01T00:00:00Z", 5) == []


def test_select_newer_oldest_first() -> None:
    releases = [
        release("v4", "2026-01-04T00:00:00Z"),
        release("v3", "2026-01-03T00:00:00Z"),
        release("v2", "2026-01-02T00:00:00Z"),
    ]

    selected = select_new(releases, "2026-01-02T00:00:00Z", 5)

    assert [r.tag for r in selected] == ["v3", "v4"]


def test_select_cap_keeps_oldest() -> None:
    releases = [release(f"v{i}", f"2026-01-0{i}T00:00:00Z") for i in range(2, 7)]

    selected = select_new(releases, "2026-01-01T00:00:00Z", 2)

    assert [r.tag for r in selected] == ["v2", "v3"]


def test_select_identical_timestamps_both_kept_in_tag_order() -> None:
    releases = [release("v2b", "2026-01-02T00:00:00Z"), release("v2a", "2026-01-02T00:00:00Z")]

    selected = select_new(releases, "2026-01-01T00:00:00Z", 5)

    assert [r.tag for r in selected] == ["v2a", "v2b"]


def test_select_does_not_mutate_input() -> None:
    releases = [release("v2", "2026-01-02T00:00:00Z"), release("v1", "2026-01-01T00:00:00Z")]
    snapshot = list(releases)

    select_new(releases, "2026-01-01T00:00:00Z", 5)

    assert releases == snapshot


def test_fetch_calls_api_with_auth() -> None:
    calls: list[tuple] = []

    def fake_http(method: str, url: str, **kwargs: object) -> Response:
        calls.append((method, url, kwargs))
        return Response(200, b'[{"tag_name": "v1", "published_at": "2026-01-01T00:00:00Z"}]')

    releases = fetch_releases("o/r", "tok", True, http=fake_http)

    assert [r.tag for r in releases] == ["v1"]
    method, url, kwargs = calls[0]
    assert method == "GET"
    assert url == "https://api.github.com/repos/o/r/releases?per_page=50"
    assert kwargs["headers"]["Authorization"] == "Bearer tok"


def test_fetch_non_200_raises() -> None:
    def fake_http(method: str, url: str, **kwargs: object) -> Response:
        return Response(404, b'{"message": "Not Found"}')

    with pytest.raises(HttpError, match="404"):
        fetch_releases("o/r", "tok", True, http=fake_http)
