# claude-code-release-notifier

[![CI](https://github.com/MrPippi/claude-code-release-notifier/actions/workflows/ci.yml/badge.svg)](https://github.com/MrPippi/claude-code-release-notifier/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](../LICENSE)

[English](../README.md) | [繁體中文](README.zh-TW.md) | **简体中文** | [日本語](README.ja.md) | [한국어](README.ko.md)

监控 [anthropics/claude-code](https://github.com/anthropics/claude-code) 的 Release，通过
Claude API 翻译更新日志（默认为繁体中文），再发送到 Discord 频道。整个流程运行在你自己 fork 的
GitHub Actions 上，不需要服务器，也不需要数据库。

## 工作原理

Workflow 每小时运行一次：

1. 列出被监控仓库最近的 release。
2. 挑出上次通知之后发布的所有 release，从旧到新排序，最多 `MAX_RELEASES_PER_RUN` 个。
3. 逐一用 Claude 翻译，再以 embed 格式发送到 Discord。
4. 把已通知的版本记录在 `notifier-state` 分支的 `state.json` 中。

首次运行时还没有任何状态，所以只会通知最新的一个版本，不会把历史版本全部补发。状态存放在
独立的分支上，通知不会在 `main` 产生任何 commit。

## 部署你自己的副本

你需要一个 [Anthropic API Key](https://console.anthropic.com/)，以及一个你有权限创建
Webhook 的 Discord 频道。

### 1. Fork 这个仓库

点击 **Fork**，然后在你 fork 的 **Actions** 标签页启用 workflows。

### 2. 创建 Discord Webhook

在 Discord 中打开频道的 **编辑频道 → 整合（Integrations）→ Webhook**，点击
**新 Webhook**，复制它的 URL。

### 3. 设置 Secrets

在你 fork 的 **Settings → Secrets and variables → Actions → Secrets** 中添加：

| Secret | 值 |
|---|---|
| `ANTHROPIC_API_KEY` | 你的 Anthropic API Key |
| `DISCORD_WEBHOOK_URL` | 第 2 步复制的 Webhook URL |

也可以使用 GitHub CLI：

```bash
gh secret set ANTHROPIC_API_KEY -R <你的账号>/claude-code-release-notifier
gh secret set DISCORD_WEBHOOK_URL -R <你的账号>/claude-code-release-notifier
```

### 4. 先试运行（dry run）

打开 **Actions → Release Notifier → Run workflow**，保持 **dry_run** 勾选后运行。日志会
显示最新版本翻译后的 embed 内容，但不会发送到 Discord，也不会保存状态。

### 5. 启用定时任务

在 **Settings → Secrets and variables → Actions → Variables** 中添加 `NOTIFIER_ENABLED`，
值设为 `true`。之后每小时的定时任务就会自动发布新版本。要暂停的话，删除这个 variable 或改成
其他值即可。

## 配置项

除了定时任务需要的 `NOTIFIER_ENABLED`，其他 variable 都可以不设置。留空则使用默认值。

| Variable | 默认值 | 说明 |
|---|---|---|
| `NOTIFIER_ENABLED` | （未设置） | 设为 `true` 才会启用每小时定时任务 |
| `SOURCE_REPO` | `anthropics/claude-code` | 要监控的仓库，格式为 `owner/name` |
| `INCLUDE_PRERELEASES` | `true` | 是否也通知 pre-release |
| `MAX_RELEASES_PER_RUN` | `5` | 每次运行最多通知几个版本（1–20），超出的留到下次 |
| `CLAUDE_MODEL` | `claude-sonnet-5-5` | 翻译使用的 Claude 模型 |
| `STATE_BRANCH` | `notifier-state` | 存放 `state.json` 的分支 |
| `TARGET_LANGUAGE` | `zh-TW` | 翻译的目标语言：`zh-TW`（繁体中文）、`zh-CN`（简体中文）、`ja`（日语）或 `ko`（韩语） |

想添加其他语言，在 [`notifier/locales.py`](../notifier/locales.py) 中添加一条语言名称和
Discord 标签文字即可。

## 费用

公开仓库使用 GitHub Actions 免费。每通知一个版本会调用一次 Claude API，费用计入你的
Anthropic 账户；没有新版本的运行不会调用 Claude。

## 故障排查

| 现象 | 原因与解决方法 |
|---|---|
| `::error::ANTHROPIC_API_KEY is required but not set` | 补上 secret（第 3 步） |
| `::error::DISCORD_WEBHOOK_URL is required but not set` | 补上 secret，或使用 **dry_run** 运行 |
| `Creating state branch (...) failed with HTTP 403` | Workflow 拿不到 `contents: write` 权限。确认 `notify.yml` 仍声明了这个权限，且组织策略没有在 **Settings → Actions → General → Workflow permissions** 中把 token 限制为只读 |
| 定时任务没有运行 | 确认 `NOTIFIER_ENABLED` 为 `true`。仓库超过 60 天没有活动时 GitHub 也会暂停定时任务，在 Actions 标签页重新启用即可 |
| 想重新通知某个版本 | 修改或删除 `notifier-state` 分支上的 `state.json`。删除后下次运行只会通知最新的一个版本 |

## 开发

请参考 [CONTRIBUTING.md](../CONTRIBUTING.md)。简要步骤：

```bash
pip install --require-hashes -r requirements.txt -r requirements-dev.txt
ruff check . && ruff format --check .
pytest --cov=notifier
```

## 安全

发现漏洞请按照 [SECURITY.md](../SECURITY.md) 私下报告。

## 许可证

[MIT](../LICENSE)
