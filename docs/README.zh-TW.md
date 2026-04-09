# claude-code-release-notifier

![GitHub Actions](https://github.com/MrPippi/claude-code-release-notifier/actions/workflows/release-notifier.yml/badge.svg)

## 概述

監控 [anthropics/claude-code](https://github.com/anthropics/claude-code) 的 Release 發布（包含 stable 與 pre-release），透過 Claude API 將更新日誌翻譯成繁體中文後，以 Discord Embed 格式發送至指定頻道。

## 功能特色

- 同時監控正式版與 Pre-release 版本
- 透過 Claude API 將更新日誌翻譯為繁體中文
- 以格式化的 Discord Embed 發送通知，包含 Anthropic 品牌識別
- 利用 GitHub Repository Variables 避免重複通知
- 支援透過 `workflow_dispatch` 手動觸發

## 前置需求

- Anthropic API Key
- Discord Webhook URL
- 已啟用 Actions 的 GitHub Repository

## 設定步驟

### 步驟一：Fork 或 Clone 此專案

```bash
git clone https://github.com/<OWNER>/claude-code-release-notifier.git
```

### 步驟二：設定 Repository Secrets

前往 **Settings > Secrets and variables > Actions > Secrets**，新增以下項目：

| Secret | 說明 |
|--------|------|
| `ANTHROPIC_API_KEY` | 你的 Anthropic API Key |
| `DISCORD_WEBHOOK_URL` | 你的 Discord 頻道 Webhook URL |

### 步驟三：設定 Repository Variables

前往 **Settings > Secrets and variables > Actions > Variables**，新增以下項目：

| Variable | 說明 |
|----------|------|
| `LAST_NOTIFIED_TAG` | 初始值留空即可 |

### 步驟四：啟用 GitHub Actions

前往 **Actions** 分頁，啟用此 Repository 的 Workflow。

## Discord Webhook 設定方式

1. 開啟你的 Discord 伺服器，進入目標頻道
2. 點選 **編輯頻道**（齒輪圖示）> **整合** > **Webhooks**
3. 點選 **新增 Webhook**，設定名稱後複製 Webhook URL
4. 將 URL 貼入 Repository Secret 的 `DISCORD_WEBHOOK_URL`

## 授權條款

本專案採用 [MIT License](../LICENSE) 授權。

---

[English](../README.md)
