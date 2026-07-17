"""Secret scanner — regex-based, deterministic, no network, no LLM.

Scans only lines being ADDED in a diff, so pre-existing (already-committed)
secrets don't block unrelated commits. Findings carry file, line number,
rule name, and a redacted preview — the full secret is never printed.
"""

import re
from collections import namedtuple

Finding = namedtuple("Finding", ["file", "line", "rule", "preview"])

# Each rule: (name, compiled pattern). Patterns target well-known token
# formats first (low false-positive rate), then a generic assignment
# catch-all last.
RULES = [
    ("AWS access key ID", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    ("GitHub fine-grained PAT", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{22,}\b")),
    ("Anthropic API key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}\b")),
    ("OpenAI API key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}\b")),
    ("Slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("Stripe live key", re.compile(r"\b[rs]k_live_[A-Za-z0-9]{20,}\b")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("Private key block", re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY")),
    ("JWT", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")),
    (
        "Hardcoded credential assignment",
        re.compile(
            r"""(?ix)
            \b(password|passwd|secret|api_?key|auth_?token|access_?token)\b
            \s*[:=]\s*
            ["'][^"'\s]{8,}["']
            """
        ),
    ),
]

# Values that look like credentials but are clearly placeholders.
PLACEHOLDER = re.compile(
    r"(?i)(xxx+|\.\.\.|<[^>]+>|\{\{.*\}\}|\$\{.*\}|your[_-]|example|changeme|dummy|placeholder)"
)

HUNK_HEADER = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")


def _redact(text, match):
    """Show enough of the match to locate it, never the whole secret."""
    secret = match.group(0)
    if len(secret) <= 12:
        return secret[:4] + "…"
    return f"{secret[:8]}…{secret[-4:]}"


def scan_diff(diff):
    """Return a list of Findings for secrets in the ADDED lines of a unified diff."""
    findings = []
    current_file = None
    line_no = 0

    for raw in diff.split("\n"):
        if raw.startswith("diff --git "):
            _, _, rest = raw.partition(" b/")
            current_file = rest or None
            continue
        header = HUNK_HEADER.match(raw)
        if header:
            line_no = int(header.group(1)) - 1
            continue
        if raw.startswith("-"):
            continue  # removed line — doesn't count toward new-file line numbers...
        if raw.startswith("+") and not raw.startswith("+++"):
            line_no += 1
            content = raw[1:]
            for rule, pattern in RULES:
                m = pattern.search(content)
                if m and not PLACEHOLDER.search(m.group(0)):
                    findings.append(
                        Finding(current_file or "?", line_no, rule, _redact(content, m))
                    )
                    break  # one finding per line is enough
        elif not raw.startswith("\\"):
            line_no += 1  # context line

    return findings
