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

`autocommit` reads your staged diff and generates a precise, conventional commit message using Claude or GPT — in under 3 seconds. No API key? Run it fully offline with `--no-ai` and it builds a message straight from the diff, or point it at a local model with Ollama.

It does more than messages:

- **Blocks secrets** — every commit is scanned for API keys, tokens, and credentials in your staged changes. Leaks are stopped before they land.
- **Reviews your diff** — `autocommit review` flags bugs and issues before you commit.
- **Writes your PR** — `autocommit pr` drafts a title and description from your branch's commits and diff.

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

**No API key?** Skip setup entirely and use offline mode — see [No-AI mode](#no-ai-offline-mode) below.

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

# No API key — generate offline from the diff
autocommit --no-ai
```

---

## No-AI (offline) mode

Don't have an API key, working offline, or just want zero-cost commits? Add `--no-ai`
and `autocommit` builds the message locally by analyzing your staged diff — no network,
no key, no SDK required.

```bash
autocommit --no-ai        # generate offline
autocommit --no-ai -a -y  # stage all, offline, auto-accept
```

It inspects the diff to pick a sensible message:

| What it detects | Example output |
|---|---|
| Brand-new file(s) | `feat(auth): add login` |
| Docs / README changes | `docs: update README` |
| Test files | `test(tests): add test_llm` |
| Config / build files | `chore: update pyproject` |
| Mostly deletions | `refactor(api): remove legacy client` |
| File removals | `chore: remove old_helper` |

The type (`feat`/`fix`/`docs`/`test`/`chore`/`refactor`), scope (derived from the common
directory), and emoji all respect your configured style. It's a heuristic, not a mind
reader — press `e` to tweak anything before committing.

Make it the default so you never pass the flag:

```bash
autocommit configure   # choose "local" when prompted for provider
```

---

## Secret Scanning

Before every commit, `autocommit` scans your **staged changes** for secrets — AWS keys,
GitHub tokens, Anthropic/OpenAI keys, Slack/Stripe/Google keys, private key blocks, JWTs,
and hardcoded `password`/`api_key`/`token` assignments. If it finds one, the commit is
blocked and the finding is shown with the secret redacted:

```
╭──────────────── Secrets detected (1) ────────────────╮
│ AWS access key ID  config.py:12                      │
│     AKIAIOSF…MPLE                                     │
╰──────────────────────────────────────────────────────╯
```

Only **added** lines are scanned, so pre-existing secrets in unrelated files don't block you.
Obvious placeholders (`your_key_here`, `xxxx`, `${VAR}`, `changeme`) are ignored.

Run the scan on its own — it exits non-zero when anything is found, so it drops straight into
a pre-commit hook or CI step:

```bash
autocommit scan
```

Turn the automatic commit-time gate off in `autocommit configure` (or set `"scan_secrets": false`
in your config).

---

## Review

Get a review of your staged diff before you commit:

```bash
autocommit review            # AI review with your configured provider
autocommit review --no-ai    # offline pattern checks only
```

With an AI provider it looks for bugs, security issues, and clear mistakes in the changed
lines. Offline mode is deterministic — it flags leftover debug statements (`print`,
`console.log`, `breakpoint()`), merge-conflict markers, and new `TODO`/`FIXME` comments —
and tells you it isn't a correctness review.

---

## Pull Requests

Draft a PR title and description from the commits and diff on your current branch:

```bash
autocommit pr                    # base branch autodetected (origin/HEAD, then main/master)
autocommit pr --base develop     # compare against a specific branch
autocommit pr --no-ai            # assemble from commit subjects, no API key
```

Output is a title plus a `## Summary` / `## Changes` / `## Testing` markdown body — paste it
straight into GitHub.

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
  "max_diff_lines": 500,
  "scan_secrets": true,
  "ollama_model": "llama3.2",
  "ollama_host": "http://localhost:11434"
}
```

</details>

---

## Providers

| Provider | Default Model | Env Var |
|---|---|---|
| `anthropic` (default) | `claude-opus-4-8` | `ANTHROPIC_API_KEY` |
| `openai` | `gpt-4o-mini` | `OPENAI_API_KEY` |
| `ollama` | `llama3.2` (local LLM) | none |
| `local` | — (offline heuristic) | none |

Switch permanently:
```bash
autocommit configure   # select openai when prompted
```

Switch for one commit:
```bash
autocommit -p openai
```

### Ollama (local LLM)

Run a real model on your own machine — no API key, no network calls off-box:

```bash
ollama serve
ollama pull llama3.2

autocommit -p ollama            # one commit
autocommit configure            # choose "ollama"; set model + host
```

Model and host are configurable (`ollama_model`, `ollama_host`).

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
| `autocommit --no-ai` | Generate offline, no API key needed |
| `autocommit scan` | Scan staged changes for secrets (exits 1 on findings) |
| `autocommit review` | Review the staged diff for bugs and issues |
| `autocommit pr` | Draft a PR title and description for the branch |
| `autocommit configure` | Interactive setup |
| `autocommit install-hook` | Install as git hook in current repo |
| `autocommit version` | Show version |

---

## License

MIT
