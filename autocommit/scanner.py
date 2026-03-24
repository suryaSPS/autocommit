import re
from dataclasses import dataclass, field
from typing import List


SECRET_PATTERNS = [
    (r"sk-ant-[a-zA-Z0-9\-_]{20,}", "Anthropic API key"),
    (r"ghp_[a-zA-Z0-9]{36}", "GitHub personal access token"),
    (r"github_pat_[a-zA-Z0-9_]{82}", "GitHub fine-grained PAT"),
    (r"AKIA[0-9A-Z]{16}", "AWS access key ID"),
    (r"sk-[a-zA-Z0-9]{48}", "OpenAI API key"),
    (r"xox[baprs]-[a-zA-Z0-9\-]+", "Slack token"),
    (r"-----BEGIN (RSA|EC|DSA|OPENSSH) PRIVATE KEY-----", "Private key"),
    (r'(?i)(password|passwd|pwd)\s*[=:]\s*["\']?[^\s"\']{8,}', "Hardcoded password"),
    (r'(?i)(secret|api_key|apikey|auth_token|access_token)\s*[=:]\s*["\']?[a-zA-Z0-9\-_]{16,}', "Hardcoded secret/token"),
]

DEBUG_PATTERNS = [
    (r"pdb\.set_trace\(\)", "pdb.set_trace()"),
    (r"\bbreakpoint\(\)", "breakpoint()"),
    (r"\bimport pdb\b", "pdb import"),
    (r"console\.log\(", "console.log"),
    (r"\bdebugger;", "debugger statement"),
    (r"\bbyebug\b", "byebug debugger"),
    (r"binding\.pry", "Ruby pry"),
]

CONFLICT_MARKER_RE = re.compile(r"^(<{7}|={7}|>{7})", re.MULTILINE)


@dataclass
class Finding:
    line: int
    label: str
    preview: str


@dataclass
class ScanResult:
    secrets: List[Finding] = field(default_factory=list)
    debug_artifacts: List[Finding] = field(default_factory=list)
    conflict_markers: List[Finding] = field(default_factory=list)

    @property
    def has_blockers(self):
        return bool(self.secrets or self.conflict_markers)

    @property
    def has_warnings(self):
        return bool(self.debug_artifacts)

    @property
    def clean(self):
        return not self.has_blockers and not self.has_warnings


def scan_diff(diff: str) -> ScanResult:
    result = ScanResult()
    lines = diff.split("\n")

    for line_num, line in enumerate(lines, 1):
        # Only inspect added lines, skip diff headers
        if not line.startswith("+") or line.startswith("+++"):
            continue

        content = line[1:]
        preview = content.strip()[:80]

        for pattern, label in SECRET_PATTERNS:
            if re.search(pattern, content):
                result.secrets.append(Finding(line_num, label, preview))
                break

        for pattern, label in DEBUG_PATTERNS:
            if re.search(pattern, content):
                result.debug_artifacts.append(Finding(line_num, label, preview))
                break

    for match in CONFLICT_MARKER_RE.finditer(diff):
        line_num = diff[: match.start()].count("\n") + 1
        result.conflict_markers.append(Finding(line_num, "Conflict marker", match.group()))

    return result
