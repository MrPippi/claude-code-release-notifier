import json
from typing import Any

import pytest

from notifier import __main__ as entry
from notifier.config import Config
from notifier.discord import DiscordError
from notifier.releases import Release
from notifier.state import State

CONFIG = Config(
    source_repo="anthropics/claude-code",
    include_prereleases=True,
    max_releases=5,
    model="claude-sonnet-5-5",
    state_branch="notifier-state",
    repository="me/fork",
    github_token="tok",
    anthropic_api_key="key",
    discord_webhook_url="https://discord.com/api/webhooks/1/x",
    dry_run=False,
)
R1 = Release("v1", "v1", "one", "u1", "2026-01-01T00:00:00Z", False)
R2 = Release("v2", "v2", "two", "u2", "2026-01-02T00:00:00Z", False)
R3 = Release("v3", "v3", "three", "u3", "2026-01-03T00:00:00Z", False)


class Recorder:
    def __init__(
        self, monkeypatch: pytest.MonkeyPatch, releases: list[Release], state: State | None
    ):
        self.posts: list[dict[str, Any]] = []
        self.states: list[State] = []
        self.shas_in: list[str | None] = []
        self.logs: list[str] = []
        self.fail_post_for: str | None = None
        monkeypatch.setattr(entry, "read_state", lambda *a, **k: state)
        monkeypatch.setattr(entry, "fetch_releases", lambda *a, **k: releases)
        monkeypatch.setattr(entry, "translate", lambda r, model, client: f"譯:{r.tag}")
        monkeypatch.setattr(entry, "post_embed", self._post)
        monkeypatch.setattr(entry, "write_state", self._write)

    def _write(
        self, repo: str, branch: str, token: str, state: State, sha: str | None, http: Any
    ) -> str:
        self.states.append(state)
        self.shas_in.append(sha)
        return f"sha-{state.last_tag}"

    def _post(self, url: str, payload: dict[str, Any], http: Any) -> None:
        title = payload["embeds"][0]["title"]
        if self.fail_post_for and title.endswith(self.fail_post_for):
            raise DiscordError("Discord webhook returned HTTP 500")
        self.posts.append(payload)

    def run(self, config: Config = CONFIG) -> int:
        return entry.run(config, client=object(), now=lambda: "NOW", log=self.logs.append)


def test_nothing_new(monkeypatch: pytest.MonkeyPatch) -> None:
    rec = Recorder(monkeypatch, [R1], State("v1", R1.published_at, "t"))

    assert rec.run() == 0
    assert rec.posts == []
    assert rec.states == []
    assert any("No new releases" in line for line in rec.logs)


def test_posts_each_new_release_in_order(monkeypatch: pytest.MonkeyPatch) -> None:
    rec = Recorder(monkeypatch, [R3, R2, R1], State("v1", R1.published_at, "t"))

    assert rec.run() == 0
    assert [p["embeds"][0]["description"] for p in rec.posts] == ["譯:v2", "譯:v3"]
    assert [s.last_tag for s in rec.states] == ["v2", "v3"]
    assert rec.states[0].updated_at == "NOW"
    assert rec.shas_in == [None, "sha-v2"]


def test_dry_run_skips_side_effects(monkeypatch: pytest.MonkeyPatch) -> None:
    rec = Recorder(monkeypatch, [R2], None)
    dry = Config(**{**CONFIG.__dict__, "dry_run": True})

    assert rec.run(dry) == 0
    assert rec.posts == []
    assert rec.states == []
    payload = json.loads(next(line for line in rec.logs if line.startswith("{")))
    assert payload["embeds"][0]["description"] == "譯:v2"


def test_failure_keeps_earlier_state(monkeypatch: pytest.MonkeyPatch) -> None:
    rec = Recorder(monkeypatch, [R3, R2, R1], State("v1", R1.published_at, "t"))
    rec.fail_post_for = "v3"

    with pytest.raises(DiscordError):
        rec.run()
    assert [s.last_tag for s in rec.states] == ["v2"]


def test_main_reports_known_errors(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(entry.os, "environ", {})

    assert entry.main() == 1
    assert "::error::" in capsys.readouterr().out


def test_main_runs_with_loaded_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(entry, "load_config", lambda env: CONFIG)
    monkeypatch.setattr(entry, "make_client", lambda key: object())
    monkeypatch.setattr(entry, "run", lambda config, client: 0)

    assert entry.main() == 0


def test_main_maps_runtime_errors(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def boom(config: Config, client: object) -> int:
        raise DiscordError("Discord webhook returned HTTP 500")

    monkeypatch.setattr(entry, "load_config", lambda env: CONFIG)
    monkeypatch.setattr(entry, "make_client", lambda key: object())
    monkeypatch.setattr(entry, "run", boom)

    assert entry.main() == 1
    assert "::error::Discord webhook returned HTTP 500" in capsys.readouterr().out
