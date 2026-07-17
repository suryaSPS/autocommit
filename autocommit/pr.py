"""PR description writer.

Builds a title + markdown body from the branch's commits and diff against
the base branch. AI providers write the prose; local mode assembles a
serviceable description from the commit subjects alone.
"""

from .llm import LOCAL_PROVIDERS, complete

PR_PROMPT = """Write a pull request title and description for this branch.

Branch: {branch}  (base: {base})

Commits on this branch, oldest first:
{commits}

Full diff against the base branch:
```
{diff}
```

Output format — exactly this structure, no other text:

TITLE: <one line, under 72 characters, imperative mood>

## Summary
<2-4 sentences: what this PR does and why>

## Changes
<bulleted list of the concrete changes, grouped logically>

## Testing
<how these changes were or should be verified; write "Not specified" if the diff contains no tests>

Rules:
- Describe WHAT changed and WHY, not a file-by-file narration
- No marketing language, no filler
- Mention breaking changes prominently if any"""


def _offline_pr(branch, base, commits):
    title = commits[-1] if commits else f"Merge {branch} into {base}"
    if len(title) > 72:
        title = title[:69] + "..."
    bullets = "\n".join(f"- {c}" for c in commits) or "- (no commits found)"
    body = (
        "## Summary\n"
        f"Changes from `{branch}` targeting `{base}` "
        f"({len(commits)} commit{'s' if len(commits) != 1 else ''}).\n\n"
        "## Changes\n"
        f"{bullets}\n\n"
        "## Testing\n"
        "Not specified.\n"
    )
    return title, body


def write_pr(branch, base, commits, diff, config):
    """Return (title, body)."""
    if config.get("provider") in LOCAL_PROVIDERS:
        return _offline_pr(branch, base, commits)

    commits_str = "\n".join(f"  - {c}" for c in commits) or "  (none)"
    raw = complete(
        PR_PROMPT.format(branch=branch, base=base, commits=commits_str, diff=diff),
        config,
        max_tokens=2000,
    )

    title, body = "", raw
    for i, line in enumerate(raw.split("\n")):
        if line.startswith("TITLE:"):
            title = line.removeprefix("TITLE:").strip()
            body = "\n".join(raw.split("\n")[i + 1 :]).strip()
            break
    if not title:
        title, _ = _offline_pr(branch, base, commits)
    return title, body
