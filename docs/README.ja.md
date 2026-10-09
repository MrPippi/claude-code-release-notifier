# claude-code-release-notifier

[![CI](https://github.com/MrPippi/claude-code-release-notifier/actions/workflows/ci.yml/badge.svg)](https://github.com/MrPippi/claude-code-release-notifier/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](../LICENSE)

[English](../README.md) | [繁體中文](README.zh-TW.md) | [简体中文](README.zh-CN.md) | **日本語** | [한국어](README.ko.md)

[anthropics/claude-code](https://github.com/anthropics/claude-code) のリリースを監視し、
Claude API でリリースノートを繁体字中国語に翻訳して Discord チャンネルに投稿します。
すべて自分の fork の GitHub Actions 上で動作するため、サーバーもデータベースも不要です。

## 仕組み

Workflow は 1 時間ごとに次の処理を行います。

1. 監視対象リポジトリの最近のリリースを取得する。
2. 前回通知したリリース以降に公開されたものを古い順に、最大 `MAX_RELEASES_PER_RUN` 件選ぶ。
3. それぞれを Claude で翻訳し、Discord に embed として投稿する。
4. 通知したリリースを `notifier-state` ブランチの `state.json` に記録する。

初回実行時は状態がないため、過去の履歴をすべて投稿するのではなく、最新のリリースだけを
投稿します。状態は専用のブランチに保存されるので、通知によって `main` にコミットが
増えることはありません。

## 自分の環境にセットアップする

[Anthropic API キー](https://console.anthropic.com/)と、Webhook を作成できる Discord
チャンネルが必要です。

### 1. このリポジトリを fork する

**Fork** をクリックし、fork 先の **Actions** タブで workflows を有効にします。

### 2. Discord Webhook を作成する

Discord でチャンネルの **チャンネルの編集 → 連携サービス（Integrations）→ ウェブフック**
を開き、**新しいウェブフック** をクリックして URL をコピーします。

### 3. Secrets を追加する

fork 先の **Settings → Secrets and variables → Actions → Secrets** で次を追加します。

| Secret | 値 |
|---|---|
| `ANTHROPIC_API_KEY` | Anthropic API キー |
| `DISCORD_WEBHOOK_URL` | 手順 2 でコピーした Webhook URL |

GitHub CLI を使う場合：

```bash
gh secret set ANTHROPIC_API_KEY -R <あなたのアカウント>/claude-code-release-notifier
gh secret set DISCORD_WEBHOOK_URL -R <あなたのアカウント>/claude-code-release-notifier
```

### 4. ドライランで試す

**Actions → Release Notifier → Run workflow** を開き、**dry_run** にチェックを入れたまま
実行します。ログに最新リリースの翻訳済み embed が表示されます。Discord への投稿や状態の
保存は行われません。

### 5. 有効にする

**Settings → Secrets and variables → Actions → Variables** で `NOTIFIER_ENABLED` を追加し、
値を `true` にします。以降は 1 時間ごとのスケジュールで新しいリリースが投稿されます。
一時停止するには、この variable を削除するか別の値に変更してください。

## 設定

スケジュール実行に必要な `NOTIFIER_ENABLED` 以外の variable はすべて任意です。空の場合は
デフォルト値が使われます。

| Variable | デフォルト | 説明 |
|---|---|---|
| `NOTIFIER_ENABLED` | （未設定） | `true` で 1 時間ごとのスケジュールを有効化 |
| `SOURCE_REPO` | `anthropics/claude-code` | 監視するリポジトリ（`owner/name` 形式） |
| `INCLUDE_PRERELEASES` | `true` | プレリリースも通知するか |
| `MAX_RELEASES_PER_RUN` | `5` | 1 回の実行で通知する最大件数（1–20）。残りは次回に投稿 |
| `CLAUDE_MODEL` | `claude-sonnet-5-5` | 翻訳に使う Claude モデル |
| `STATE_BRANCH` | `notifier-state` | `state.json` を保存するブランチ |

別の言語に翻訳したい場合は、[`notifier/prompts.py`](../notifier/prompts.py) のプロンプトと
[`notifier/discord.py`](../notifier/discord.py) のラベルを編集してください。

## 費用

公開リポジトリでは GitHub Actions は無料です。通知するリリース 1 件ごとに Claude API を
1 回呼び出し、その料金は Anthropic アカウントに請求されます。新しいリリースがない実行では
Claude は呼び出されません。

## トラブルシューティング

| 症状 | 原因と対処 |
|---|---|
| `::error::ANTHROPIC_API_KEY is required but not set` | secret を追加する（手順 3） |
| `::error::DISCORD_WEBHOOK_URL is required but not set` | secret を追加するか、**dry_run** で実行する |
| `Creating state branch (...) failed with HTTP 403` | Workflow が `contents: write` を取得できていません。`notify.yml` がこの権限を要求しているか、組織のポリシーで **Settings → Actions → General → Workflow permissions** のトークンが読み取り専用に制限されていないか確認してください |
| スケジュール実行がスキップされる | `NOTIFIER_ENABLED` を `true` に設定する。60 日間アクティビティがないリポジトリでは GitHub がスケジュールを停止するため、Actions タブで workflow を再度有効にしてください |
| リリースを再通知したい | `notifier-state` ブランチの `state.json` を編集または削除する。削除すると次回は最新のリリースだけが通知されます |

## 開発

[CONTRIBUTING.md](../CONTRIBUTING.md) を参照してください。概要：

```bash
pip install --require-hashes -r requirements.txt -r requirements-dev.txt
ruff check . && ruff format --check .
pytest --cov=notifier
```

## セキュリティ

脆弱性は [SECURITY.md](../SECURITY.md) の手順に従って非公開で報告してください。

## ライセンス

[MIT](../LICENSE)
