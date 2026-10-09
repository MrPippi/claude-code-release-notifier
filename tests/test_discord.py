import pytest

from notifier.discord import (
    DESCRIPTION_LIMIT,
    DiscordError,
    build_payload,
    post_embed,
)
from notifier.http import Response
from notifier.locales import LOCALES
from notifier.releases import Release

STABLE = Release("v2.1.300", "v2.1.300", "", "https://gh/r/v2.1.300", "2026-10-08T19:48:38Z", False)
PRE = Release("v3.0.0-beta", "v3.0.0-beta", "", "https://gh/r/b", "2026-10-09T00:00:00Z", True)
ZH_TW = LOCALES["zh-TW"]
WEBHOOK = "https://discord.com/api/webhooks/1/secret-token"


def embed(payload: dict) -> dict:
    return payload["embeds"][0]


def test_stable_embed() -> None:
    result = embed(build_payload(STABLE, "內容", ZH_TW))

    assert result["title"] == "🚀 正式版  Claude Code v2.1.300"
    assert result["color"] == 16744272
    assert result["url"] == "https://gh/r/v2.1.300"
    assert result["description"] == "內容"
    assert result["footer"]["text"] == "發布日期：2026-10-08  •  查看原文 → https://gh/r/v2.1.300"
    assert result["author"]["name"] == "Anthropic Claude Code"


def test_prerelease_embed() -> None:
    result = embed(build_payload(PRE, "內容", ZH_TW))

    assert result["title"] == "🧪 Pre-release  Claude Code v3.0.0-beta"
    assert result["color"] == 16776960


def test_embed_uses_locale_labels() -> None:
    ja = LOCALES["ja"]

    stable = embed(build_payload(STABLE, "本文", ja))
    pre = embed(build_payload(PRE, "本文", ja))

    assert stable["title"] == f"{ja.stable_badge}  Claude Code v2.1.300"
    assert pre["title"] == f"{ja.prerelease_badge}  Claude Code v3.0.0-beta"
    assert stable["footer"]["text"] == "公開日：2026-10-08  •  原文を見る → https://gh/r/v2.1.300"


def test_description_at_limit_is_untouched() -> None:
    text = "字" * DESCRIPTION_LIMIT

    assert embed(build_payload(STABLE, text, ZH_TW))["description"] == text


def test_long_description_is_truncated_with_notice() -> None:
    text = "字" * (DESCRIPTION_LIMIT + 1)

    description = embed(build_payload(STABLE, text, ZH_TW))["description"]

    assert description.endswith(ZH_TW.truncated_notice)
    assert description.startswith("字" * 3900)
    assert len(description) <= DESCRIPTION_LIMIT


def test_post_success() -> None:
    calls: list[tuple] = []

    def fake_http(method: str, url: str, **kwargs: object) -> Response:
        calls.append((method, url, kwargs["json_body"]))
        return Response(204, b"")

    post_embed(WEBHOOK, {"embeds": []}, http=fake_http)

    assert calls == [("POST", WEBHOOK, {"embeds": []})]


def test_post_failure_does_not_leak_webhook() -> None:
    def fake_http(method: str, url: str, **kwargs: object) -> Response:
        return Response(400, b'{"message": "Invalid Form Body"}')

    with pytest.raises(DiscordError) as excinfo:
        post_embed(WEBHOOK, {"embeds": []}, http=fake_http)

    assert "400" in str(excinfo.value)
    assert "secret-token" not in str(excinfo.value)
