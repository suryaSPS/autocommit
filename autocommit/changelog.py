"""Changelog generation from conventional commit history.

Deliberately deterministic — a changelog should be reproducible from the
same history, so no LLM is involved. Commits are grouped by conventional
type; breaking changes (`!` marker) get their own section up top.
"""

import datetime
import re

CC_PATTERN = re.compile(
    r"^(?P<type>[a-z]+)(?:\((?P<scope>[^)]*)\))?(?P<bang>!)?:\s*(?P<desc>.+)$"
)

SECTIONS = [
    ("feat", "Features"),
    ("fix", "Bug Fixes"),
    ("perf", "Performance"),
    ("refactor", "Refactoring"),
    ("docs", "Documentation"),
    ("test", "Tests"),
    ("build", "Build"),
    ("ci", "CI"),
    ("chore", "Chores"),
]


def group_commits(subjects):
    """Split subjects into (sections, breaking, other).

    sections: {heading: [entry, ...]} in SECTIONS order, empty headings omitted.
    breaking: entries whose type carried a `!`.
    other:    subjects that don't parse as conventional commits.
    """
    by_type: dict = {}
    breaking = []
    other = []

    for subject in subjects:
        m = CC_PATTERN.match(subject.strip())
        if not m:
            other.append(subject.strip())
            continue
        scope = m.group("scope")
        entry = f"**{scope}:** {m.group('desc')}" if scope else m.group("desc")
        if m.group("bang"):
            breaking.append(entry)
        by_type.setdefault(m.group("type"), []).append(entry)

    sections = {}
    for ctype, heading in SECTIONS:
        if ctype in by_type:
            sections[heading] = by_type[ctype]
    return sections, breaking, other


def build_changelog(subjects, label="Unreleased", date=None):
    """Render a markdown changelog block for one release."""
    date = date or datetime.date.today().isoformat()
    sections, breaking, other = group_commits(subjects)

    lines = [f"## {label} ({date})", ""]

    if breaking:
        lines.append("### ⚠ Breaking Changes")
        lines.append("")
        lines.extend(f"- {e}" for e in breaking)
        lines.append("")

    for heading, entries in sections.items():
        lines.append(f"### {heading}")
        lines.append("")
        lines.extend(f"- {e}" for e in entries)
        lines.append("")

    if other:
        lines.append("### Other")
        lines.append("")
        lines.extend(f"- {e}" for e in other)
        lines.append("")

    if not sections and not breaking and not other:
        lines.append("_No changes._")
        lines.append("")

    return "\n".join(lines)
