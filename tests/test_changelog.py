from autocommit.changelog import build_changelog, group_commits


SUBJECTS = [
    "feat(auth): add OAuth callback",
    "fix(cli): handle empty diff",
    "feat!: drop python 3.8 support",
    "docs: update README",
    "random non-conventional commit",
    "chore: bump deps",
]


def test_group_commits_by_type():
    sections, breaking, other = group_commits(SUBJECTS)
    assert "**auth:** add OAuth callback" in sections["Features"]
    assert "**cli:** handle empty diff" in sections["Bug Fixes"]
    assert sections["Documentation"] == ["update README"]
    assert sections["Chores"] == ["bump deps"]


def test_breaking_changes_detected():
    _, breaking, _ = group_commits(SUBJECTS)
    assert breaking == ["drop python 3.8 support"]


def test_non_conventional_goes_to_other():
    _, _, other = group_commits(SUBJECTS)
    assert other == ["random non-conventional commit"]


def test_build_changelog_structure():
    md = build_changelog(SUBJECTS, label="v1.0.0", date="2026-07-17")
    assert md.startswith("## v1.0.0 (2026-07-17)")
    assert md.index("Breaking Changes") < md.index("### Features")
    assert md.index("### Features") < md.index("### Bug Fixes")
    assert "### Other" in md


def test_build_changelog_deterministic():
    a = build_changelog(SUBJECTS, label="x", date="2026-01-01")
    b = build_changelog(SUBJECTS, label="x", date="2026-01-01")
    assert a == b


def test_empty_history():
    md = build_changelog([], label="v0", date="2026-01-01")
    assert "_No changes._" in md
