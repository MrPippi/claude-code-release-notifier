# Public Self-Host Restructure — Design

Date: 2026-10-09
Status: Approved (user directive: "依照建議持續執行到完成")

## Goal

Turn the repo into a project others can **fork and self-host**: no personal state in
`main`, behaviour configured through repository variables, logic testable outside
GitHub Actions, and the usual public-repo hygiene.

## Decisions

| Topic | Decision |
|---|---|
| Audience | Fork / template self-hosting (not a Marketplace Action) |
| State | Orphan branch `notifier-state`, file `state.json`, written via Contents API with `GITHUB_TOKEN` |
| Logic | Python package `notifier/`; `anthropic` SDK for Claude, stdlib `urllib` for GitHub + Discord |
| Release selection | Every release newer than state, oldest first, capped per run; first run notifies only the newest |
| Scheduling | Hourly cron, gated by variable `NOTIFIER_ENABLED == 'true'` |
| Secrets | Repository secrets (no Environments) |

Deviation from the in-chat sketch: the original plan was "stdlib only". The Claude
API guidance requires the official SDK in Python projects, so `anthropic` is the one
pinned runtime dependency (`requirements.txt`). GitHub and Discord stay on `urllib`.

Deviation 2: the old marker (`v2.1.236`) is **not** migrated. 48 releases shipped
since then; migrating would backfill ~48 Discord posts. Without state, the first run
posts only the newest release and records it.

## Layout

```
.github/
  workflows/notify.yml      # cron + dispatch → python -m notifier
  workflows/ci.yml          # ruff + pytest (coverage ≥ 80%) + actionlint
  dependabot.yml            # github-actions + pip
  ISSUE_TEMPLATE/{bug_report,feature_request}.yml, config.yml
  PULL_REQUEST_TEMPLATE.md
notifier/
  __init__.py
  __main__.py   # wiring, exit codes
  config.py     # env → frozen Config, validation
  http.py       # urllib JSON helper: timeout, retry on 429/5xx
  releases.py   # Release dataclass, fetch + select_new
  state.py      # State dataclass, read/write on notifier-state branch
  prompts.py    # system + user prompt text (zh-TW)
  translate.py  # Claude call, refusal/max_tokens handling
  discord.py    # embed build, truncation, post
tests/          # one test module per notifier module
requirements.in → requirements.txt (pip-compile, hash-pinned) / requirements-dev.txt / pyproject.toml
README.md, docs/README.zh-TW.md, SECURITY.md, CONTRIBUTING.md, CHANGELOG.md
```

`.github/last-notified-tag` is deleted from `main`.

## Configuration

Secrets: `ANTHROPIC_API_KEY`, `DISCORD_WEBHOOK_URL` (required unless dry run).

Variables (all optional except the gate):

| Variable | Default | Meaning |
|---|---|---|
| `NOTIFIER_ENABLED` | unset | `true` enables the hourly schedule |
| `SOURCE_REPO` | `anthropics/claude-code` | `owner/name` to watch |
| `INCLUDE_PRERELEASES` | `true` | include pre-releases |
| `MAX_RELEASES_PER_RUN` | `5` | 1–20 |
| `CLAUDE_MODEL` | `claude-sonnet-5-5` | model ID |
| `STATE_BRANCH` | `notifier-state` | branch holding `state.json` |

`workflow_dispatch` input `dry_run` (boolean): print embeds, skip Discord + state write.
In dry run the Discord secret is not required.

Validation fails fast with a clear message: bad `owner/name`, non-integer or
out-of-range max, non-boolean flags, missing secrets.

## Data flow

1. `load_config(os.environ)` → `Config` (frozen).
2. `read_state(...)` → `State | None` from `STATE_BRANCH:state.json` (404 → `None`).
3. `fetch_releases(...)` → `GET /repos/{SOURCE_REPO}/releases?per_page=100&page=N`, paging
   (max 10 pages) until a release at or before the stored state appears; drafts dropped,
   pre-releases dropped unless enabled.
4. `select_new(releases, state, max)`:
   - `state is None` → `[newest]`
   - else releases with `(published_at, tag) > (state.last_published_at, state.last_tag)`,
     ascending, first `max`.
     Leftovers go out on later runs, so nothing is skipped.
5. Per release, in order: `translate` → `post_embed` → `write_state(release)`.
   State is written after each success so a mid-batch failure never re-sends earlier posts.
6. Exit 0 when all succeed or nothing is new; exit 1 on the first failure (state already
   reflects the last success).

State file:
```json
{"last_tag": "v2.1.295", "last_published_at": "2026-10-08T19:48:38Z", "updated_at": "..."}
```
Branch missing → created as an orphan via Git Data API (blob → tree → commit with no
parents → ref). File present → `PUT contents` with its `sha`.

## Translation

`client.beta.messages.create(model, max_tokens=16000, system, messages,
output_config={"effort": "medium"}, betas=["server-side-fallback-2026-07-01"],
fallbacks="default")`. Fallbacks are sent only for models that support the `"default"`
form (`claude-sonnet-5-5`, `claude-opus-5-5`, `claude-opus-5`, `claude-fable-5-1`).
`stop_reason == "refusal"` or `"max_tokens"` → `TranslationError`. Text = joined `text`
blocks; empty → `TranslationError`. SDK retries (429/5xx/connection) are left on.

## Discord

Embed matches today's look (author, colour by stable/pre-release, badge title, footer
with date + link). Description capped at 4096 chars: if longer, cut to 3900 and append
the "內容過長" notice. Non-2xx → `DiscordError`. 429 handled by `http.py` retry using
`retry_after`. The webhook URL is never logged.

## Workflows

`notify.yml`: `on: schedule (hourly) + workflow_dispatch(dry_run)`.
Job `if: github.event_name == 'workflow_dispatch' || vars.NOTIFIER_ENABLED == 'true'`.
`permissions: contents: write` (state branch only). `concurrency: notifier` (no
cancel). Actions pinned to commit SHAs. Steps: checkout → setup-python 3.12 with pip
cache → `pip install -r requirements.txt` → `python -m notifier`. Inputs reach the
script only through `env:` (no `${{ }}` inside `run:`).

`ci.yml`: on push to `main` and pull requests; `permissions: contents: read`; ruff
check + format check, pytest with `--cov-fail-under=80`, actionlint.

## Error handling

Custom exceptions per boundary (`ConfigError`, `HttpError`, `StateError`,
`TranslationError`, `DiscordError`). `__main__` catches them, prints
`::error::<message>` and exits 1. Unexpected exceptions propagate (traceback in logs).
Messages never include secrets.

## Testing

pytest, all network faked (fake `http` callable / fake Anthropic client injected).
Coverage ≥ 80% enforced in CI. Cases: config defaults/validation, selection (first run,
ordering, cap, prerelease filter, drafts), state read 404/ok and write create/update,
translation success/refusal/max_tokens/empty, Discord truncation/colour/error, main
happy path, dry run, mid-batch failure keeps earlier state.

## Docs & hygiene

README (en) + `docs/README.zh-TW.md` rewritten as a self-host guide: fork → secrets →
variables → dry run → enable. `SECURITY.md` (private vulnerability reporting),
`CONTRIBUTING.md` (dev setup, tests, commit style), `CHANGELOG.md` (this restructure as
2.0.0), issue/PR templates, Dependabot.

## Out of scope

Marketplace Action packaging, multiple target languages, multiple webhooks, other
chat platforms.
