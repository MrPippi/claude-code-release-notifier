import pytest

from notifier.config import Config, ConfigError, load_config
from notifier.locales import LOCALES

BASE_ENV = {
    "GITHUB_REPOSITORY": "someone/fork",
    "GITHUB_TOKEN": "gh-token-secret",
    "ANTHROPIC_API_KEY": "sk-ant-secret",
    "DISCORD_WEBHOOK_URL": "https://discord.com/api/webhooks/1/secret",
}


def env(**overrides: str) -> dict[str, str]:
    return {**BASE_ENV, **overrides}


def test_defaults() -> None:
    config = load_config(BASE_ENV)

    assert config == Config(
        source_repo="anthropics/claude-code",
        include_prereleases=True,
        max_releases=5,
        model="claude-sonnet-5-5",
        state_branch="notifier-state",
        repository="someone/fork",
        github_token="gh-token-secret",
        anthropic_api_key="sk-ant-secret",
        discord_webhook_url="https://discord.com/api/webhooks/1/secret",
        dry_run=False,
        locale=LOCALES["zh-TW"],
    )


def test_empty_strings_mean_unset() -> None:
    config = load_config(env(SOURCE_REPO="", MAX_RELEASES_PER_RUN="", CLAUDE_MODEL=""))

    assert config.source_repo == "anthropics/claude-code"
    assert config.max_releases == 5
    assert config.model == "claude-sonnet-5-5"


def test_overrides() -> None:
    config = load_config(
        env(
            SOURCE_REPO="owner/other-repo",
            INCLUDE_PRERELEASES="false",
            MAX_RELEASES_PER_RUN="20",
            CLAUDE_MODEL="claude-opus-5-5",
            STATE_BRANCH="my-state",
            DRY_RUN="true",
            TARGET_LANGUAGE="ja",
        )
    )

    assert config.source_repo == "owner/other-repo"
    assert config.include_prereleases is False
    assert config.max_releases == 20
    assert config.model == "claude-opus-5-5"
    assert config.state_branch == "my-state"
    assert config.dry_run is True
    assert config.locale == LOCALES["ja"]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("TRUE", True), ("1", True), ("yes", True), ("False", False), ("0", False), ("no", False)],
)
def test_bool_parsing(raw: str, expected: bool) -> None:
    assert load_config(env(INCLUDE_PRERELEASES=raw)).include_prereleases is expected


def test_bad_bool_rejected() -> None:
    with pytest.raises(ConfigError, match="INCLUDE_PRERELEASES"):
        load_config(env(INCLUDE_PRERELEASES="maybe"))


@pytest.mark.parametrize("raw", ["abc", "0", "21", "-1", "2.5"])
def test_bad_max_rejected(raw: str) -> None:
    with pytest.raises(ConfigError, match="MAX_RELEASES_PER_RUN"):
        load_config(env(MAX_RELEASES_PER_RUN=raw))


@pytest.mark.parametrize("raw", ["no-slash", "a/b/c", "/repo", "owner/", "own er/repo"])
def test_bad_source_repo_rejected(raw: str) -> None:
    with pytest.raises(ConfigError, match="SOURCE_REPO"):
        load_config(env(SOURCE_REPO=raw))


@pytest.mark.parametrize("name", ["GITHUB_REPOSITORY", "GITHUB_TOKEN", "ANTHROPIC_API_KEY"])
def test_required_values(name: str) -> None:
    with pytest.raises(ConfigError, match=name):
        load_config(env(**{name: ""}))


def test_webhook_required_unless_dry_run() -> None:
    with pytest.raises(ConfigError, match="DISCORD_WEBHOOK_URL"):
        load_config(env(DISCORD_WEBHOOK_URL=""))

    assert load_config(env(DISCORD_WEBHOOK_URL="", DRY_RUN="true")).discord_webhook_url == ""


def test_webhook_must_be_https() -> None:
    with pytest.raises(ConfigError, match="DISCORD_WEBHOOK_URL"):
        load_config(env(DISCORD_WEBHOOK_URL="http://example.com/hook"))


def test_errors_never_leak_secrets() -> None:
    with pytest.raises(ConfigError) as excinfo:
        load_config(env(DISCORD_WEBHOOK_URL="http://secret-hook-value"))

    assert "secret-hook-value" not in str(excinfo.value)


@pytest.mark.parametrize("raw", ["feature/state", "state_v2", "notifier.state"])
def test_valid_state_branch(raw: str) -> None:
    assert load_config(env(STATE_BRANCH=raw)).state_branch == raw


@pytest.mark.parametrize(
    "raw", ["a#b", "a&b", "with space", "-leading", "a..b", "trailing/", "x+y"]
)
def test_bad_state_branch_rejected(raw: str) -> None:
    with pytest.raises(ConfigError, match="STATE_BRANCH"):
        load_config(env(STATE_BRANCH=raw))


def test_target_language_ignores_case() -> None:
    assert load_config(env(TARGET_LANGUAGE="zh-cn")).locale == LOCALES["zh-CN"]


def test_unknown_target_language_rejected() -> None:
    with pytest.raises(ConfigError, match=r"TARGET_LANGUAGE must be one of zh-TW, zh-CN, ja, ko"):
        load_config(env(TARGET_LANGUAGE="fr"))
