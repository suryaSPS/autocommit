import shutil
import subprocess  # nosec B404
from pathlib import Path
from typing import Optional, Tuple


def _git_executable():
    git = shutil.which("git")
    if not git:
        raise RuntimeError("git executable not found on PATH")
    return git


def _run_git(args):
    # Args are fixed by this module; shell is never used.
    return subprocess.run(  # nosec B603
        [_git_executable(), *args],
        capture_output=True,
        text=True,
    )


def is_git_repo():
    result = _run_git(["rev-parse", "--is-inside-work-tree"])
    return result.returncode == 0


def get_staged_diff():
    result = _run_git(["diff", "--cached"])
    if result.returncode != 0:
        return None, result.stderr
    return result.stdout, None


def get_staged_files():
    result = _run_git(["diff", "--cached", "--name-only"])
    if result.returncode != 0:
        return [], result.stderr
    files = [f for f in result.stdout.strip().split("\n") if f]
    return files, None


def stage_all():
    result = _run_git(["add", "-A"])
    return result.returncode == 0, result.stderr


def make_commit(message):
    result = _run_git(["commit", "-m", message])
    return result.returncode == 0, result.stdout, result.stderr


def get_repo_name():
    result = _run_git(["rev-parse", "--show-toplevel"])
    if result.returncode == 0:
        return Path(result.stdout.strip()).name
    return None


def get_current_branch() -> Optional[str]:
    result = _run_git(["rev-parse", "--abbrev-ref", "HEAD"])
    if result.returncode == 0:
        branch = result.stdout.strip()
        return None if branch == "HEAD" else branch
    return None


def get_default_branch() -> str:
    """Detect the remote default branch (main, master, or develop)."""
    for branch in ("main", "master", "develop"):
        result = _run_git(["rev-parse", "--verify", f"origin/{branch}"])
        if result.returncode == 0:
            return branch
    return "main"


def get_commit_log(base: str, head: str = "HEAD", fmt: str = "%h %s") -> str:
    """Return a formatted log of commits between base and head."""
    result = _run_git(["log", f"{base}..{head}", f"--pretty=format:{fmt}"])
    return result.stdout.strip() if result.returncode == 0 else ""


def get_full_diff_since(base: str) -> str:
    """Return the full diff of all changes since base ref."""
    result = _run_git(["diff", base, "HEAD"])
    return result.stdout if result.returncode == 0 else ""


def fetch_remote(branch: str) -> Tuple[bool, str]:
    """Fetch a remote branch. Returns (success, stderr)."""
    result = _run_git(["fetch", "origin", branch])
    return result.returncode == 0, result.stderr


def ref_exists(ref: str) -> bool:
    result = _run_git(["rev-parse", "--verify", ref])
    return result.returncode == 0
