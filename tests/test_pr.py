from unittest.mock import patch

from autocommit.pr import write_pr


def test_offline_pr_from_commits():
    title, body = write_pr(
        "feature", "main", ["feat: add x", "fix: correct y"], "diff", {"provider": "local"}
    )
    assert title == "fix: correct y"
    assert "## Summary" in body
    assert "- feat: add x" in body
    assert "- fix: correct y" in body
    assert "## Testing" in body


def test_offline_pr_no_commits():
    title, body = write_pr("feature", "main", [], "", {"provider": "local"})
    assert "Merge feature into main" == title
    assert "no commits found" in body


def test_offline_pr_truncates_long_title():
    long = "feat: " + "x" * 100
    title, _ = write_pr("f", "main", [long], "", {"provider": "local"})
    assert len(title) <= 72
    assert title.endswith("...")


def test_ai_pr_parses_title_and_body():
    raw = "TITLE: add feature flag support\n\n## Summary\nAdds flags.\n"
    with patch("autocommit.pr.complete", return_value=raw):
        title, body = write_pr("f", "main", ["feat: flags"], "diff", {"provider": "anthropic"})
    assert title == "add feature flag support"
    assert body.startswith("## Summary")


def test_ai_pr_falls_back_when_no_title_line():
    with patch("autocommit.pr.complete", return_value="just some prose"):
        title, body = write_pr("f", "main", ["feat: flags"], "diff", {"provider": "anthropic"})
    # Falls back to the offline title derived from commits
    assert title == "feat: flags"
