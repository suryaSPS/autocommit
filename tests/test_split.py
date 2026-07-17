import json
from unittest.mock import patch

from autocommit import split


FILES = ["auth/views.py", "auth/models.py", "tests/test_auth.py", "README.md", "pyproject.toml"]


def test_heuristic_groups_by_kind():
    groups = split.propose_groups(FILES)
    labels = [g.label for g in groups]
    assert labels == ["auth", "tests", "docs", "config"]
    by_label = {g.label: g.files for g in groups}
    assert set(by_label["auth"]) == {"auth/views.py", "auth/models.py"}
    assert by_label["tests"] == ["tests/test_auth.py"]
    assert by_label["docs"] == ["README.md"]
    assert by_label["config"] == ["pyproject.toml"]


def test_heuristic_source_scopes_split_separately():
    groups = split.propose_groups(["auth/a.py", "orders/b.py"])
    assert sorted(g.label for g in groups) == ["auth", "orders"]


def test_every_file_appears_exactly_once():
    groups = split.propose_groups(FILES)
    seen = [f for g in groups for f in g.files]
    assert sorted(seen) == sorted(FILES)


def test_ai_grouping_valid_json_used():
    raw = json.dumps(
        {
            "groups": [
                {"reason": "auth refactor", "files": ["auth/views.py", "auth/models.py"]},
                {"reason": "tests", "files": ["tests/test_auth.py"]},
                {"reason": "docs and config", "files": ["README.md", "pyproject.toml"]},
            ]
        }
    )
    with patch("autocommit.split.complete", return_value=raw):
        groups, used_ai = split.propose_groups_ai("diff", FILES, {"provider": "anthropic"})
    assert used_ai
    assert len(groups) == 3
    assert groups[0].reason == "auth refactor"


def test_ai_grouping_wrapped_in_prose_still_parses():
    raw = 'Here you go:\n```json\n{"groups": [{"reason": "all", "files": %s}]}\n```' % json.dumps(
        FILES
    )
    with patch("autocommit.split.complete", return_value=raw):
        groups, used_ai = split.propose_groups_ai("diff", FILES, {"provider": "anthropic"})
    assert used_ai
    assert len(groups) == 1


def test_ai_grouping_missing_file_falls_back():
    raw = json.dumps({"groups": [{"reason": "partial", "files": ["auth/views.py"]}]})
    with patch("autocommit.split.complete", return_value=raw):
        groups, used_ai = split.propose_groups_ai("diff", FILES, {"provider": "anthropic"})
    assert not used_ai  # fell back to heuristic
    seen = [f for g in groups for f in g.files]
    assert sorted(seen) == sorted(FILES)


def test_ai_grouping_invented_file_falls_back():
    raw = json.dumps({"groups": [{"reason": "bad", "files": FILES + ["ghost.py"]}]})
    with patch("autocommit.split.complete", return_value=raw):
        _, used_ai = split.propose_groups_ai("diff", FILES, {"provider": "anthropic"})
    assert not used_ai


def test_ai_grouping_garbage_falls_back():
    with patch("autocommit.split.complete", return_value="I cannot do that"):
        _, used_ai = split.propose_groups_ai("diff", FILES, {"provider": "anthropic"})
    assert not used_ai


def test_local_provider_never_calls_ai():
    with patch("autocommit.split.complete") as mock:
        _, used_ai = split.propose_groups_ai("diff", FILES, {"provider": "local"})
    assert not used_ai
    mock.assert_not_called()
