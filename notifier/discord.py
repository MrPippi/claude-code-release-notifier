"""Build and send the Discord embed for a translated release."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from notifier.http import Response, request
from notifier.releases import Release

DESCRIPTION_LIMIT = 4096
TRUNCATE_AT = 3900
TRUNCATED_NOTICE = "\n\n… （內容過長，請至原文連結閱讀完整內容）"
STABLE_COLOR = 16744272
PRERELEASE_COLOR = 16776960
AUTHOR = {
    "name": "Anthropic Claude Code",
    "icon_url": "https://avatars.githubusercontent.com/u/76263028",
}


class DiscordError(Exception):
    """Raised when Discord rejects the webhook call. Never includes the webhook URL."""


def build_payload(release: Release, translated: str) -> dict[str, Any]:
    badge = "🧪 Pre-release" if release.prerelease else "🚀 正式版"
    return {
        "embeds": [
            {
                "author": AUTHOR,
                "title": f"{badge}  Claude Code {release.tag}",
                "url": release.url,
                "description": _truncate(translated),
                "color": PRERELEASE_COLOR if release.prerelease else STABLE_COLOR,
                "footer": {
                    "text": f"發布日期：{release.published_at[:10]}  •  查看原文 → {release.url}"
                },
            }
        ]
    }


def post_embed(
    webhook_url: str, payload: dict[str, Any], *, http: Callable[..., Response] = request
) -> None:
    response = http("POST", webhook_url, json_body=payload)
    if not 200 <= response.status < 300:
        raise DiscordError(f"Discord webhook returned HTTP {response.status}")


def _truncate(text: str) -> str:
    if len(text) <= DESCRIPTION_LIMIT:
        return text
    return text[:TRUNCATE_AT] + TRUNCATED_NOTICE
