from autocommit.secrets import scan_diff

from .conftest import make_diff


def test_detects_aws_key():
    diff = make_diff("config.py", ["aws_key = 'AKIA" + "TESTTESTTESTTEST'"], new_file=True)
    findings = scan_diff(diff)
    assert len(findings) == 1
    assert findings[0].rule == "AWS access key ID"
    assert findings[0].file == "config.py"
    assert findings[0].line == 1


def test_detects_github_token():
    token = "ghp_" + "0123456789012345678901234567890123456"
    findings = scan_diff(make_diff("a.py", [f"tok = '{token}'"]))
    assert findings and findings[0].rule == "GitHub token"


def test_detects_hardcoded_password():
    findings = scan_diff(make_diff("a.py", ["password = 'hunter2secret'"]))
    assert findings and findings[0].rule == "Hardcoded credential assignment"


def test_preview_is_redacted():
    secret = "AKIA" + "TESTTESTTESTTEST"
    findings = scan_diff(make_diff("a.py", [f"k = '{secret}'"]))
    assert secret not in findings[0].preview
    assert "…" in findings[0].preview


def test_ignores_placeholders():
    diff = make_diff("a.py", ["password = 'your_password_here'"])
    assert scan_diff(diff) == []


def test_ignores_removed_lines():
    # A secret on a removed (-) line should not be flagged.
    diff = (
        "diff --git a/a.py b/a.py\n"
        "--- a/a.py\n+++ b/a.py\n"
        "@@ -1,1 +1,1 @@\n"
        "-key = 'AKIA" + "TESTTESTTESTTEST'\n"
        "+key = os.environ['KEY']\n"
    )
    assert scan_diff(diff) == []


def test_clean_diff_has_no_findings():
    diff = make_diff("a.py", ["def add(a, b):", "    return a + b"], new_file=True)
    assert scan_diff(diff) == []


def test_line_numbers_track_hunk_header():
    diff = (
        "diff --git a/a.py b/a.py\n"
        "--- a/a.py\n+++ b/a.py\n"
        "@@ -10,2 +10,3 @@\n"
        " context\n"
        "+password = 'realsecret123'\n"
        " more context\n"
    )
    findings = scan_diff(diff)
    assert findings and findings[0].line == 11
