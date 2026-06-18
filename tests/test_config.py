import json

import pytest

from autocommit import config as config_module


def test_load_config_rejects_invalid_json(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    config_path.write_text("{invalid")
    monkeypatch.setattr(config_module, "CONFIG_PATH", config_path)

    with pytest.raises(ValueError, match="Invalid config JSON"):
        config_module.load_config()


def test_save_config_filters_secret_like_keys(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    monkeypatch.setattr(config_module, "CONFIG_PATH", config_path)

    config_module.save_config(
        {
            "provider": "openai",
            "api_key": "sk-test",
            "access_token": "token",
            "client_secret": "secret",
        }
    )

    saved = json.loads(config_path.read_text())
    assert saved == {"provider": "openai"}
