"""Shared fixtures and helpers for the test suite."""


def make_diff(path, added_lines, new_file=False):
    """Build a minimal unified diff that adds `added_lines` to `path`."""
    header = f"diff --git a/{path} b/{path}\n"
    if new_file:
        header += "new file mode 100644\nindex 0000000..1111111\n--- /dev/null\n"
    else:
        header += "index 1111111..2222222 100644\n--- a/{0}\n".format(path)
    header += f"+++ b/{path}\n"
    hunk = f"@@ -0,0 +1,{len(added_lines)} @@\n"
    body = "".join(f"+{line}\n" for line in added_lines)
    return header + hunk + body
