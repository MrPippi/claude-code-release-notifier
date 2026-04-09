# claude-code-release-notifier

![GitHub Actions](https://github.com/MrPippi/claude-code-release-notifier/actions/workflows/release-notifier.yml/badge.svg)

## Overview

Monitors [anthropics/claude-code](https://github.com/anthropics/claude-code) releases (both stable and pre-release), translates release notes into Traditional Chinese via the Claude API, and sends formatted notifications to a Discord channel.

## Features

- Monitors both stable and pre-release versions
- Translates release notes to Traditional Chinese via Claude API
- Sends formatted Discord Embed with Anthropic branding
- Skips duplicate notifications using GitHub Repository Variables
- Supports manual trigger via `workflow_dispatch`

## Prerequisites

- Anthropic API Key
- Discord Webhook URL
- GitHub repository with Actions enabled

## Setup

### Step 1: Fork or clone this repository

```bash
git clone https://github.com/<OWNER>/claude-code-release-notifier.git
```

### Step 2: Set Repository Secrets

Go to **Settings > Secrets and variables > Actions > Secrets** and add:

| Secret | Description |
|--------|-------------|
| `ANTHROPIC_API_KEY` | Your Anthropic API key |
| `DISCORD_WEBHOOK_URL` | Your Discord channel webhook URL |

### Step 3: Set Repository Variables

Go to **Settings > Secrets and variables > Actions > Variables** and add:

| Variable | Description |
|----------|-------------|
| `LAST_NOTIFIED_TAG` | Leave empty for initial setup |

### Step 4: Enable GitHub Actions

Go to **Actions** tab and enable workflows for this repository.

## Discord Webhook Setup

1. Open your Discord server and navigate to the target channel
2. Click **Edit Channel** (gear icon) > **Integrations** > **Webhooks**
3. Click **New Webhook**, give it a name, and copy the webhook URL
4. Paste the URL into the `DISCORD_WEBHOOK_URL` repository secret

## License

This project is licensed under the [MIT License](LICENSE).

---

[繁體中文說明](docs/README.zh-TW.md)
