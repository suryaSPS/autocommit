import subprocess
from pathlib import Path


def is_git_repo():
    result = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def get_staged_diff():
    result = subprocess.run(
        ["git", "diff", "--cached"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None, result.stderr
    return result.stdout, None


def get_staged_files():
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return [], result.stderr
    files = [f for f in result.stdout.strip().split("\n") if f]
    return files, None


def stage_all():
    result = subprocess.run(["git", "add", "-A"], capture_output=True, text=True)
    return result.returncode == 0


def make_commit(message):
    result = subprocess.run(
        ["git", "commit", "-m", message],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0, result.stdout, result.stderr


def get_current_branch():
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def get_default_branch():
    """Best-effort base branch: origin/HEAD if set, else main/master if they exist."""
    result = subprocess.run(
        ["git", "symbolic-ref", "--short", "refs/remotes/origin/HEAD"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return result.stdout.strip().removeprefix("origin/")
    for name in ("main", "master"):
        check = subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", name],
            capture_output=True,
            text=True,
        )
        if check.returncode == 0:
            return name
    return None


def get_branch_commits(base):
    """Commit subjects on HEAD that are not on base, oldest first."""
    result = subprocess.run(
        ["git", "log", "--reverse", "--pretty=%s", f"{base}..HEAD"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return [], result.stderr
    return [ln for ln in result.stdout.strip().split("\n") if ln], None


def get_branch_diff(base):
    """Diff of HEAD against the merge-base with base (what a PR would show)."""
    result = subprocess.run(
        ["git", "diff", f"{base}...HEAD"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None, result.stderr
    return result.stdout, None


def get_recent_commit_subjects(n=20):
    """Subjects of the last n commits, newest first. Empty list on any failure."""
    result = subprocess.run(
        ["git", "log", f"-{n}", "--pretty=%s"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return []
    return [ln for ln in result.stdout.strip().split("\n") if ln]


def get_last_tag():
    result = subprocess.run(
        ["git", "describe", "--tags", "--abbrev=0"],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def get_commit_subjects_since(ref):
    """Subjects after ref (exclusive) up to HEAD, oldest first. ref=None -> all commits."""
    rev_range = f"{ref}..HEAD" if ref else "HEAD"
    result = subprocess.run(
        ["git", "log", "--reverse", "--pretty=%s", rev_range],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return [], result.stderr
    return [ln for ln in result.stdout.strip().split("\n") if ln], None


def get_unstaged_files():
    result = subprocess.run(
        ["git", "diff", "--name-only"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return []
    return [f for f in result.stdout.strip().split("\n") if f]


def unstage_all():
    result = subprocess.run(["git", "reset", "-q"], capture_output=True, text=True)
    return result.returncode == 0


def stage_files(files):
    result = subprocess.run(["git", "add", "--", *files], capture_output=True, text=True)
    return result.returncode == 0


def get_repo_name():
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return Path(result.stdout.strip()).name
    return None
