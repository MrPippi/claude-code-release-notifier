# claude-code-release-notifier

[![CI](https://github.com/MrPippi/claude-code-release-notifier/actions/workflows/ci.yml/badge.svg)](https://github.com/MrPippi/claude-code-release-notifier/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

[繁體中文說明](docs/README.zh-TW.md)

Watches [anthropics/claude-code](https://github.com/anthropics/claude-code) releases,
translates the release notes into Traditional Chinese with the Claude API, and posts them
to a Discord channel. It runs entirely on GitHub Actions in your own fork: no server, no
database.

## How it works

Every hour the workflow:

1. Lists recent releases of the watched repository.
2. Picks every release published since the last one it announced, oldest first, up to
   `MAX_RELEASES_PER_RUN`.
3. Translates each one with Claude and posts it to Discord as an embed.
4. Records the release in `state.json` on the `notifier-state` branch.

The first run has no previous state, so it posts only the newest release instead of the
whole history. State lives on its own branch, so notifications never add commits to `main`.

## Set up your own copy

You need an [Anthropic API key](https://console.anthropic.com/) and a Discord channel
where you can create webhooks.

### 1. Fork this repository

Click **Fork**, then open the **Actions** tab of your fork and enable workflows.

### 2. Create a Discord webhook

In Discord, open the channel's **Edit Channel → Integrations → Webhooks**, click
**New Webhook**, and copy its URL.

### 3. Add secrets

In your fork go to **Settings → Secrets and variables → Actions → Secrets** and add:

| Secret | Value |
|---|---|
| `ANTHROPIC_API_KEY` | Your Anthropic API key |
| `DISCORD_WEBHOOK_URL` | The webhook URL from step 2 |

Or with the GitHub CLI:

```bash
gh secret set ANTHROPIC_API_KEY -R <you>/claude-code-release-notifier
gh secret set DISCORD_WEBHOOK_URL -R <you>/claude-code-release-notifier
```

### 4. Do a dry run

Open **Actions → Release Notifier → Run workflow**, leave **dry_run** checked, and run
it. The log shows the translated embed for the newest release. Nothing is posted and no
state is saved.

### 5. Turn it on

Under **Settings → Secrets and variables → Actions → Variables**, add
`NOTIFIER_ENABLED` with the value `true`. The hourly schedule now posts new releases.
To pause it, delete the variable or set it to anything else.

## Configuration

All variables are optional except `NOTIFIER_ENABLED`, which is needed for scheduled
runs. Empty values use the default.

| Variable | Default | Description |
|---|---|---|
| `NOTIFIER_ENABLED` | *(unset)* | `true` enables the hourly schedule |
| `SOURCE_REPO` | `anthropics/claude-code` | Repository to watch, as `owner/name` |
| `INCLUDE_PRERELEASES` | `true` | Also announce pre-releases |
| `MAX_RELEASES_PER_RUN` | `5` | Most releases announced per run (1–20). Any extra go out on the next run |
| `CLAUDE_MODEL` | `claude-sonnet-5-5` | Claude model used for translation |
| `STATE_BRANCH` | `notifier-state` | Branch that stores `state.json` |

To translate into another language, edit the prompts in
[`notifier/prompts.py`](notifier/prompts.py) and the labels in
[`notifier/discord.py`](notifier/discord.py).

## Costs

GitHub Actions is free for public repositories. Each announced release is one Claude API
request, billed to your Anthropic account. Runs with no new release don't call Claude.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `::error::ANTHROPIC_API_KEY is required but not set` | Add the secret (step 3) |
| `::error::DISCORD_WEBHOOK_URL is required but not set` | Add the secret, or run with **dry_run** |
| `Creating state branch (...) failed with HTTP 403` | The workflow could not get `contents: write`. Check that `notify.yml` still requests it, and that no organization policy under **Settings → Actions → General → Workflow permissions** limits tokens to read-only |
| Scheduled runs are skipped | Set `NOTIFIER_ENABLED` to `true`. GitHub also pauses schedules in repositories with no activity for 60 days; re-enable the workflow in the Actions tab |
| You want to re-announce a release | Edit or delete `state.json` on the `notifier-state` branch. Deleting it makes the next run announce only the newest release |

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md). In short:

```bash
pip install --require-hashes -r requirements.txt -r requirements-dev.txt
ruff check . && ruff format --check .
pytest --cov=notifier
```

## Security

Report vulnerabilities privately as described in [SECURITY.md](SECURITY.md).

## License

[MIT](LICENSE)
