# claude-code-release-notifier

[![CI](https://github.com/MrPippi/claude-code-release-notifier/actions/workflows/ci.yml/badge.svg)](https://github.com/MrPippi/claude-code-release-notifier/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](../LICENSE)

[English](../README.md) | [繁體中文](README.zh-TW.md) | [简体中文](README.zh-CN.md) | [日本語](README.ja.md) | **한국어**

[anthropics/claude-code](https://github.com/anthropics/claude-code)의 릴리스를 감시하고,
Claude API로 릴리스 노트를 번역해(기본값은 번체 중국어) Discord 채널에 게시합니다. 모든 작업이
여러분의 fork에 있는 GitHub Actions에서 실행되므로 서버나 데이터베이스가 필요 없습니다.

## 동작 방식

Workflow는 1시간마다 다음을 수행합니다.

1. 감시 대상 저장소의 최근 릴리스를 가져옵니다.
2. 마지막으로 알린 릴리스 이후에 게시된 릴리스를 오래된 순으로 최대 `MAX_RELEASES_PER_RUN`개
   고릅니다.
3. 각각을 Claude로 번역하고 Discord에 embed로 게시합니다.
4. 알린 릴리스를 `notifier-state` 브랜치의 `state.json`에 기록합니다.

첫 실행에는 이전 상태가 없으므로 전체 기록이 아니라 최신 릴리스 하나만 게시합니다. 상태는
별도 브랜치에 저장되므로 알림 때문에 `main`에 커밋이 추가되지 않습니다.

## 직접 설정하기

[Anthropic API 키](https://console.anthropic.com/)와 Webhook을 만들 수 있는 Discord
채널이 필요합니다.

### 1. 이 저장소를 fork하기

**Fork**를 클릭한 다음, fork한 저장소의 **Actions** 탭에서 workflows를 활성화합니다.

### 2. Discord Webhook 만들기

Discord에서 채널의 **채널 편집 → 연동 (Integrations) → 웹후크**를 열고 **새 웹후크**를
클릭한 뒤 URL을 복사합니다.

### 3. Secrets 추가하기

fork한 저장소의 **Settings → Secrets and variables → Actions → Secrets**에서 다음을
추가합니다.

| Secret | 값 |
|---|---|
| `ANTHROPIC_API_KEY` | Anthropic API 키 |
| `DISCORD_WEBHOOK_URL` | 2단계에서 복사한 Webhook URL |

GitHub CLI를 사용하는 경우:

```bash
gh secret set ANTHROPIC_API_KEY -R <사용자명>/claude-code-release-notifier
gh secret set DISCORD_WEBHOOK_URL -R <사용자명>/claude-code-release-notifier
```

### 4. 드라이 런으로 테스트하기

**Actions → Release Notifier → Run workflow**를 열고 **dry_run**을 체크한 상태로
실행합니다. 로그에 최신 릴리스의 번역된 embed가 표시됩니다. Discord에 게시하지 않으며
상태도 저장하지 않습니다.

### 5. 활성화하기

**Settings → Secrets and variables → Actions → Variables**에서 `NOTIFIER_ENABLED`를
추가하고 값을 `true`로 설정합니다. 이제 1시간마다 새 릴리스가 게시됩니다. 일시 중지하려면
이 variable을 삭제하거나 다른 값으로 바꾸세요.

## 설정

스케줄 실행에 필요한 `NOTIFIER_ENABLED` 외의 variable은 모두 선택 사항입니다. 값이 비어
있으면 기본값을 사용합니다.

| Variable | 기본값 | 설명 |
|---|---|---|
| `NOTIFIER_ENABLED` | (미설정) | `true`이면 1시간마다 스케줄 실행 |
| `SOURCE_REPO` | `anthropics/claude-code` | 감시할 저장소 (`owner/name` 형식) |
| `INCLUDE_PRERELEASES` | `true` | 프리릴리스도 알릴지 여부 |
| `MAX_RELEASES_PER_RUN` | `5` | 한 번 실행에 알리는 최대 릴리스 수 (1–20). 나머지는 다음 실행에 게시 |
| `CLAUDE_MODEL` | `claude-sonnet-5-5` | 번역에 사용할 Claude 모델 |
| `STATE_BRANCH` | `notifier-state` | `state.json`을 저장하는 브랜치 |
| `TARGET_LANGUAGE` | `zh-TW` | 번역할 언어: `zh-TW`(번체 중국어), `zh-CN`(간체 중국어), `ja`(일본어), `ko`(한국어) |

다른 언어를 추가하려면 [`notifier/locales.py`](../notifier/locales.py)에 언어 이름과
Discord 라벨을 추가하세요.

## 비용

공개 저장소에서는 GitHub Actions가 무료입니다. 알리는 릴리스마다 Claude API를 한 번
호출하며, 요금은 여러분의 Anthropic 계정에 청구됩니다. 새 릴리스가 없는 실행에서는 Claude를
호출하지 않습니다.

## 문제 해결

| 증상 | 원인과 해결 방법 |
|---|---|
| `::error::ANTHROPIC_API_KEY is required but not set` | secret을 추가하세요 (3단계) |
| `::error::DISCORD_WEBHOOK_URL is required but not set` | secret을 추가하거나 **dry_run**으로 실행하세요 |
| `Creating state branch (...) failed with HTTP 403` | Workflow가 `contents: write` 권한을 받지 못했습니다. `notify.yml`이 이 권한을 요청하는지, 그리고 조직 정책이 **Settings → Actions → General → Workflow permissions**에서 토큰을 읽기 전용으로 제한하지 않는지 확인하세요 |
| 스케줄 실행이 건너뛰어짐 | `NOTIFIER_ENABLED`를 `true`로 설정하세요. 60일 동안 활동이 없는 저장소는 GitHub가 스케줄을 일시 중지하므로 Actions 탭에서 workflow를 다시 활성화하세요 |
| 릴리스를 다시 알리고 싶음 | `notifier-state` 브랜치의 `state.json`을 수정하거나 삭제하세요. 삭제하면 다음 실행에서 최신 릴리스 하나만 알립니다 |

## 개발

[CONTRIBUTING.md](../CONTRIBUTING.md)를 참고하세요. 요약:

```bash
pip install --require-hashes -r requirements.txt -r requirements-dev.txt
ruff check . && ruff format --check .
pytest --cov=notifier
```

## 보안

취약점은 [SECURITY.md](../SECURITY.md)에 안내된 방법으로 비공개로 제보해 주세요.

## 라이선스

[MIT](../LICENSE)
