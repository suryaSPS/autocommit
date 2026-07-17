import json
from pathlib import Path

CONFIG_PATH = Path.home() / ".autocommit" / "config.json"

DEFAULTS = {
    "provider": "anthropic",
    "anthropic_model": "claude-opus-4-8",
    "openai_model": "gpt-4o-mini",
    "ollama_model": "llama3.2",
    "ollama_host": "http://localhost:11434",
    "style": "conventional",
    "include_scope": True,
    "include_body": False,
    "emoji": False,
    "max_diff_lines": 500,
    "scan_secrets": True,
}


def load_config():
    config = DEFAULTS.copy()
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            config.update(json.load(f))
    return config


def save_config(config):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    # Never persist API keys to disk
    safe = {k: v for k, v in config.items() if "api_key" not in k}
    with open(CONFIG_PATH, "w") as f:
        json.dump(safe, f, indent=2)
    return CONFIG_PATH
