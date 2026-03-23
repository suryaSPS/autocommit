<div align="center">

# autocommit

**AI-powered git commit message generator — reads your staged diff, writes the commit for you**

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)
[![PyPI](https://img.shields.io/badge/PyPI-autocommit--ai-orange.svg)](https://pypi.org/project/autocommit-ai/)

</div>

---

## The Problem

Writing good commit messages is tedious. Most developers either:
- Write vague messages like `fix bug` or `update stuff`
- Spend more time on the message than the actual change
- Skip conventions entirely under time pressure

## The Solution

`autocommit` reads your staged diff and generates a precise, conventional commit message using Claude or GPT — in under 3 seconds.

```
git add orders/views.py orders/serializers.py

autocommit
```

```
Staged (2 files):
  · orders/views.py
  · orders/serializers.py

╭─ Suggested commit message ────────────────────────────────────╮
│ feat(orders): add bulk export endpoint with date range filters │
╰───────────────────────────────────────────────────────────────╯

[Enter] commit   e edit   r regenerate   q quit
>
✓ Committed successfully
```

---

## Installation

```bash
pip install autocommit-ai
```

## Setup

```bash
# Anthropic Claude (default)
export ANTHROPIC_API_KEY=sk-ant-...

# Or OpenAI
export OPENAI_API_KEY=sk-...
```

Add the export to your `~/.zshrc` or `~/.bashrc` so it persists.

---

## Quick Start

```bash
# Stage your changes
git add <files>

# Generate and commit
autocommit
```

That's it. Press Enter to accept, `e` to edit, `r` to regenerate, `q` to quit.

---

## Usage

```bash
# Stage everything, then generate
autocommit -a

# Auto-accept without prompting (CI / hooks)
autocommit -a -y

# Change style for one commit
autocommit --style simple
autocommit --style angular

# Add emoji prefix  (✨ feat, 🐛 fix, ♻️ refactor...)
autocommit --emoji

# Include a commit body explaining WHY
autocommit --body

# Switch provider for one commit
autocommit --provider openai
```

---

## Commit Styles

| Style | Example output |
|---|---|
| `conventional` (default) | `feat(auth): add JWT refresh token rotation` |
| `angular` | `fix(orders): handle null warehouse on bulk export` |
| `simple` | `Fix null check in order serializer` |

---

## Configure

Run the interactive setup to save your preferences:

```bash
autocommit configure
```

Preferences are saved to `~/.autocommit/config.json`.
API keys are **never** written to disk — always read from environment variables.

<details>
<summary>Manual config (~/.autocommit/config.json)</summary>

```json
{
  "provider": "anthropic",
  "style": "conventional",
  "include_scope": true,
  "include_body": false,
  "emoji": false,
  "max_diff_lines": 500
}
```

</details>

---

## Providers

| Provider | Default Model | Env Var |
|---|---|---|
| `anthropic` (default) | `claude-sonnet-4-6` | `ANTHROPIC_API_KEY` |
| `openai` | `gpt-4o-mini` | `OPENAI_API_KEY` |

Switch permanently:
```bash
autocommit configure   # select openai when prompted
```

Switch for one commit:
```bash
autocommit -p openai
```

---

## Git Hook

Install `autocommit` as a `prepare-commit-msg` hook so every `git commit` auto-generates a message:

```bash
autocommit install-hook
```

To uninstall:
```bash
rm .git/hooks/prepare-commit-msg
```

---

## Commands

| Command | Description |
|---|---|
| `autocommit` | Generate from staged diff (interactive) |
| `autocommit -a` | Stage all changes, then generate |
| `autocommit -y` | Auto-accept first suggestion |
| `autocommit configure` | Interactive setup |
| `autocommit install-hook` | Install as git hook in current repo |
| `autocommit version` | Show version |

---

## License

MIT
