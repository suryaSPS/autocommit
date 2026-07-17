# Repository Guidelines

## Project Structure & Module Organization

This repository contains a small Python CLI package for generating commit messages from staged diffs.

- `autocommit/cli.py` defines the Click command group, interactive prompts, and subcommands.
- `autocommit/git.py` wraps git operations such as reading staged files and creating commits.
- `autocommit/llm.py` builds prompts and calls Anthropic or OpenAI providers.
- `autocommit/config.py` loads and saves user preferences in `~/.autocommit/config.json`.
- `README.md` documents user-facing installation, setup, and CLI usage.
- `pyproject.toml` contains package metadata, dependencies, console script wiring, and Ruff settings.

There is no committed `tests/` directory yet; add one with new tests.

## Build, Test, and Development Commands

Use a virtual environment for local work:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Common commands:

- `autocommit version` verifies the editable console script is installed.
- `pytest` runs the test suite once tests exist.
- `ruff check .` runs lint checks with the repository line length setting.
- `python -m build` builds distribution artifacts, if the `build` package is installed.

For manual testing, stage a small change in a disposable git repo and run `autocommit`.

## Coding Style & Naming Conventions

Target Python 3.9+. Use 4-space indentation, clear function names, and focused modules. Private helpers use a leading underscore, for example `_build_prompt` and `_do_commit`.

Keep lines at or below 100 characters per `[tool.ruff]`. Prefer standard library facilities before adding dependencies. Keep CLI output consistent with the existing Click and Rich style.

## Testing Guidelines

Use `pytest` for new tests. Place tests under `tests/` and name files `test_<module>.py`, such as `tests/test_config.py`. Prefer unit tests for prompt construction, config behavior, and git wrapper error handling. Mock network clients and subprocess calls; do not require real API keys or commits.

## Commit & Pull Request Guidelines

Recent history uses Conventional Commit-style messages, for example `docs: add README` and `feat: initial autocommit CLI`. Continue using concise prefixes such as `feat:`, `fix:`, `docs:`, `test:`, and `chore:`.

Pull requests should include a short summary, testing performed, and any user-facing CLI behavior changes. Link related issues when available. Include terminal output only when it clarifies interactive CLI changes.

## Security & Configuration Tips

Never commit API keys or generated local config. `ANTHROPIC_API_KEY` and `OPENAI_API_KEY` must stay in environment variables. Do not persist secrets in `~/.autocommit/config.json` or test fixtures.
