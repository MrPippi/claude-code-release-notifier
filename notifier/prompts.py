"""Prompt text for translating release notes into the configured language."""

from __future__ import annotations

from notifier.locales import Locale
from notifier.releases import Release

_SYSTEM_TEMPLATE = """You are a professional technical translator. You translate the English release notes of Anthropic's Claude Code into {language}.

Rules:
1. Write the translation in {language}.
2. Keep product names and technical terms in English, for example: MCP, SDK, API, CLI, Plugin, Webhook, Session, Artifact, Tool, Prompt, Token, Context, Workflow, Agent, Slash Command, CLAUDE.md.
3. Keep version numbers exactly as written (such as v2.1.76, beta, rc).
4. Preserve all Markdown formatting: heading levels, bullet points, code blocks and bold text.
5. Do not translate code blocks (content fenced with ```); output them unchanged.
6. Use a professional, natural tone suited to developers.
7. Do not add anything that is not in the original, and do not leave out any section.
8. When you are unsure how to translate a term, keep the English original instead of forcing a translation."""

EMPTY_BODY_TEXT = "(No release notes were provided for this version.)"


def build_system_prompt(locale: Locale) -> str:
    return _SYSTEM_TEMPLATE.format(language=locale.language)


def release_type_label(release: Release) -> str:
    return "Pre-release" if release.prerelease else "Stable"


def build_user_prompt(release: Release, locale: Locale) -> str:
    body = release.body.strip() or EMPTY_BODY_TEXT
    return f"""Translate the following Claude Code release notes into {locale.language}.

Version: {release.tag}
Release type: {release_type_label(release)}
Release date: {release.published_at[:10]}

<release_notes>
{body}
</release_notes>

Output only the {locale.language} translation, with all Markdown formatting preserved. Do not add any preface, explanation or notes."""
