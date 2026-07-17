from unittest.mock import patch

from autocommit.explain import explain


def test_explain_local_provider_returns_none():
    assert explain("diff", ["a.py"], {"provider": "local"}) is None


def test_explain_calls_complete_with_diff():
    with patch("autocommit.explain.complete", return_value="## What changed\nStuff.") as mock:
        out = explain("some-diff", ["a.py"], {"provider": "anthropic"})
    assert out.startswith("## What changed")
    prompt = mock.call_args[0][0]
    assert "some-diff" in prompt
    assert "a.py" in prompt
