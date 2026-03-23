import os


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
    emoji_note = "Prepend a single relevant emoji before the type (e.g. ✨ feat, 🐛 fix, ♻️ refactor)." if emoji else ""

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


def generate(diff, files, config):
    provider = config.get("provider", "anthropic")
    if provider == "anthropic":
        return _anthropic(diff, files, config)
    if provider == "openai":
        return _openai(diff, files, config)
    raise ValueError(f"Unknown provider: {provider}")


def _anthropic(diff, files, config):
    try:
        import anthropic
    except ImportError:
        raise ImportError("Install the Anthropic SDK:  pip install anthropic")

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "ANTHROPIC_API_KEY is not set.\n"
            "Export it:  export ANTHROPIC_API_KEY=sk-ant-..."
        )

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=config.get("anthropic_model", "claude-sonnet-4-6"),
        max_tokens=300,
        messages=[{"role": "user", "content": _build_prompt(diff, files, config)}],
    )
    return message.content[0].text.strip()


def _openai(diff, files, config):
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError("Install the OpenAI SDK:  pip install openai")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "OPENAI_API_KEY is not set.\n"
            "Export it:  export OPENAI_API_KEY=sk-..."
        )

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=config.get("openai_model", "gpt-4o-mini"),
        max_tokens=300,
        temperature=0.3,
        messages=[{"role": "user", "content": _build_prompt(diff, files, config)}],
    )
    return response.choices[0].message.content.strip()
