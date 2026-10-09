# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [2.0.0] - 2026-10-09

The notifier was rebuilt so anyone can fork and run their own copy.

### Added

- Python package `notifier/` with tests (coverage ≥ 80%) replacing the inline shell
  workflow.
- Configuration through repository variables: `SOURCE_REPO`, `INCLUDE_PRERELEASES`,
  `MAX_RELEASES_PER_RUN`, `CLAUDE_MODEL`, `STATE_BRANCH`.
- `NOTIFIER_ENABLED` gate for the hourly schedule.
- `dry_run` option for manual runs.
- Catch-up: every release published since the last run is announced, oldest first,
  following pagination when the backlog is long.
- Hash-pinned runtime dependencies (`requirements.in` → `requirements.txt`).
- GET requests retry network errors and timeouts.
- Refusal fallback (`fallbacks: "default"`) for supported Claude models.
- CI (ruff, pytest, actionlint), Dependabot, issue and PR templates, `SECURITY.md`,
  `CONTRIBUTING.md`.

### Changed

- State moved from `.github/last-notified-tag` on `main` to `state.json` on the orphan
  branch `notifier-state`. Notifications no longer add commits to `main`.
- Secrets are plain repository secrets instead of GitHub Environments.
- Default model is now `claude-sonnet-5-5` (was `claude-sonnet-4-6`).
- Pre-releases are actually included. The old workflow used `/releases/latest`, which
  never returns pre-releases.

### Removed

- `LAST_NOTIFIED_TAG` repository variable and the per-secret Environments.

## [1.0.0] - 2026-04-10

- Initial shell-based GitHub Actions workflow.
