"""Target languages: the name Claude translates into and the Discord labels for each.

To add a language, add a Locale to _ALL below and a test in tests/test_locales.py.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True)
class Locale:
    code: str
    # English name used in the prompt, e.g. "Japanese".
    language: str
    stable_badge: str
    prerelease_badge: str
    # Formatted with {date} (YYYY-MM-DD) and {url}.
    footer: str
    truncated_notice: str


_ALL = (
    Locale(
        code="zh-TW",
        language="Traditional Chinese (Taiwan)",
        stable_badge="🚀 正式版",
        prerelease_badge="🧪 Pre-release",
        footer="發布日期：{date}  •  查看原文 → {url}",
        truncated_notice="\n\n… （內容過長，請至原文連結閱讀完整內容）",
    ),
    Locale(
        code="zh-CN",
        language="Simplified Chinese (Mainland China)",
        stable_badge="🚀 正式版",
        prerelease_badge="🧪 预发布版",
        footer="发布日期：{date}  •  查看原文 → {url}",
        truncated_notice="\n\n… （内容过长，请前往原文链接阅读完整内容）",
    ),
    Locale(
        code="ja",
        language="Japanese",
        stable_badge="🚀 正式版",
        prerelease_badge="🧪 プレリリース",
        footer="公開日：{date}  •  原文を見る → {url}",
        truncated_notice="\n\n… （内容が長いため省略しました。全文は原文リンクからご覧ください）",
    ),
    Locale(
        code="ko",
        language="Korean",
        stable_badge="🚀 정식 버전",
        prerelease_badge="🧪 프리릴리스",
        footer="게시일: {date}  •  원문 보기 → {url}",
        truncated_notice="\n\n… (내용이 너무 길어 생략했습니다. 전체 내용은 원문 링크에서 확인하세요)",
    ),
)

LOCALES: Mapping[str, Locale] = MappingProxyType({locale.code: locale for locale in _ALL})
DEFAULT_LOCALE = "zh-TW"


def find_locale(code: str) -> Locale | None:
    """Look up a locale by code, ignoring case. Returns None when unsupported."""
    wanted = code.strip().lower()
    return next((locale for locale in _ALL if locale.code.lower() == wanted), None)
