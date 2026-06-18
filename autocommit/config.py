import json
from pathlib import Path

CONFIG_PATH = Path.home() / ".autocommit" / "config.json"

DEFAULTS = {
    "provider": "anthropic",
    "anthropic_model": "claude-sonnet-4-6",
    "openai_model": "gpt-4o-mini",
    "style": "conventional",
    "include_scope": True,
    "include_body": False,
    "emoji": False,
    "max_diff_lines": 500,
    "redact_secrets": True,
}


def load_config():
    config = DEFAULTS.copy()
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH) as f:
                loaded = json.load(f)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid config JSON at {CONFIG_PATH}: {exc}") from exc
        if not isinstance(loaded, dict):
            raise ValueError(f"Invalid config at {CONFIG_PATH}: expected a JSON object")
        config.update(loaded)
    return config


def save_config(config):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    # Never persist API keys to disk
    safe = {
        k: v
        for k, v in config.items()
        if "api_key" not in k.lower() and "secret" not in k.lower() and "token" not in k.lower()
    }
    with open(CONFIG_PATH, "w") as f:
        json.dump(safe, f, indent=2)
    return CONFIG_PATH
