# autocommit

AI-powered git commit message generator. Reads your staged diff → writes a perfect conventional commit message → you just press Enter.

```
$ autocommit

Staged (3 files):
  · orders/views.py
  · orders/serializers.py
  · orders/tests.py

╭─ Suggested commit message ────────────────────────────────╮
│ feat(orders): add bulk order export endpoint with filters  │
╰───────────────────────────────────────────────────────────╯

[Enter] commit   e edit   r regenerate   q quit
>
✓ Committed successfully
```

## Install

```bash
pip install autocommit-ai
```

## Setup

```bash
# Set your API key (Anthropic Claude by default)
export ANTHROPIC_API_KEY=sk-ant-...

# Or use OpenAI
export OPENAI_API_KEY=sk-...
autocommit configure   # switch provider to openai
```

## Usage

```bash
# Generate from staged changes
autocommit

# Stage all changes, then generate
autocommit -a

# Auto-accept first suggestion (good for scripts/hooks)
autocommit -a -y

# Override style for one commit
autocommit --style simple
autocommit --style angular
autocommit --emoji

# Include a commit body explaining WHY
autocommit --body
```

## Styles

| Style | Example |
|---|---|
| `conventional` (default) | `feat(auth): add JWT refresh token rotation` |
| `angular` | `fix(orders): handle null warehouse on bulk export` |
| `simple` | `Fix null check in order serializer` |

## Configure

```bash
autocommit configure
```

Saves preferences to `~/.autocommit/config.json`. API keys are never written to disk — always read from environment.

## Git Hook

Install as a `prepare-commit-msg` hook so every `git commit` auto-generates a message:

```bash
autocommit install-hook
```

To uninstall: `rm .git/hooks/prepare-commit-msg`

## Providers

| Provider | Default Model | Env Var |
|---|---|---|
| `anthropic` (default) | `claude-sonnet-4-6` | `ANTHROPIC_API_KEY` |
| `openai` | `gpt-4o-mini` | `OPENAI_API_KEY` |

Switch provider:
```bash
autocommit configure        # interactive
autocommit -p openai        # one-off override
```

## License

MIT
