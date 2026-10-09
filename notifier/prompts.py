"""Prompt text for translating release notes into Traditional Chinese.

Forks that want another language only need to edit this file.
"""

from __future__ import annotations

from notifier.releases import Release

SYSTEM_PROMPT = """你是一位專業的技術文件翻譯員，專門將 Anthropic Claude Code 的英文更新日誌翻譯成繁體中文。

翻譯規則：
1. 以繁體中文為主要語言
2. 專有名詞保留英文原文，例如：MCP、SDK、API、CLI、Plugin、Webhook、Session、Artifact、Tool、Prompt、Token、Context、Workflow、Agent、Slash Command、CLAUDE.md 等
3. 版本號完整保留（如 v2.1.76、beta、rc）
4. Markdown 格式完整保留（標題層級、bullet point、code block、粗體）
5. 程式碼區塊（``` 包覆的內容）不翻譯，原樣輸出
6. 翻譯語氣專業且自然，適合開發者閱讀
7. 不添加任何原文沒有的內容，不省略任何段落
8. 如遇到無法確認的專有名詞，優先保留英文而非強行翻譯"""

EMPTY_BODY_TEXT = "（此版本沒有提供更新說明）"


def release_type_label(release: Release) -> str:
    return "Pre-release（測試版）" if release.prerelease else "Stable（正式版）"


def build_user_prompt(release: Release) -> str:
    body = release.body.strip() or EMPTY_BODY_TEXT
    return f"""請將以下 Claude Code 更新日誌翻譯成繁體中文。

版本：{release.tag}
發布類型：{release_type_label(release)}
發布日期：{release.published_at[:10]}

---原文開始---
{body}
---原文結束---

輸出格式要求：
- 只輸出翻譯後的繁體中文內容
- 完整保留所有 Markdown 格式
- 不輸出任何前言、說明或備註"""
