import json

from autocommit import config as config_mod


def test_defaults_present():
    d = config_mod.DEFAULTS
    assert d["provider"] == "anthropic"
    assert d["scan_secrets"] is True
    assert d["ollama_model"]
    assert d["ollama_host"].startswith("http")


def test_load_returns_defaults_when_no_file(tmp_path, monkeypatch):
    monkeypatch.setattr(config_mod, "CONFIG_PATH", tmp_path / "config.json")
    cfg = config_mod.load_config()
    assert cfg["provider"] == "anthropic"
    assert cfg["scan_secrets"] is True


def test_load_merges_file_over_defaults(tmp_path, monkeypatch):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"provider": "ollama", "style": "simple"}))
    monkeypatch.setattr(config_mod, "CONFIG_PATH", path)
    cfg = config_mod.load_config()
    assert cfg["provider"] == "ollama"
    assert cfg["style"] == "simple"
    # untouched keys still come from defaults
    assert cfg["scan_secrets"] is True


def test_save_strips_api_keys(tmp_path, monkeypatch):
    path = tmp_path / "config.json"
    monkeypatch.setattr(config_mod, "CONFIG_PATH", path)
    config_mod.save_config({"provider": "openai", "openai_api_key": "sk-secret"})
    saved = json.loads(path.read_text())
    assert "openai_api_key" not in saved
    assert saved["provider"] == "openai"
