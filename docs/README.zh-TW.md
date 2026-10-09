# claude-code-release-notifier

[![CI](https://github.com/MrPippi/claude-code-release-notifier/actions/workflows/ci.yml/badge.svg)](https://github.com/MrPippi/claude-code-release-notifier/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](../LICENSE)

[English](../README.md)

監控 [anthropics/claude-code](https://github.com/anthropics/claude-code) 的 Release，透過
Claude API 把更新日誌翻譯成繁體中文，再發送到 Discord 頻道。整個流程跑在你自己 fork 的
GitHub Actions 上，不需要伺服器，也不需要資料庫。

## 運作方式

Workflow 每小時執行一次：

1. 列出被監控 repo 最近的 release。
2. 挑出上次通知之後發布的所有 release，從舊到新排序，最多 `MAX_RELEASES_PER_RUN` 個。
3. 逐一用 Claude 翻譯，再以 embed 格式發到 Discord。
4. 把已通知的版本記錄在 `notifier-state` branch 的 `state.json`。

第一次執行時還沒有任何狀態，所以只會通知最新的一版，不會把歷史版本全部補發。狀態存在
獨立的 branch，通知不會在 `main` 產生任何 commit。

## 架設自己的版本

你需要一把 [Anthropic API Key](https://console.anthropic.com/)，以及一個你有權限建立
Webhook 的 Discord 頻道。

### 1. Fork 這個 repo

按 **Fork**，然後到你 fork 的 **Actions** 分頁啟用 workflows。

### 2. 建立 Discord Webhook

在 Discord 打開頻道的 **編輯頻道 → 整合 → Webhook**，按 **新 Webhook**，複製它的 URL。

### 3. 設定 Secrets

到你 fork 的 **Settings → Secrets and variables → Actions → Secrets**，新增：

| Secret | 值 |
|---|---|
| `ANTHROPIC_API_KEY` | 你的 Anthropic API Key |
| `DISCORD_WEBHOOK_URL` | 步驟 2 複製的 Webhook URL |

也可以用 GitHub CLI：

```bash
gh secret set ANTHROPIC_API_KEY -R <你的帳號>/claude-code-release-notifier
gh secret set DISCORD_WEBHOOK_URL -R <你的帳號>/claude-code-release-notifier
```

### 4. 先試跑（dry run）

打開 **Actions → Release Notifier → Run workflow**，保持 **dry_run** 勾選後執行。Log 會
顯示最新版本翻譯後的 embed 內容，但不會發到 Discord，也不會儲存狀態。

### 5. 啟用排程

到 **Settings → Secrets and variables → Actions → Variables**，新增 `NOTIFIER_ENABLED`，
值設為 `true`。之後每小時的排程就會自動發布新版本。要暫停的話，刪掉這個 variable 或改成
其他值即可。

## 設定項目

除了排程需要的 `NOTIFIER_ENABLED`，其他 variable 都可以不設。留空就使用預設值。

| Variable | 預設值 | 說明 |
|---|---|---|
| `NOTIFIER_ENABLED` | （未設定） | 設為 `true` 才會啟用每小時排程 |
| `SOURCE_REPO` | `anthropics/claude-code` | 要監控的 repo，格式為 `owner/name` |
| `INCLUDE_PRERELEASES` | `true` | 是否也通知 pre-release |
| `MAX_RELEASES_PER_RUN` | `5` | 每次執行最多通知幾個版本（1–20），超過的留到下次 |
| `CLAUDE_MODEL` | `claude-sonnet-5-5` | 翻譯使用的 Claude 模型 |
| `STATE_BRANCH` | `notifier-state` | 存放 `state.json` 的 branch |

想翻成其他語言，修改 [`notifier/prompts.py`](../notifier/prompts.py) 的 prompt 和
[`notifier/discord.py`](../notifier/discord.py) 的標籤文字即可。

## 費用

公開 repo 使用 GitHub Actions 免費。每通知一個版本會呼叫一次 Claude API，費用計入你的
Anthropic 帳戶；沒有新版本的執行不會呼叫 Claude。

## 疑難排解

| 狀況 | 原因與解法 |
|---|---|
| `::error::ANTHROPIC_API_KEY is required but not set` | 補上 secret（步驟 3） |
| `::error::DISCORD_WEBHOOK_URL is required but not set` | 補上 secret，或用 **dry_run** 執行 |
| `Creating state branch (...) failed with HTTP 403` | Workflow 拿不到 `contents: write` 權限。確認 `notify.yml` 仍有宣告這個權限，且組織政策沒有在 **Settings → Actions → General → Workflow permissions** 把 token 限制為唯讀 |
| 排程沒有執行 | 確認 `NOTIFIER_ENABLED` 為 `true`。repo 超過 60 天沒有活動時 GitHub 也會暫停排程，到 Actions 分頁重新啟用即可 |
| 想重新通知某個版本 | 修改或刪除 `notifier-state` branch 上的 `state.json`。刪除後下次執行只會通知最新的一版 |

## 開發

請參考 [CONTRIBUTING.md](../CONTRIBUTING.md)。簡要步驟：

```bash
pip install --require-hashes -r requirements.txt -r requirements-dev.txt
ruff check . && ruff format --check .
pytest --cov=notifier
```

## 安全性

發現漏洞請依 [SECURITY.md](../SECURITY.md) 私下回報。

## 授權

[MIT](../LICENSE)
