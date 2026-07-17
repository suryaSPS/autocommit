from unittest.mock import patch

import pytest

from autocommit import llm, providers

from .conftest import make_diff


def test_local_providers_constant():
    assert "local" in llm.LOCAL_PROVIDERS


def test_heuristic_new_file_is_feat():
    diff = make_diff("auth/login.py", ["def login():", "    pass"], new_file=True)
    msg = llm.generate(diff, ["auth/login.py"], {"provider": "local", "style": "conventional"})
    assert msg.startswith("feat")
    assert "login" in msg


def test_heuristic_docs():
    diff = make_diff("README.md", ["# Title"], new_file=True)
    msg = llm.generate(diff, ["README.md"], {"provider": "local"})
    assert msg.startswith("docs")


def test_heuristic_respects_line_length():
    diff = make_diff("a.py", ["x = 1"], new_file=True)
    msg = llm.generate(diff, ["a.py"], {"provider": "local"})
    assert len(msg) <= 72


def test_complete_dispatches_to_anthropic():
    with patch.object(providers.PROVIDERS["anthropic"], "complete", return_value="msg") as mock:
        out = llm.complete("prompt", {"provider": "anthropic"}, max_tokens=100)
    assert out == "msg"
    mock.assert_called_once()


def test_complete_dispatches_to_ollama():
    with patch.object(providers.PROVIDERS["ollama"], "complete", return_value="msg") as mock:
        out = llm.complete("prompt", {"provider": "ollama"})
    assert out == "msg"
    mock.assert_called_once()


def test_complete_unknown_provider_raises():
    with pytest.raises(ValueError):
        llm.complete("prompt", {"provider": "nope"})


def test_generate_ai_provider_calls_complete():
    with patch("autocommit.llm.complete", return_value="feat: thing") as mock:
        out = llm.generate("diff", ["a.py"], {"provider": "anthropic"})
    assert out == "feat: thing"
    mock.assert_called_once()


def test_anthropic_missing_key_raises(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(EnvironmentError):
        providers.PROVIDERS["anthropic"].complete("prompt", {}, 100)


def test_custom_provider_registration():
    class FakeProvider(providers.LLMProvider):
        name = "fake"

        def complete(self, prompt, config, max_tokens=1024):
            return "from-fake"

    providers.register(FakeProvider())
    try:
        assert llm.complete("prompt", {"provider": "fake"}) == "from-fake"
    finally:
        del providers.PROVIDERS["fake"]


def test_prompt_includes_recent_commit_style():
    prompt = llm._build_prompt(
        "diff", ["a.py"], {}, recent_subjects=["feat(core): add thing", "fix(cli): handle x"]
    )
    assert "feat(core): add thing" in prompt
    assert "match their tone" in prompt


def test_prompt_omits_recent_block_when_empty():
    prompt = llm._build_prompt("diff", ["a.py"], {}, recent_subjects=[])
    assert "match their tone" not in prompt
