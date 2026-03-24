<div align="center">

# autocommit

**AI-powered git workflow assistant — review, validate, commit, and ship with confidence**

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)
[![PyPI](https://img.shields.io/badge/PyPI-autocommit--ai-orange.svg)](https://pypi.org/project/autocommit-ai/)

</div>

---

## What it does

`autocommit` is a full pre-push workflow tool for developers who care about code quality:

1. **Scans** staged changes for secrets, debug artifacts, and conflict markers before you commit
2. **Reviews** your code with AI — catches bugs, security issues, and breaking changes
3. **Generates** precise conventional commit messages from your diff
4. **Checks** for merge conflicts against your target branch before you push
5. **Writes** GitHub PR descriptions from your commits and diff

```
git add orders/views.py orders/serializers.py

autocommit review      # AI code review first
autocommit             # then commit — scanner runs automatically
autocommit merge-check # check for conflicts before pushing
autocommit pr          # generate PR description
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

## Workflow

### 1. Stage your changes

```bash
git add <files>
# or
autocommit -a   # stage everything
```

### 2. Review before committing

```bash
autocommit review
```

```
Reviewing 3 files...

╭─ Code Review ─────────────────────────────────────────────────────╮
│ ⚠️ Minor issues                                                    │
│                                                                    │
│ [WARNING] orders/views.py: missing null check on warehouse field   │
│ [SUGGESTION] orders/serializers.py: consider extracting validation │
╰───────────────────────────────────────────────────────────────────╯
```

### 3. Commit — scanner runs automatically

```bash
autocommit
```

The scanner checks for secrets, debug artifacts, and conflict markers on every commit:

```
⚠ Debug artifacts found:
  line 42 (pdb.set_trace()): pdb.set_trace()

Continue anyway? [y/N]
```

Secrets and conflict markers are hard blockers — they exit before the LLM is called.

### 4. Check for merge conflicts before pushing

```bash
autocommit merge-check              # checks against main/master
autocommit merge-check --into dev   # or a specific branch
```

```
✓ Clean merge — feature/bulk-export merges into main with no conflicts.
```

```
✗ Merge conflicts detected — feature/bulk-export → main

  · orders/models.py
    CONFLICT (content): Merge conflict in orders/models.py
```

### 5. Generate a PR description

```bash
autocommit pr               # generate from all commits since main
autocommit pr --into dev    # target a specific branch
autocommit pr --copy        # copy to clipboard
```

```
╭─ PR Title ───────────────────────────────────────────────────────╮
│ feat(orders): add bulk export endpoint with date range filters   │
╰──────────────────────────────────────────────────────────────────╯

╭─ PR Description ─────────────────────────────────────────────────╮
│ ## Summary                                                       │
│ - Adds POST /orders/export accepting start_date and end_date     │
│ - Returns CSV with order ID, status, and warehouse               │
│ - Validates date range and rejects ranges over 90 days           │
│                                                                  │
│ ## Test plan                                                      │
│ - [ ] POST /orders/export returns 200 with valid date range      │
│ - [ ] Returns 400 when range exceeds 90 days                     │
│ - [ ] CSV headers match spec                                     │
╰──────────────────────────────────────────────────────────────────╯
```

---

## All commands

| Command | Description |
|---|---|
| `autocommit` | Scan + generate commit message (interactive) |
| `autocommit -a` | Stage all changes, then generate |
| `autocommit -y` | Auto-accept first suggestion |
| `autocommit review` | AI code review of staged changes |
| `autocommit merge-check` | Dry-run conflict check against main/master |
| `autocommit merge-check --into <branch>` | Check against a specific branch |
| `autocommit pr` | Generate GitHub PR title + description |
| `autocommit pr --copy` | Generate and copy to clipboard |
| `autocommit configure` | Interactive setup |
| `autocommit install-hook` | Install as git prepare-commit-msg hook |
| `autocommit version` | Show version |

---

## Options

```bash
autocommit [OPTIONS]

  -s, --style [conventional|angular|simple]
  -e, --emoji           Add emoji prefix to type
  -b, --body            Include a commit body
  -p, --provider [anthropic|openai]
  -a, --all             Stage all changes first
  -y, --yes             Auto-accept without prompting
```

---

## Commit Styles

| Style | Example output |
|---|---|
| `conventional` (default) | `feat(auth): add JWT refresh token rotation` |
| `angular` | `fix(orders): handle null warehouse on bulk export` |
| `simple` | `Fix null check in order serializer` |

---

## Scanner — what gets flagged

**Blockers** (hard exit, commit does not proceed):
- Hardcoded secrets: Anthropic/OpenAI API keys, GitHub tokens, AWS keys, Slack tokens, private keys, hardcoded passwords
- Merge conflict markers: `<<<<<<<`, `=======`, `>>>>>>>`

**Warnings** (prompt to continue):
- Debug artifacts: `pdb.set_trace()`, `breakpoint()`, `console.log`, `debugger`, `byebug`, `binding.pry`

---

## Configure

```bash
autocommit configure
```

Preferences are saved to `~/.autocommit/config.json`. API keys are **never** written to disk.

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

---

## Git Hook

```bash
autocommit install-hook
```

Installs `autocommit` as a `prepare-commit-msg` hook — every `git commit` auto-generates and accepts a message. To uninstall: `rm .git/hooks/prepare-commit-msg`.

---

## License

MIT
