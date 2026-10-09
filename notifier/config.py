"""Load and validate notifier configuration from environment variables."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass

from notifier.locales import DEFAULT_LOCALE, LOCALES, Locale, find_locale

DEFAULT_SOURCE_REPO = "anthropics/claude-code"
DEFAULT_MODEL = "claude-sonnet-5-5"
DEFAULT_STATE_BRANCH = "notifier-state"
DEFAULT_MAX_RELEASES = 5
MAX_RELEASES_LIMIT = 20

_REPO_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
# Conservative subset of git ref names: safe in URLs and API paths without surprises.
_BRANCH_PATTERN = re.compile(r"^(?!-)(?!.*\.\.)(?!.*/$)[A-Za-z0-9._/-]+$")
_TRUE_VALUES = frozenset({"true", "1", "yes"})
_FALSE_VALUES = frozenset({"false", "0", "no"})


class ConfigError(Exception):
    """Raised when configuration is missing or invalid."""


@dataclass(frozen=True)
class Config:
    source_repo: str
    include_prereleases: bool
    max_releases: int
    model: str
    state_branch: str
    repository: str
    github_token: str
    anthropic_api_key: str
    discord_webhook_url: str
    dry_run: bool
    locale: Locale


def load_config(env: Mapping[str, str]) -> Config:
    """Build a Config from an environment mapping. Empty strings count as unset."""
    dry_run = _parse_bool(env, "DRY_RUN", default=False)
    webhook = _get(env, "DISCORD_WEBHOOK_URL", default="")
    if not dry_run:
        _require_value(webhook, "DISCORD_WEBHOOK_URL")
    if webhook and not webhook.startswith("https://"):
        raise ConfigError("DISCORD_WEBHOOK_URL must be an https:// URL")

    return Config(
        source_repo=_parse_repo(env, "SOURCE_REPO", default=DEFAULT_SOURCE_REPO),
        include_prereleases=_parse_bool(env, "INCLUDE_PRERELEASES", default=True),
        max_releases=_parse_max_releases(env),
        model=_get(env, "CLAUDE_MODEL", default=DEFAULT_MODEL),
        state_branch=_parse_branch(env),
        repository=_parse_repo(env, "GITHUB_REPOSITORY", default=""),
        github_token=_require_value(_get(env, "GITHUB_TOKEN", default=""), "GITHUB_TOKEN"),
        anthropic_api_key=_require_value(
            _get(env, "ANTHROPIC_API_KEY", default=""), "ANTHROPIC_API_KEY"
        ),
        discord_webhook_url=webhook,
        dry_run=dry_run,
        locale=_parse_locale(env),
    )


def _get(env: Mapping[str, str], name: str, *, default: str) -> str:
    value = env.get(name, "").strip()
    return value or default


def _require_value(value: str, name: str) -> str:
    if not value:
        raise ConfigError(f"{name} is required but not set")
    return value


def _parse_repo(env: Mapping[str, str], name: str, *, default: str) -> str:
    value = _require_value(_get(env, name, default=default), name)
    if not _REPO_PATTERN.match(value):
        raise ConfigError(f"{name} must look like 'owner/name', got {value!r}")
    return value


def _parse_bool(env: Mapping[str, str], name: str, *, default: bool) -> bool:
    raw = _get(env, name, default="").lower()
    if not raw:
        return default
    if raw in _TRUE_VALUES:
        return True
    if raw in _FALSE_VALUES:
        return False
    raise ConfigError(f"{name} must be true or false, got {raw!r}")


def _parse_max_releases(env: Mapping[str, str]) -> int:
    raw = _get(env, "MAX_RELEASES_PER_RUN", default=str(DEFAULT_MAX_RELEASES))
    if not raw.isdigit() or not 1 <= int(raw) <= MAX_RELEASES_LIMIT:
        raise ConfigError(
            f"MAX_RELEASES_PER_RUN must be an integer from 1 to {MAX_RELEASES_LIMIT}, got {raw!r}"
        )
    return int(raw)


def _parse_branch(env: Mapping[str, str]) -> str:
    value = _get(env, "STATE_BRANCH", default=DEFAULT_STATE_BRANCH)
    if not _BRANCH_PATTERN.match(value):
        raise ConfigError(
            f"STATE_BRANCH may only contain letters, digits, '.', '_', '-' and '/', got {value!r}"
        )
    return value


def _parse_locale(env: Mapping[str, str]) -> Locale:
    value = _get(env, "TARGET_LANGUAGE", default=DEFAULT_LOCALE)
    locale = find_locale(value)
    if locale is None:
        raise ConfigError(f"TARGET_LANGUAGE must be one of {', '.join(LOCALES)}, got {value!r}")
    return locale
