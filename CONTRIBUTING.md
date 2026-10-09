# Contributing

Thanks for helping out. Bug reports, fixes and documentation improvements are all welcome.

## Development setup

Requires Python 3.12 or newer.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
```

## Checks

Run these before opening a pull request. CI runs the same commands.

```bash
ruff check .
ruff format --check .
pytest --cov=notifier --cov-fail-under=80
```

Tests never touch the network: GitHub, Discord and Claude calls are replaced by fakes.
New behaviour needs a test. Bug fixes need a test that fails without the fix.

## Trying a change end to end

Push the branch to your fork, then run the **Release Notifier** workflow manually with
**dry_run** checked. It translates the release and prints the Discord payload without
posting it or saving state.

## Code layout

| Module | Responsibility |
|---|---|
| `notifier/config.py` | Read and validate environment variables |
| `notifier/http.py` | JSON over HTTP with retries for 429 and 5xx responses |
| `notifier/releases.py` | Fetch releases and select the ones to notify |
| `notifier/state.py` | Read and write `state.json` on the state branch |
| `notifier/prompts.py` | Translation prompts |
| `notifier/translate.py` | Claude API call |
| `notifier/discord.py` | Discord embed and webhook call |
| `notifier/__main__.py` | Wires the steps together |

## Commits and pull requests

- Use [Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`,
  `docs:`, `refactor:`, `test:`, `chore:`, `ci:`.
- Keep each pull request focused on one change and add an entry to `CHANGELOG.md`
  under "Unreleased".
- Never commit secrets, webhook URLs or personal data.
