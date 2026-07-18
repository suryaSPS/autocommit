from rich.console import Console

from autocommit import onboarding


def test_is_first_run(tmp_path):
    cfg = tmp_path / "config.json"
    assert onboarding.is_first_run(cfg) is True
    cfg.write_text("{}")
    assert onboarding.is_first_run(cfg) is False


def _patch_config_path(monkeypatch, tmp_path):
    """Point save_config at a temp file so tests never touch the real ~/.autocommit."""
    monkeypatch.setattr("autocommit.config.CONFIG_PATH", tmp_path / "config.json")


def test_onboarding_local_provider(monkeypatch, tmp_path):
    _patch_config_path(monkeypatch, tmp_path)
    monkeypatch.setattr("click.prompt", lambda *a, **k: "local")

    run_config = onboarding.run_onboarding(Console(), {})
    assert run_config["provider"] == "local"
    assert (tmp_path / "config.json").exists()


def test_onboarding_key_used_for_session_not_persisted(monkeypatch, tmp_path):
    _patch_config_path(monkeypatch, tmp_path)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    answers = iter(["anthropic", "sk-ant-secret"])
    monkeypatch.setattr("click.prompt", lambda *a, **k: next(answers))

    run_config = onboarding.run_onboarding(Console(), {})

    assert run_config["provider"] == "anthropic"  # real choice kept
    assert onboarding.os.environ["ANTHROPIC_API_KEY"] == "sk-ant-secret"  # session only
    saved = (tmp_path / "config.json").read_text()
    assert "sk-ant-secret" not in saved  # never written to disk


def test_onboarding_no_key_falls_back_to_local_this_run(monkeypatch, tmp_path):
    _patch_config_path(monkeypatch, tmp_path)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    answers = iter(["anthropic", ""])  # choose anthropic, skip the key
    monkeypatch.setattr("click.prompt", lambda *a, **k: next(answers))

    run_config = onboarding.run_onboarding(Console(), {})

    assert run_config["provider"] == "local"  # this run falls back
    import json

    saved = json.loads((tmp_path / "config.json").read_text())
    assert saved["provider"] == "anthropic"  # but the choice is remembered
