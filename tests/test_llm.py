import pytest

from autocommit.llm import clean_commit_message, generate, redact_sensitive_diff


def test_redact_sensitive_diff_masks_common_secret_shapes():
    diff = """
+API_KEY="sk-live-secret-value"
+github_token = ghp_123456789012345678901234567890123456
+password = hunter2
"""

    redacted = redact_sensitive_diff(diff)

    assert "sk-live-secret-value" not in redacted
    assert "ghp_123456789012345678901234567890123456" not in redacted
    assert "hunter2" not in redacted
    assert "[REDACTED]" in redacted


def test_clean_commit_message_removes_markdown_and_coauthors():
    message = """```text
feat(cli): add raw suggest command

Co-Authored-By: Someone <someone@example.com>
```"""

    assert clean_commit_message(message, include_body=True) == (
        "feat(cli): add raw suggest command"
    )


def test_clean_commit_message_rejects_empty_output():
    with pytest.raises(ValueError, match="empty commit message"):
        clean_commit_message("```")


def test_generate_cleans_provider_output(monkeypatch):
    monkeypatch.setattr(
        "autocommit.llm._call_anthropic",
        lambda prompt, config, max_tokens=300: "```text\nfix(cli): handle staging errors\n```",
    )

    message = generate("diff", ["autocommit/cli.py"], {"provider": "anthropic"})

    assert message == "fix(cli): handle staging errors"
