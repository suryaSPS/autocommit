import subprocess
from pathlib import Path
from typing import Optional, Tuple


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


def get_repo_name():
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return Path(result.stdout.strip()).name
    return None


def get_current_branch() -> Optional[str]:
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        branch = result.stdout.strip()
        return None if branch == "HEAD" else branch
    return None


def get_default_branch() -> str:
    """Detect the remote default branch (main, master, or develop)."""
    for branch in ("main", "master", "develop"):
        result = subprocess.run(
            ["git", "rev-parse", "--verify", f"origin/{branch}"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return branch
    return "main"


def get_commit_log(base: str, head: str = "HEAD", fmt: str = "%h %s") -> str:
    """Return a formatted log of commits between base and head."""
    result = subprocess.run(
        ["git", "log", f"{base}..{head}", f"--pretty=format:{fmt}"],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def get_full_diff_since(base: str) -> str:
    """Return the full diff of all changes since base ref."""
    result = subprocess.run(
        ["git", "diff", base, "HEAD"],
        capture_output=True,
        text=True,
    )
    return result.stdout if result.returncode == 0 else ""


def fetch_remote(branch: str) -> Tuple[bool, str]:
    """Fetch a remote branch. Returns (success, stderr)."""
    result = subprocess.run(
        ["git", "fetch", "origin", branch],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0, result.stderr
