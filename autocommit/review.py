"""Code review of the staged diff.

AI providers get a structured review prompt. Local mode runs deterministic
checks only — leftover debug statements, conflict markers, new TODOs —
and says so, rather than pretending a heuristic can judge correctness.
"""

import re
from collections import namedtuple

from .llm import LOCAL_PROVIDERS, complete

Issue = namedtuple("Issue", ["file", "line", "kind", "detail"])

REVIEW_PROMPT = """You are a senior engineer reviewing a git diff before it is committed.

Changed files:
{files}

Staged diff:
```
{diff}
```

Review ONLY the changed lines. Report:
1. Bugs — logic errors, off-by-one, unhandled edge cases, broken error handling
2. Security issues — injection, unsafe deserialization, path traversal
3. Clear mistakes — leftover debug code, dead code, wrong variable used

Rules:
- Be specific: name the file and quote the problematic line
- Do NOT comment on style, formatting, or naming preferences
- Do NOT suggest speculative refactors
- If the diff looks correct, say exactly: "No issues found."
- Order findings most severe first
- Keep each finding to 1-3 sentences"""

_DEBUG_PATTERNS = [
    ("debug statement", re.compile(r"^\s*(print\(|console\.(log|debug)\(|debugger\b|breakpoint\(\)|pdb\.set_trace)")),
    ("merge conflict marker", re.compile(r"^(<{7}|={7}|>{7})( |$)")),
    ("new TODO/FIXME", re.compile(r"\b(TODO|FIXME|XXX)\b")),
]

_HUNK_HEADER = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")


def offline_review(diff):
    """Deterministic checks over added lines. Returns a list of Issues."""
    issues = []
    current_file = None
    line_no = 0

    for raw in diff.split("\n"):
        if raw.startswith("diff --git "):
            _, _, rest = raw.partition(" b/")
            current_file = rest or None
            continue
        header = _HUNK_HEADER.match(raw)
        if header:
            line_no = int(header.group(1)) - 1
            continue
        if raw.startswith("-"):
            continue
        if raw.startswith("+") and not raw.startswith("+++"):
            line_no += 1
            content = raw[1:]
            for kind, pattern in _DEBUG_PATTERNS:
                if pattern.search(content):
                    issues.append(Issue(current_file or "?", line_no, kind, content.strip()[:80]))
                    break
        elif not raw.startswith("\\"):
            line_no += 1

    return issues


def review(diff, files, config):
    """Return (text, is_offline). AI text for AI providers, None for local mode
    (callers render offline_review() Issues instead)."""
    if config.get("provider") in LOCAL_PROVIDERS:
        return None, True
    files_str = "\n".join(f"  - {f}" for f in files)
    return complete(REVIEW_PROMPT.format(files=files_str, diff=diff), config, max_tokens=2000), False
