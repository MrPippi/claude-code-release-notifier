import pytest

from notifier.locales import DEFAULT_LOCALE, LOCALES, find_locale


def test_default_is_traditional_chinese() -> None:
    assert DEFAULT_LOCALE == "zh-TW"
    assert LOCALES[DEFAULT_LOCALE].language == "Traditional Chinese (Taiwan)"


@pytest.mark.parametrize("code", ["zh-TW", "zh-CN", "ja", "ko"])
def test_builtin_locales(code: str) -> None:
    locale = LOCALES[code]

    assert locale.code == code
    assert "{date}" in locale.footer
    assert "{url}" in locale.footer


@pytest.mark.parametrize(("raw", "expected"), [("zh-tw", "zh-TW"), ("JA", "ja"), ("Ko", "ko")])
def test_find_locale_ignores_case(raw: str, expected: str) -> None:
    locale = find_locale(raw)

    assert locale is not None
    assert locale.code == expected


def test_find_locale_unknown() -> None:
    assert find_locale("fr") is None


def test_locales_are_read_only() -> None:
    with pytest.raises(TypeError):
        LOCALES["fr"] = LOCALES["ja"]  # type: ignore[index]
