from types import SimpleNamespace
from unittest.mock import patch

from autocommit import git

from .conftest import make_diff


def _result(returncode=0, stdout="", stderr=""):
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


def test_is_git_repo_true():
    with patch("autocommit.git.subprocess.run", return_value=_result(0)):
        assert git.is_git_repo() is True


def test_is_git_repo_false():
    with patch("autocommit.git.subprocess.run", return_value=_result(128)):
        assert git.is_git_repo() is False


def test_get_staged_files_parses_names():
    out = "a.py\nb/c.py\n"
    with patch("autocommit.git.subprocess.run", return_value=_result(0, out)):
        files, err = git.get_staged_files()
    assert files == ["a.py", "b/c.py"]
    assert err is None


def test_get_staged_diff_error_returns_stderr():
    with patch("autocommit.git.subprocess.run", return_value=_result(1, "", "boom")):
        diff, err = git.get_staged_diff()
    assert diff is None
    assert err == "boom"


def test_make_commit_success():
    with patch("autocommit.git.subprocess.run", return_value=_result(0, "committed", "")):
        ok, out, err = git.make_commit("feat: x")
    assert ok is True
    assert out == "committed"


def test_get_current_branch():
    with patch("autocommit.git.subprocess.run", return_value=_result(0, "feature\n")):
        assert git.get_current_branch() == "feature"


def test_get_default_branch_from_origin_head():
    with patch("autocommit.git.subprocess.run", return_value=_result(0, "origin/main\n")):
        assert git.get_default_branch() == "main"


def test_get_default_branch_falls_back_to_main():
    calls = [_result(1)]  # symbolic-ref fails

    def side_effect(args, **kwargs):
        if args[:2] == ["git", "symbolic-ref"]:
            return _result(1)
        if "main" in args:
            return _result(0)
        return _result(1)

    with patch("autocommit.git.subprocess.run", side_effect=side_effect):
        assert git.get_default_branch() == "main"
    assert calls  # keep linter calm


def test_get_branch_commits_oldest_first():
    out = "feat: a\nfix: b\n"
    with patch("autocommit.git.subprocess.run", return_value=_result(0, out)):
        commits, err = git.get_branch_commits("main")
    assert commits == ["feat: a", "fix: b"]
    assert err is None


def test_get_branch_diff():
    diff = make_diff("a.py", ["x = 1"])
    with patch("autocommit.git.subprocess.run", return_value=_result(0, diff)):
        out, err = git.get_branch_diff("main")
    assert out == diff
    assert err is None
