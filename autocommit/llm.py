import os
from pathlib import PurePosixPath


STYLE_INSTRUCTIONS = {
    "conventional": """\
Generate a conventional commit message.

Format:  <type>(<scope>): <description>

Types: feat, fix, docs, style, refactor, test, chore, perf, ci, build
- feat: a new feature
- fix: a bug fix
- refactor: code change that neither fixes a bug nor adds a feature
- chore: tooling, deps, config changes
- docs: documentation only
- perf: performance improvement
- test: adding or fixing tests

Rules:
- First line must be under 72 characters
- Description is lowercase, no trailing period
- Scope is the module or component affected (e.g. auth, orders, cli)""",
    "angular": """\
Generate an Angular-style commit message.

Format:  <type>(<scope>): <subject>

Types: feat, fix, docs, style, refactor, test, chore
Subject is imperative, present tense, lowercase, no trailing period.
First line under 72 characters.""",
    "simple": """\
Generate a short, plain-English commit message.
No special format. Imperative mood. Under 72 characters.
Example: "Add user authentication" or "Fix null pointer in order view" """,
}


def _build_prompt(diff, files, config):
    style = config.get("style", "conventional")
    include_scope = config.get("include_scope", True)
    include_body = config.get("include_body", False)
    emoji = config.get("emoji", False)

    files_str = "\n".join(f"  - {f}" for f in files)
    style_block = STYLE_INSTRUCTIONS.get(style, STYLE_INSTRUCTIONS["conventional"])

    scope_note = "" if include_scope else "Do NOT include a scope."
    body_note = (
        "After the first line, add one blank line then a short body explaining WHY (not what) the change was made."
        if include_body
        else "Do NOT include a body. First line only."
    )
    emoji_note = (
        "Prepend a single relevant emoji before the type (e.g. ✨ feat, 🐛 fix, ♻️ refactor)."
        if emoji
        else ""
    )

    return f"""You are an expert developer writing a git commit message.

Changed files:
{files_str}

Staged diff:
```
{diff}
```

{style_block}
{scope_note}
{body_note}
{emoji_note}

Additional rules:
- Be specific, not generic ("fix bug" is bad, "fix null check in order serializer" is good)
- Output ONLY the commit message — no explanation, no markdown, no backticks
- Never include Co-Authored-By lines"""


LOCAL_PROVIDERS = ("local", "none", "heuristic")


def complete(prompt, config, max_tokens=1024):
    """Send a prompt to the configured AI provider and return the text response.

    Shared by every AI feature (commit messages, review, PR descriptions).
    Local/heuristic mode has no completion backend — callers handle it themselves.
    """
    provider = config.get("provider", "anthropic")
    if provider == "anthropic":
        return _anthropic(prompt, config, max_tokens)
    if provider == "openai":
        return _openai(prompt, config, max_tokens)
    if provider == "ollama":
        return _ollama(prompt, config)
    raise ValueError(f"Unknown provider: {provider}")


def generate(diff, files, config):
    provider = config.get("provider", "anthropic")
    if provider in LOCAL_PROVIDERS:
        return _heuristic(diff, files, config)
    return complete(_build_prompt(diff, files, config), config, max_tokens=300)


# ──────────────────────────────────────────────────────────────────────────────
# Local heuristic generator — no API key, no network, works fully offline
# ──────────────────────────────────────────────────────────────────────────────

EMOJI = {
    "feat": "✨",
    "fix": "🐛",
    "docs": "📝",
    "refactor": "♻️",
    "test": "✅",
    "chore": "🔧",
}

GENERIC_DIRS = {"src", "lib", "app", "source", "pkg", "internal", "."}

DOC_STEMS = {"readme", "license", "licence", "changelog", "contributing", "authors", "notice"}
DOC_EXTS = {".md", ".rst", ".txt", ".adoc"}

CONFIG_EXTS = {".toml", ".yml", ".yaml", ".ini", ".cfg", ".lock", ".json", ".conf"}
CONFIG_NAMES = {
    "dockerfile",
    "makefile",
    ".gitignore",
    ".dockerignore",
    ".editorconfig",
    "requirements.txt",
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "package.json",
    "package-lock.json",
    "yarn.lock",
    "poetry.lock",
    "cargo.toml",
    "go.mod",
    "go.sum",
}


def _is_test(path):
    p = path.lower()
    name = PurePosixPath(p).name
    return (
        "/test" in p
        or p.startswith("test")
        or "/tests/" in p
        or name.startswith("test_")
        or name.endswith("_test.py")
        or ".test." in name
        or ".spec." in name
    )


def _is_doc(path):
    p = PurePosixPath(path.lower())
    return p.stem in DOC_STEMS or p.suffix in DOC_EXTS or "docs/" in path.lower()


def _is_config(path):
    p = PurePosixPath(path.lower())
    return p.name in CONFIG_NAMES or p.suffix in CONFIG_EXTS


def _parse_diff_status(diff):
    """Map each file path to 'A' (added), 'D' (deleted), or 'M' (modified)."""
    status = {}
    current = None
    for line in diff.split("\n"):
        if line.startswith("diff --git "):
            _, _, rest = line.partition(" b/")
            current = rest or None
            if current:
                status[current] = "M"
        elif current and line.startswith("new file mode"):
            status[current] = "A"
        elif current and line.startswith("deleted file mode"):
            status[current] = "D"
    return status


def _count_lines(diff):
    adds = sum(1 for ln in diff.split("\n") if ln.startswith("+") and not ln.startswith("+++"))
    dels = sum(1 for ln in diff.split("\n") if ln.startswith("-") and not ln.startswith("---"))
    return adds, dels


def _infer_type(files, added, deleted, adds, dels):
    if files and all(_is_test(f) for f in files):
        return "test"
    if files and all(_is_doc(f) for f in files):
        return "docs"
    if files and all(_is_config(f) for f in files):
        return "chore"
    if added and not [f for f in files if f not in added]:
        return "feat"  # only brand-new files
    if deleted and len(deleted) == len(files):
        return "chore"  # pure removals
    if adds > dels * 3:
        return "feat"
    if dels > adds * 3:
        return "refactor"
    return "fix"


def _deepest_scope(parts):
    for comp in reversed(list(parts)):
        c = comp.lower()
        if c and c not in GENERIC_DIRS and not c.startswith("."):
            return c
    return None


def _infer_scope(files):
    if len(files) == 1:
        return _deepest_scope(PurePosixPath(files[0]).parent.parts)
    try:
        common = os.path.commonpath(files)
    except ValueError:
        return None
    return _deepest_scope([p for p in common.split("/") if p])


def _display_name(path):
    p = PurePosixPath(path)
    return p.stem or p.name


def _join(items):
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def _name_list(files, limit=2):
    names = list(dict.fromkeys(_display_name(f) for f in files))
    if len(names) <= limit:
        return _join(names)
    return f"{len(files)} files"


def _build_subject(ctype, files, added, deleted):
    if deleted and len(deleted) == len(files):
        return f"remove {_name_list(deleted)}"

    verb = {
        "feat": "add",
        "fix": "fix",
        "docs": "update",
        "test": "add",
        "chore": "update",
        "refactor": "refactor",
    }.get(ctype, "update")

    if len(files) == 1:
        name = _display_name(files[0])
        if files[0] in added:
            return f"add {name}"
        return f"{verb} {name}"

    return f"{verb} {_name_list(files)}"


def _format_message(ctype, scope, subject, config):
    style = config.get("style", "conventional")
    if style == "simple":
        msg = subject[:1].upper() + subject[1:]
    else:
        head = f"{ctype}({scope})" if scope else ctype
        prefix = f"{EMOJI[ctype]} " if config.get("emoji") and ctype in EMOJI else ""
        msg = f"{prefix}{head}: {subject}"
    return msg[:72]


def _heuristic(diff, files, config):
    status = _parse_diff_status(diff)
    for f in files:  # binary / untracked files may not appear in the diff body
        status.setdefault(f, "M")

    added = [f for f in files if status.get(f) == "A"]
    deleted = [f for f in files if status.get(f) == "D"]
    adds, dels = _count_lines(diff)

    ctype = _infer_type(files, added, deleted, adds, dels)
    scope = _infer_scope(files) if config.get("include_scope", True) else None
    subject = _build_subject(ctype, files, added, deleted)
    return _format_message(ctype, scope, subject, config)


def _anthropic(prompt, config, max_tokens):
    try:
        import anthropic
    except ImportError:
        raise ImportError("Install the Anthropic SDK:  pip install anthropic")

    if not os.getenv("ANTHROPIC_API_KEY"):
        raise EnvironmentError(
            "ANTHROPIC_API_KEY is not set.\nExport it:  export ANTHROPIC_API_KEY=sk-ant-..."
        )

    client = anthropic.Anthropic()
    message = client.messages.create(
        model=config.get("anthropic_model", "claude-opus-4-8"),
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    text = next((b.text for b in message.content if b.type == "text"), "")
    return text.strip()


def _openai(prompt, config, max_tokens):
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError("Install the OpenAI SDK:  pip install openai")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "OPENAI_API_KEY is not set.\nExport it:  export OPENAI_API_KEY=sk-..."
        )

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=config.get("openai_model", "gpt-4o-mini"),
        max_tokens=max_tokens,
        temperature=0.3,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content.strip()


def _ollama(prompt, config):
    """Local LLM via Ollama's native HTTP API — stdlib only, no SDK, no API key."""
    import json
    import urllib.error
    import urllib.request

    host = config.get("ollama_host", "http://localhost:11434")
    payload = json.dumps(
        {
            "model": config.get("ollama_model", "llama3.2"),
            "prompt": prompt,
            "stream": False,
        }
    ).encode()
    req = urllib.request.Request(
        f"{host}/api/generate", data=payload, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.load(resp)["response"].strip()
    except urllib.error.URLError as e:
        raise EnvironmentError(
            f"Cannot reach Ollama at {host} ({e.reason}).\n"
            "Is Ollama running?  Start it with:  ollama serve\n"
            f"And pull the model:  ollama pull {config.get('ollama_model', 'llama3.2')}"
        )
