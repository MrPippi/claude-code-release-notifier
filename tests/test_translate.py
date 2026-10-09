from types import SimpleNamespace
from typing import Any

import pytest

from notifier.locales import LOCALES
from notifier.prompts import build_system_prompt, build_user_prompt
from notifier.releases import Release
from notifier.translate import TranslationError, translate

RELEASE = Release(
    tag="v2.1.300",
    name="v2.1.300",
    body="- Fixed a bug in `/resume`",
    url="https://github.com/anthropics/claude-code/releases/tag/v2.1.300",
    published_at="2026-10-08T19:48:38Z",
    prerelease=False,
)
ZH_TW = LOCALES["zh-TW"]
JA = LOCALES["ja"]


def text(value: str) -> SimpleNamespace:
    return SimpleNamespace(type="text", text=value)


class FakeClient:
    def __init__(self, response: SimpleNamespace) -> None:
        self.kwargs: dict[str, Any] = {}
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))
        self._response = response

    def _create(self, **kwargs: Any) -> SimpleNamespace:
        self.kwargs = kwargs
        return self._response


def response(*blocks: SimpleNamespace, stop_reason: str = "end_turn") -> SimpleNamespace:
    return SimpleNamespace(content=list(blocks), stop_reason=stop_reason)


def test_translate_joins_text_blocks_and_skips_others() -> None:
    thinking = SimpleNamespace(type="thinking", thinking="")
    client = FakeClient(response(thinking, text("第一段"), text("第二段")))

    assert (
        translate(RELEASE, "claude-sonnet-5-5", locale=ZH_TW, client=client) == "第一段\n\n第二段"
    )


def test_translate_request_shape_with_fallbacks() -> None:
    client = FakeClient(response(text("ok")))

    translate(RELEASE, "claude-sonnet-5-5", locale=ZH_TW, client=client)

    kwargs = client.kwargs
    assert kwargs["model"] == "claude-sonnet-5-5"
    assert kwargs["system"] == build_system_prompt(ZH_TW)
    assert kwargs["messages"] == [{"role": "user", "content": build_user_prompt(RELEASE, ZH_TW)}]
    assert kwargs["output_config"] == {"effort": "medium"}
    assert kwargs["fallbacks"] == "default"
    assert kwargs["betas"] == ["server-side-fallback-2026-07-01"]


def test_translate_omits_fallbacks_for_unsupported_model() -> None:
    client = FakeClient(response(text("ok")))

    translate(RELEASE, "claude-haiku-5-5", locale=ZH_TW, client=client)

    assert "fallbacks" not in client.kwargs
    assert "betas" not in client.kwargs


@pytest.mark.parametrize("stop_reason", ["refusal", "max_tokens"])
def test_translate_rejects_bad_stop_reason(stop_reason: str) -> None:
    client = FakeClient(response(text("partial"), stop_reason=stop_reason))

    with pytest.raises(TranslationError, match=stop_reason):
        translate(RELEASE, "claude-sonnet-5-5", locale=ZH_TW, client=client)


def test_translate_rejects_empty_text() -> None:
    client = FakeClient(response(text("   ")))

    with pytest.raises(TranslationError, match="empty"):
        translate(RELEASE, "claude-sonnet-5-5", locale=ZH_TW, client=client)


def test_translate_uses_requested_language() -> None:
    client = FakeClient(response(text("ok")))

    translate(RELEASE, "claude-sonnet-5-5", locale=JA, client=client)

    assert "Japanese" in client.kwargs["system"]
    assert "Japanese" in client.kwargs["messages"][0]["content"]


def test_system_prompt_names_language() -> None:
    prompt = build_system_prompt(ZH_TW)

    assert "Traditional Chinese (Taiwan)" in prompt
    assert "Markdown" in prompt


def test_user_prompt_contains_release_details() -> None:
    prompt = build_user_prompt(RELEASE, ZH_TW)

    assert "Traditional Chinese (Taiwan)" in prompt
    assert "v2.1.300" in prompt
    assert "Release type: Stable" in prompt
    assert "2026-10-08" in prompt
    assert "- Fixed a bug in `/resume`" in prompt


def test_user_prompt_marks_prerelease() -> None:
    prerelease = Release("v3-beta", "v3-beta", "x", "u", "2026-10-08T00:00:00Z", True)

    assert "Release type: Pre-release" in build_user_prompt(prerelease, ZH_TW)


def test_user_prompt_with_empty_body() -> None:
    empty = Release("v1", "v1", "", "u", "2026-10-08T00:00:00Z", False)

    assert "(No release notes were provided for this version.)" in build_user_prompt(empty, ZH_TW)
