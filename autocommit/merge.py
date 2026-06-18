from dataclasses import dataclass, field
from typing import List, Optional

from .git import _run_git, fetch_remote, get_current_branch, get_default_branch, ref_exists


@dataclass
class ConflictFile:
    path: str
    reason: str = ""


@dataclass
class MergeCheckResult:
    target_branch: str
    current_branch: Optional[str]
    conflicts: List[ConflictFile] = field(default_factory=list)
    fetch_failed: bool = False
    fetch_error: str = ""
    error: str = ""

    @property
    def clean(self):
        return not self.conflicts and not self.error


def _merge_base(ref_a: str, ref_b: str) -> Optional[str]:
    result = _run_git(["merge-base", ref_a, ref_b])
    return result.stdout.strip() if result.returncode == 0 else None


def _parse_conflicts_new(stdout: str, stderr: str) -> List[ConflictFile]:
    """Parse conflicts from git merge-tree --write-tree output."""
    conflicts = []
    seen = set()
    for line in (stdout + "\n" + stderr).split("\n"):
        low = line.lower()
        if "conflict" in low:
            parts = line.strip().split()
            # Last token that looks like a path
            path = next((p for p in reversed(parts) if "/" in p or "." in p), "unknown")
            if path not in seen:
                seen.add(path)
                conflicts.append(ConflictFile(path=path, reason=line.strip()))
    return conflicts


def _parse_conflicts_old(stdout: str) -> List[ConflictFile]:
    """Fallback: parse the classic git merge-tree output for conflict markers."""
    conflicts = []
    current_file = None
    for line in stdout.split("\n"):
        # Classic merge-tree output marks conflict sections with 'changed in both'
        stripped = line.strip()
        if stripped.startswith("changed in both"):
            current_file = None
        elif current_file is None and stripped and not stripped.startswith(("@", "-", "+")):
            current_file = stripped
            conflicts.append(ConflictFile(path=current_file, reason="changed in both"))
        elif "<<<<<<" in line and current_file:
            pass  # already captured
    # Deduplicate
    seen = set()
    unique = []
    for c in conflicts:
        if c.path not in seen:
            seen.add(c.path)
            unique.append(c)
    return unique


def check_merge(target: Optional[str] = None) -> MergeCheckResult:
    """
    Dry-run merge check of the current branch against target.
    Does NOT touch the working tree or index.
    """
    if target is None:
        target = get_default_branch()

    current = get_current_branch()
    result = MergeCheckResult(target_branch=target, current_branch=current)

    # Fetch latest target branch
    ok, err = fetch_remote(target)
    if not ok:
        result.fetch_failed = True
        result.fetch_error = err.strip()

    target_ref = f"origin/{target}" if not result.fetch_failed else target

    # Ensure target ref exists locally
    if not ref_exists(target_ref):
        result.error = f"Cannot resolve ref '{target_ref}'. Is the branch name correct?"
        return result

    merge_base = _merge_base("HEAD", target_ref)
    if not merge_base:
        result.error = f"Cannot find merge base between HEAD and {target_ref}."
        return result

    # Try modern merge-tree (git >= 2.38)
    modern = _run_git(["merge-tree", "--write-tree", "--no-messages", merge_base, "HEAD", target_ref])

    if modern.returncode == 0:
        return result  # clean merge

    if modern.returncode == 1:
        conflicts = _parse_conflicts_new(modern.stdout, modern.stderr)
        if conflicts:
            result.conflicts = conflicts
            return result

    # Fallback to classic merge-tree (git < 2.38)
    classic = _run_git(["merge-tree", merge_base, "HEAD", target_ref])
    if "<<<<<<" in classic.stdout:
        result.conflicts = _parse_conflicts_old(classic.stdout)
        if not result.conflicts:
            result.conflicts = [ConflictFile(path="(unknown)", reason="conflict markers found")]

    return result
