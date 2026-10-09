"""Translate release notes with the Claude API."""

from __future__ import annotations

from typing import Any

import anthropic

from notifier.locales import Locale
from notifier.prompts import build_system_prompt, build_user_prompt
from notifier.releases import Release

MAX_TOKENS = 16000
EFFORT = "medium"
FALLBACK_BETA = "server-side-fallback-2026-07-01"
# Models that accept the server-side `fallbacks: "default"` form.
FALLBACK_MODELS = frozenset(
    {"claude-sonnet-5-5", "claude-opus-5-5", "claude-opus-5", "claude-fable-5-1"}
)


class TranslationError(Exception):
    """Raised when Claude does not return a usable translation."""


def make_client(api_key: str) -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=api_key)


def translate(release: Release, model: str, *, locale: Locale, client: Any) -> str:
    request: dict[str, Any] = {
        "model": model,
        "max_tokens": MAX_TOKENS,
        "system": build_system_prompt(locale),
        "messages": [{"role": "user", "content": build_user_prompt(release, locale)}],
        "output_config": {"effort": EFFORT},
    }
    if model in FALLBACK_MODELS:
        request = {**request, "betas": [FALLBACK_BETA], "fallbacks": "default"}

    response = client.beta.messages.create(**request)

    if response.stop_reason in ("refusal", "max_tokens"):
        raise TranslationError(
            f"Claude stopped with stop_reason={response.stop_reason} for {release.tag}"
        )
    translated = "\n\n".join(
        block.text for block in response.content if block.type == "text"
    ).strip()
    if not translated:
        raise TranslationError(f"Claude returned empty text for {release.tag}")
    return translated
