"""Intelligent commit splitting.

Clusters the staged files into coherent commit groups — source changes by
scope, then tests, docs, and config — so one oversized `git add .` becomes
a clean series of atomic commits. AI providers propose the grouping from
the diff; local mode uses the same deterministic classifiers the heuristic
message generator uses. Splitting is file-level: a single file's hunks are
never divided across commits, so no group can produce a broken in-between
state that the file itself didn't have.
"""

import json
import re
from collections import namedtuple

from .llm import LOCAL_PROVIDERS, _infer_scope, _is_config, _is_doc, _is_test, complete

Group = namedtuple("Group", ["label", "files", "reason"])

SPLIT_PROMPT = """You are splitting one large staged git change into atomic commits.

Staged files:
{files}

Staged diff:
```
{diff}
```

Group the files into 2-6 logical commits. Files that implement one change
belong together; unrelated concerns (docs, tests for other areas, config,
separate features) belong apart. Source changes come before their tests.

Respond with ONLY this JSON, no other text:
{{"groups": [{{"reason": "<short description of the commit>", "files": ["path", ...]}}, ...]}}

Every staged file must appear in exactly one group."""


def _classify(path):
    """Return (sort_key, label) for a file. Source scopes sort first."""
    if _is_test(path):
        return (2, "tests")
    if _is_doc(path):
        return (3, "docs")
    if _is_config(path):
        return (4, "config")
    return (1, _infer_scope([path]) or "core")


def propose_groups(files):
    """Deterministic grouping: source files bucketed by scope, then tests, docs, config."""
    buckets: dict = {}
    for f in files:
        key = _classify(f)
        buckets.setdefault(key, []).append(f)

    groups = []
    for (order, label), members in sorted(buckets.items()):
        reason = {
            2: "test changes",
            3: "documentation",
            4: "config and tooling",
        }.get(order, f"{label} changes")
        groups.append(Group(label, members, reason))
    return groups


def _parse_ai_groups(raw, files):
    """Parse the model's JSON. Returns groups only if they exactly partition files."""
    fenced = re.search(r"\{.*\}", raw, re.DOTALL)
    if not fenced:
        return None
    try:
        data = json.loads(fenced.group(0))
    except json.JSONDecodeError:
        return None

    groups = []
    seen = []
    for g in data.get("groups", []):
        members = [f for f in g.get("files", []) if isinstance(f, str)]
        if not members:
            return None
        groups.append(Group(_infer_scope(members) or "change", members, g.get("reason", "")))
        seen.extend(members)

    if sorted(seen) != sorted(files):
        return None  # missing, duplicated, or invented files — don't trust it
    return groups


def propose_groups_ai(diff, files, config):
    """AI grouping with strict validation; falls back to the heuristic.

    Returns (groups, used_ai).
    """
    if config.get("provider") in LOCAL_PROVIDERS:
        return propose_groups(files), False

    files_str = "\n".join(f"  - {f}" for f in files)
    raw = complete(SPLIT_PROMPT.format(files=files_str, diff=diff), config, max_tokens=1500)
    groups = _parse_ai_groups(raw, files)
    if groups is None:
        return propose_groups(files), False
    return groups, True
