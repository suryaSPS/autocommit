from unittest.mock import patch

from autocommit.review import offline_review, review

from .conftest import make_diff


def test_offline_detects_debug_statement():
    issues = offline_review(make_diff("a.py", ["print('debugging')"]))
    assert any(i.kind == "debug statement" for i in issues)


def test_offline_detects_todo():
    issues = offline_review(make_diff("a.py", ["x = 1  # TODO fix this"]))
    assert any(i.kind == "new TODO/FIXME" for i in issues)


def test_offline_detects_conflict_marker():
    diff = make_diff("a.py", ["<<<<<<< HEAD"])
    issues = offline_review(diff)
    assert any(i.kind == "merge conflict marker" for i in issues)


def test_offline_clean_diff():
    issues = offline_review(make_diff("a.py", ["def f():", "    return 42"]))
    assert issues == []


def test_review_local_returns_offline_flag():
    text, is_offline = review("diff", ["a.py"], {"provider": "local"})
    assert text is None
    assert is_offline is True


def test_review_ai_calls_complete():
    with patch("autocommit.review.complete", return_value="No issues found.") as mock:
        text, is_offline = review("some diff", ["a.py"], {"provider": "anthropic"})
    assert is_offline is False
    assert text == "No issues found."
    mock.assert_called_once()
