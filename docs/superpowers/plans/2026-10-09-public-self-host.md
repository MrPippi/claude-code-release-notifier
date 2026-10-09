# Public Self-Host Restructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the inline-shell workflow with a tested Python package that forks can configure through repository variables and that keeps its state on an orphan branch.

**Architecture:** `notifier/` holds one module per boundary (config, http, releases, state, translate, discord) wired by `__main__`. Every module takes its I/O as an injected callable/client so tests run offline. The workflow only installs deps and runs `python -m notifier`.

**Tech Stack:** Python 3.12 (CI/runtime), `anthropic==1.12.1`, stdlib `urllib`, pytest 9 + pytest-cov, ruff, actionlint.

**Spec:** `docs/superpowers/specs/2026-10-09-public-self-host-design.md`

**Execution:** Native (user directive: continue to completion without pauses).

## Global Constraints

- Runtime deps: only `anthropic==1.12.1` (`requirements.txt`).
- Default model `claude-sonnet-5-5`; fallbacks `"default"` + beta `server-side-fallback-2026-07-01` only for `claude-sonnet-5-5`, `claude-opus-5-5`, `claude-opus-5`, `claude-fable-5-1`.
- `MAX_RELEASES_PER_RUN` range 1–20, default 5. `STATE_BRANCH` default `notifier-state`.
- Discord description ≤ 4096 chars; cut at 3900 + notice when longer.
- All dataclasses `frozen=True`; no in-place mutation of inputs.
- No `${{ }}` expressions inside `run:` blocks; actions pinned by SHA
  (`actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1` v7.0.1,
  `actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97` v7.0.0).
- Coverage ≥ 80% (`--cov-fail-under=80`).
- Secrets never appear in log or exception text.

## Review Focus

1. Release body `null`/empty from GitHub → translate a placeholder-free prompt, not crash (test in Task 3/5).
2. Two releases with identical `published_at` → both picked, stable order by tag (Task 3).
3. State branch exists but `state.json` missing / malformed JSON → treat missing as `None`, malformed as `StateError` (Task 4).
4. Translation contains Markdown longer than 4096 chars incl. multi-byte chars → truncation by characters, never mid-surrogate (Task 6).
5. Discord 429 with `retry_after` → retried once by `http.py`, then success (Task 2).

---

### Task 1: Project scaffold + config

**Files:** Create `pyproject.toml`, `requirements.txt`, `requirements-dev.txt`, `notifier/__init__.py`, `notifier/config.py`, `tests/test_config.py`.

**Interfaces — Produces:**
- `class ConfigError(Exception)`
- `@dataclass(frozen=True) class Config: source_repo: str; include_prereleases: bool; max_releases: int; model: str; state_branch: str; repository: str; github_token: str; anthropic_api_key: str; discord_webhook_url: str; dry_run: bool`
- `def load_config(env: Mapping[str, str]) -> Config`

Env names: `SOURCE_REPO`, `INCLUDE_PRERELEASES`, `MAX_RELEASES_PER_RUN`, `CLAUDE_MODEL`, `STATE_BRANCH`, `GITHUB_REPOSITORY`, `GITHUB_TOKEN`, `ANTHROPIC_API_KEY`, `DISCORD_WEBHOOK_URL`, `DRY_RUN`. Empty string = unset (Actions passes unset vars as `""`).

Tests: defaults; overrides; bool parsing (`true/false/1/0/yes/no`, case-insensitive) and rejection; max non-int / 0 / 21 rejected; bad repo format rejected; missing `GITHUB_REPOSITORY`/`GITHUB_TOKEN`/`ANTHROPIC_API_KEY` rejected; `DISCORD_WEBHOOK_URL` required unless dry run; error message never contains secret values.

- [ ] Write tests → run (FAIL) → implement → run (PASS) → ruff → commit `feat: add notifier config loading`

### Task 2: HTTP helper

**Files:** Create `notifier/http.py`, `tests/test_http.py`.

**Interfaces — Produces:**
- `class HttpError(Exception)` with `.status: int | None`
- `@dataclass(frozen=True) class Response: status: int; body: bytes` + `def json(self) -> Any`
- `Transport = Callable[[urllib.request.Request, float], Response]` (default uses `urlopen`; `HTTPError` converted to `Response`)
- `def request(method, url, *, headers=None, json_body=None, transport=default_transport, sleep=time.sleep, retries=3, timeout=30.0) -> Response` — retries 429 (honours `retry_after` JSON field or `Retry-After`… body field only, capped 60s) and 5xx with backoff `2**attempt`; returns non-retryable responses as-is (caller decides); raises `HttpError` after retries exhausted or on `URLError`.

Tests: success passthrough; JSON body encoded + content-type set; 500→500→200 retried with sleeps 1,2; 429 with `retry_after: 1.5` sleeps 1.5; 404 returned without retry; exhaustion raises `HttpError(status=503)`; URLError raises `HttpError(status=None)`.

- [ ] TDD cycle → commit `feat: add http helper with retry`

### Task 3: Releases

**Files:** Create `notifier/releases.py`, `tests/test_releases.py`.

**Interfaces — Produces:**
- `@dataclass(frozen=True) class Release: tag: str; name: str; body: str; url: str; published_at: str; prerelease: bool`
- `def parse_releases(items: list[dict], include_prereleases: bool) -> list[Release]` (drops drafts and items without `published_at`; `body None → ""`)
- `def fetch_releases(source_repo, token, include_prereleases, *, http=request) -> list[Release]`
- `def select_new(releases, last_published_at: str | None, max_releases: int) -> list[Release]` — ascending by `(published_at, tag)`; `None` → `[newest]`; empty list → `[]`.

Tests: draft dropped; prerelease filtered/kept; null body; first run picks newest only; strictly-newer filter; ordering oldest→newest; cap keeps oldest N; identical timestamps both selected; fetch sends auth header and raises `HttpError` on non-200.

- [ ] TDD cycle → commit `feat: add release fetching and selection`

### Task 4: State branch

**Files:** Create `notifier/state.py`, `tests/test_state.py`.

**Interfaces — Produces:**
- `class StateError(Exception)`
- `@dataclass(frozen=True) class State: last_tag: str; last_published_at: str; updated_at: str`
- `def read_state(repository, branch, token, *, http=request) -> State | None` — `GET contents/state.json?ref=branch`; 404 → `None`; malformed → `StateError`.
- `def write_state(repository, branch, token, state, *, http=request) -> None` — get file sha (404 = none); if branch missing (`GET git/ref/heads/{branch}` 404) create orphan: `POST git/blobs` → `POST git/trees` → `POST git/commits` (no parents) → `POST git/refs`; else `PUT contents/state.json` with `branch` and optional `sha`.
- `def state_from_release(release, now: str) -> State`

Tests: read ok (base64 decode); read 404; read malformed; write update with sha; write create file on existing branch (no sha); write creates orphan branch (asserts 4 POST calls, commit has `parents: []`); non-2xx raises `StateError`.

- [ ] TDD cycle → commit `feat: store notifier state on orphan branch`

### Task 5: Translation

**Files:** Create `notifier/prompts.py`, `notifier/translate.py`, `tests/test_translate.py`.

**Interfaces — Produces:**
- `SYSTEM_PROMPT: str`, `def build_user_prompt(release: Release) -> str` (from current workflow text)
- `class TranslationError(Exception)`
- `def translate(release, model, *, client) -> str` — `client.beta.messages.create(...)` per spec; fallbacks only for supported models; refusal / max_tokens / empty → `TranslationError`; joins `text` blocks.
- `def make_client(api_key: str) -> anthropic.Anthropic`

Tests (fake client recording kwargs, returning `SimpleNamespace`): success joins text blocks and skips non-text; refusal; max_tokens; empty text; fallbacks present for sonnet-5-5 and absent for `claude-haiku-5-5`; prompt includes tag, release type label, date, body; empty body still builds prompt.

- [ ] TDD cycle → commit `feat: translate release notes with Claude`

### Task 6: Discord

**Files:** Create `notifier/discord.py`, `tests/test_discord.py`.

**Interfaces — Produces:**
- `class DiscordError(Exception)`
- `def build_payload(release: Release, translated: str) -> dict`
- `def post_embed(webhook_url, payload, *, http=request) -> None` — 2xx ok, else `DiscordError` (message has status only, never URL).

Tests: stable colour 16744272 + `🚀 正式版`; prerelease colour 16776960 + `🧪 Pre-release`; ≤4096 untouched; >4096 cut to 3900 + notice and final length ≤ 4096; multi-byte string truncation by characters; footer contains date + url; post 204 ok; post 400 raises without URL in message.

- [ ] TDD cycle → commit `feat: build and post Discord embeds`

### Task 7: Main wiring

**Files:** Create `notifier/__main__.py`, `tests/test_main.py`.

**Interfaces — Produces:**
- `def run(config, *, http=request, client=None, now=utc_now, log=print) -> int`
- `def main() -> int` (loads config from `os.environ`, catches known errors → `::error::` + 1)

Tests: nothing new → 0, no posts; two new → two posts, two state writes in order; dry run → no post, no state write, payload logged; failure on 2nd release → exit 1, state written once (1st release); `main()` maps `ConfigError` to exit 1 with `::error::`.

- [ ] TDD cycle → commit `feat: wire notifier entrypoint`

### Task 8: Workflows, repo hygiene, docs

**Files:** Replace `.github/workflows/release-notifier.yml` with `.github/workflows/notify.yml`; create `.github/workflows/ci.yml`, `.github/dependabot.yml`, `.github/ISSUE_TEMPLATE/{bug_report.yml,feature_request.yml,config.yml}`, `.github/PULL_REQUEST_TEMPLATE.md`, `SECURITY.md`, `CONTRIBUTING.md`, `CHANGELOG.md`; rewrite `README.md`, `docs/README.zh-TW.md`; delete `.github/last-notified-tag`.

- [ ] Write files per spec "Workflows" + "Docs & hygiene"
- [ ] Verify: `ruff check`, `ruff format --check`, `pytest --cov=notifier --cov-fail-under=80`, actionlint (via CI run)
- [ ] Commit `ci: replace inline workflow with python notifier` and `docs: rewrite README as self-host guide`

### Task 9: Ship

- [ ] Push `main`; confirm CI green (`gh run watch`)
- [ ] Enable private vulnerability reporting (`gh api -X PUT repos/{repo}/private-vulnerability-reporting`)
- [ ] Trigger `notify.yml` with `dry_run=true`; confirm it lists the newest release and exits 0 (secrets not yet set → Anthropic call would fail; dry run still translates, so expect failure until the user sets `ANTHROPIC_API_KEY` — record the outcome honestly)
- [ ] Final whole-branch review; report remaining user actions (set secrets, `NOTIFIER_ENABLED=true`)
