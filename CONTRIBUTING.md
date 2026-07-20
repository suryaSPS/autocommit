# Contributing to autocommit

Thanks for your interest in improving **autocommit** (published on PyPI as
[`commitstash`](https://pypi.org/project/commitstash/)) — an AI-powered git
workflow CLI that writes commit messages, scans for secrets, reviews diffs, and
drafts PRs from your staged changes.

This guide covers the fast path for contributors. For deeper conventions on
structure, style, and testing, see [`AGENTS.md`](./AGENTS.md).

## Development setup

Requires **Python 3.9+**.

```bash
git clone https://github.com/suryaSPS/autocommit.git
cd autocommit

python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate

pip install -e ".[dev]"          # editable install + dev tooling
pre-commit install               # run lint/type checks on every commit
```

Verify the console script is wired up:

```bash
autocommit version
```

## Running the checks

CI (`.github/workflows/ci.yml`) runs these across Python 3.9–3.12, so run them
locally before pushing:

```bash
ruff check .            # lint (100-char line length)
mypy autocommit/        # type-check
pytest -q               # tests
```

## Making a change

1. Branch off `master`: `git checkout -b feat/short-description`.
2. Make focused commits — this repo **dogfoods itself**, so stage your changes
   and run `autocommit` to generate the message.
3. Follow [Conventional Commits](https://www.conventionalcommits.org/): prefixes
   like `feat:`, `fix:`, `docs:`, `test:`, `chore:`, `refactor:`. The
   `autocommit changelog` command relies on these to generate release notes.
4. Add or update tests under `tests/` (`test_<module>.py`). Mock network clients
   and subprocess calls — never require a real API key or make real commits.
5. Open a PR against `master` using the pull request template.

## Adding a new LLM provider

Providers live in [`autocommit/providers.py`](./autocommit/providers.py) behind a
small abstraction, so adding one (e.g. Gemini or Groq) is self-contained:

1. Subclass `LLMProvider` and implement `complete(self, prompt, config, max_tokens)`,
   returning the model's text response.
2. Give it a `name` and register it in the `PROVIDERS` registry (follow how
   `AnthropicProvider`, `OpenAIProvider`, and `OllamaProvider` do it).
3. If the provider runs locally with no key (like Ollama), add its name to
   `LOCAL_PROVIDERS` in `autocommit/llm.py`.
4. Add unit tests that mock the client — assert prompt handling and error paths,
   not live network calls.

## Reporting bugs & requesting features

Use the [issue templates](./.github/ISSUE_TEMPLATE/) — they prompt for the
version (`autocommit version`), OS, provider, and steps to reproduce, which makes
triage much faster.

## Security

Never commit API keys or generated local config. `ANTHROPIC_API_KEY` and
`OPENAI_API_KEY` belong in environment variables only, never in
`~/.autocommit/config.json` or test fixtures. If you find a security issue,
please open a minimal report rather than including real secrets.

## License

By contributing, you agree that your contributions are licensed under the
project's [MIT License](./LICENSE).
