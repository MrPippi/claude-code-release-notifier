# Security Policy

## Reporting a vulnerability

Please report vulnerabilities privately through
[GitHub private vulnerability reporting](https://github.com/MrPippi/claude-code-release-notifier/security/advisories/new).
Do not open a public issue.

Include what is affected, how to reproduce it, and the impact you expect. You should
get a first response within 7 days.

## Scope

In scope: code in `notifier/`, the workflows in `.github/workflows/`, and the
documented setup.

Out of scope: leaks caused by a fork owner's own configuration, such as committing
secrets or pasting webhook URLs into public issues.

## If a secret leaks

- **Discord webhook URL**: delete the webhook in Discord (Channel → Integrations →
  Webhooks), create a new one, and update the `DISCORD_WEBHOOK_URL` secret.
- **Anthropic API key**: revoke it in the Claude Console, create a new key, and update
  the `ANTHROPIC_API_KEY` secret.
