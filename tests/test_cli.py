from unittest.mock import patch

from click.testing import CliRunner

from autocommit.cli import cli

from .conftest import make_diff

SECRET_DIFF = make_diff("config.py", ["aws = 'AKIA" + "TESTTESTTESTTEST'"], new_file=True)
CLEAN_DIFF = make_diff("app.py", ["def run():", "    return 1"], new_file=True)


def _cfg(**over):
    base = {"provider": "local", "scan_secrets": True, "style": "conventional", "max_diff_lines": 500}
    base.update(over)
    return base


def test_version():
    result = CliRunner().invoke(cli, ["version"])
    assert result.exit_code == 0
    assert "autocommit" in result.output


def test_scan_clean_exits_zero():
    with patch("autocommit.cli.is_git_repo", return_value=True), patch(
        "autocommit.cli.get_staged_diff", return_value=(CLEAN_DIFF, None)
    ):
        result = CliRunner().invoke(cli, ["scan"])
    assert result.exit_code == 0
    assert "No secrets" in result.output


def test_scan_finds_secret_exits_one():
    with patch("autocommit.cli.is_git_repo", return_value=True), patch(
        "autocommit.cli.get_staged_diff", return_value=(SECRET_DIFF, None)
    ):
        result = CliRunner().invoke(cli, ["scan"])
    assert result.exit_code == 1
    assert "AWS access key ID" in result.output


def test_scan_outside_repo():
    with patch("autocommit.cli.is_git_repo", return_value=False):
        result = CliRunner().invoke(cli, ["scan"])
    assert result.exit_code == 1
    assert "Not inside a git repository" in result.output


def test_commit_gate_blocks_secret_under_yes():
    with patch("autocommit.cli.is_git_repo", return_value=True), patch(
        "autocommit.cli.load_config", return_value=_cfg()
    ), patch("autocommit.cli.get_staged_diff", return_value=(SECRET_DIFF, None)), patch(
        "autocommit.cli.get_staged_files", return_value=(["config.py"], None)
    ), patch("autocommit.cli.make_commit") as commit:
        result = CliRunner().invoke(cli, ["--no-ai", "-y"])
    assert result.exit_code == 1
    assert "Secrets detected" in result.output
    commit.assert_not_called()


def test_commit_clean_commits_under_yes():
    with patch("autocommit.cli.is_git_repo", return_value=True), patch(
        "autocommit.cli.load_config", return_value=_cfg()
    ), patch("autocommit.cli.get_staged_diff", return_value=(CLEAN_DIFF, None)), patch(
        "autocommit.cli.get_staged_files", return_value=(["app.py"], None)
    ), patch("autocommit.cli.make_commit", return_value=(True, "ok", "")) as commit:
        result = CliRunner().invoke(cli, ["--no-ai", "-y"])
    assert result.exit_code == 0
    commit.assert_called_once()


def test_scan_secrets_disabled_allows_commit():
    with patch("autocommit.cli.is_git_repo", return_value=True), patch(
        "autocommit.cli.load_config", return_value=_cfg(scan_secrets=False)
    ), patch("autocommit.cli.get_staged_diff", return_value=(SECRET_DIFF, None)), patch(
        "autocommit.cli.get_staged_files", return_value=(["config.py"], None)
    ), patch("autocommit.cli.make_commit", return_value=(True, "ok", "")) as commit:
        result = CliRunner().invoke(cli, ["--no-ai", "-y"])
    assert result.exit_code == 0
    commit.assert_called_once()


def test_review_offline():
    diff = make_diff("a.py", ["print('debug')"], new_file=True)
    with patch("autocommit.cli.is_git_repo", return_value=True), patch(
        "autocommit.cli.load_config", return_value=_cfg()
    ), patch("autocommit.cli.get_staged_diff", return_value=(diff, None)), patch(
        "autocommit.cli.get_staged_files", return_value=(["a.py"], None)
    ):
        result = CliRunner().invoke(cli, ["review", "--no-ai"])
    assert result.exit_code == 0
    assert "debug statement" in result.output


def test_review_offline_clean():
    diff = make_diff("a.py", ["x = 1"], new_file=True)
    with patch("autocommit.cli.is_git_repo", return_value=True), patch(
        "autocommit.cli.load_config", return_value=_cfg()
    ), patch("autocommit.cli.get_staged_diff", return_value=(diff, None)), patch(
        "autocommit.cli.get_staged_files", return_value=(["a.py"], None)
    ):
        result = CliRunner().invoke(cli, ["review", "--no-ai"])
    assert result.exit_code == 0
    assert "No obvious issues" in result.output


def test_pr_offline():
    diff = make_diff("a.py", ["x = 1"], new_file=True)
    with patch("autocommit.cli.is_git_repo", return_value=True), patch(
        "autocommit.cli.load_config", return_value=_cfg()
    ), patch("autocommit.cli.get_current_branch", return_value="feature"), patch(
        "autocommit.cli.get_default_branch", return_value="main"
    ), patch("autocommit.cli.get_branch_commits", return_value=(["feat: add a"], None)), patch(
        "autocommit.cli.get_branch_diff", return_value=(diff, None)
    ):
        result = CliRunner().invoke(cli, ["pr", "--no-ai"])
    assert result.exit_code == 0
    assert "feat: add a" in result.output


def test_pr_base_equals_branch():
    with patch("autocommit.cli.is_git_repo", return_value=True), patch(
        "autocommit.cli.load_config", return_value=_cfg()
    ), patch("autocommit.cli.get_current_branch", return_value="main"), patch(
        "autocommit.cli.get_default_branch", return_value="main"
    ):
        result = CliRunner().invoke(cli, ["pr", "--no-ai"])
    assert result.exit_code == 1
    assert "base branch" in result.output


def test_provider_choice_includes_ollama():
    result = CliRunner().invoke(cli, ["--help"])
    assert "ollama" in result.output
