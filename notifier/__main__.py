"""Entry point: `python -m notifier`."""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import anthropic

from notifier.config import Config, ConfigError, load_config
from notifier.discord import DiscordError, build_payload, post_embed
from notifier.http import HttpError, Response, request
from notifier.releases import fetch_releases, select_new
from notifier.state import StateError, read_state, state_from_release, write_state
from notifier.translate import TranslationError, make_client, translate

KNOWN_ERRORS = (
    ConfigError,
    HttpError,
    StateError,
    TranslationError,
    DiscordError,
    anthropic.APIError,
)


def utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def run(
    config: Config,
    *,
    client: Any,
    http: Callable[..., Response] = request,
    now: Callable[[], str] = utc_now,
    log: Callable[[str], None] = print,
) -> int:
    token = config.github_token
    state = read_state(config.repository, config.state_branch, token, http=http)
    releases = fetch_releases(config.source_repo, token, config.include_prereleases, http=http)
    selected = select_new(releases, state.last_published_at if state else None, config.max_releases)
    if not selected:
        log(f"No new releases since {state.last_tag if state else 'start'}.")
        return 0

    log(f"Notifying {len(selected)} release(s): {', '.join(r.tag for r in selected)}")
    for release in selected:
        payload = build_payload(release, translate(release, config.model, client=client))
        if config.dry_run:
            log(f"[dry run] {release.tag} payload:")
            log(json.dumps(payload, ensure_ascii=False, indent=2))
            continue
        post_embed(config.discord_webhook_url, payload, http=http)
        write_state(
            config.repository,
            config.state_branch,
            token,
            state_from_release(release, now()),
            http=http,
        )
        log(f"Notified {release.tag}")
    return 0


def main() -> int:
    try:
        config = load_config(os.environ)
        return run(config, client=make_client(config.anthropic_api_key))
    except KNOWN_ERRORS as err:
        print(f"::error::{err}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
