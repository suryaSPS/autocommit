from click.testing import CliRunner

from autocommit import cli as cli_module


def _use_default_config(monkeypatch):
    monkeypatch.setattr(cli_module, "load_config", lambda: {"provider": "anthropic"})


def test_yes_commits_generated_message(monkeypatch):
    _use_default_config(monkeypatch)
    monkeypatch.setattr(cli_module, "is_git_repo", lambda: True)
    monkeypatch.setattr(cli_module, "get_staged_diff", lambda: ("diff", None))
    monkeypatch.setattr(cli_module, "get_staged_files", lambda: (["app.py"], None))
    monkeypatch.setattr(cli_module, "generate", lambda diff, files, config: "feat(app): add demo")

    committed = {}

    def fake_commit(message):
        committed["message"] = message
        return True, "created commit", ""

    monkeypatch.setattr(cli_module, "make_commit", fake_commit)

    result = CliRunner().invoke(cli_module.cli, ["--yes"])

    assert result.exit_code == 0
    assert committed["message"] == "feat(app): add demo"
    assert "Committed successfully" in result.output


def test_stage_all_failure_exits(monkeypatch):
    _use_default_config(monkeypatch)
    monkeypatch.setattr(cli_module, "is_git_repo", lambda: True)
    monkeypatch.setattr(cli_module, "stage_all", lambda: (False, "permission denied"))

    result = CliRunner().invoke(cli_module.cli, ["--all"])

    assert result.exit_code == 1
    assert "Failed to stage files" in result.output


def test_suggest_prints_raw_message(monkeypatch):
    _use_default_config(monkeypatch)
    monkeypatch.setattr(cli_module, "is_git_repo", lambda: True)
    monkeypatch.setattr(cli_module, "get_staged_diff", lambda: ("diff", None))
    monkeypatch.setattr(cli_module, "get_staged_files", lambda: (["app.py"], None))
    monkeypatch.setattr(cli_module, "generate", lambda diff, files, config: "fix(app): repair demo")

    result = CliRunner().invoke(cli_module.cli, ["suggest"])

    assert result.exit_code == 0
    assert result.output == "fix(app): repair demo\n"


def test_install_hook_writes_message_file_script(tmp_path, monkeypatch):
    hooks_dir = tmp_path / ".git" / "hooks"
    hooks_dir.mkdir(parents=True)
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(cli_module.cli, ["install-hook"])

    hook = hooks_dir / "prepare-commit-msg"
    script = hook.read_text()
    assert result.exit_code == 0
    assert 'autocommit suggest > "$COMMIT_MSG_FILE"' in script
    assert "autocommit --yes" not in script
