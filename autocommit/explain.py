"""Explain the staged diff in plain language.

Needs a real model — there is no offline mode; the heuristic can classify
a change but cannot explain intent.
"""

from .llm import LOCAL_PROVIDERS, complete

EXPLAIN_PROMPT = """Explain this staged git diff to a reviewer who hasn't seen the codebase today.

Changed files:
{files}

Staged diff:
```
{diff}
```

Output exactly these markdown sections:

## What changed
<2-4 sentences describing the change in plain language>

## Why (inferred)
<the most likely motivation, inferred from the code — say "unclear" if it is>

## Impact
<what behavior changes for users or callers>

## Risk
<Low, Medium, or High — one line explaining the rating; call out missing tests>

Rules:
- Plain language, no file-by-file narration
- Be honest about uncertainty; never invent intent the diff doesn't support"""


def explain(diff, files, config):
    """Return a markdown explanation, or None if the provider is offline-only."""
    if config.get("provider") in LOCAL_PROVIDERS:
        return None
    files_str = "\n".join(f"  - {f}" for f in files)
    return complete(EXPLAIN_PROMPT.format(files=files_str, diff=diff), config, max_tokens=1500)
