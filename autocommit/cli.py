import sys

import click
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from .config import load_config, save_config
from .git import (
    get_branch_commits,
    get_branch_diff,
    get_current_branch,
    get_default_branch,
    get_staged_diff,
    get_staged_files,
    is_git_repo,
    make_commit,
    stage_all,
)
from .llm import generate
from .pr import write_pr
from .review import offline_review
from .review import review as _review
from .secrets import scan_diff

console = Console()

# Provider choices shared across the main command and subcommands.
# 'local' = offline heuristic (no API key); 'ollama' = local LLM via Ollama.
PROVIDER_CHOICES = ["anthropic", "openai", "ollama", "local"]


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────


def _show_message(message, title="Suggested commit message", style="green"):
    console.print()
    console.print(
        Panel(
            Text(message, style=f"bold {style}"), title=f"[bold]{title}[/bold]", border_style=style
        )
    )
    console.print()


def _do_commit(message):
    success, out, err = make_commit(message)
    if success:
        console.print("[bold green]✓ Committed successfully[/bold green]")
        if out.strip():
            console.print(f"[dim]{out.strip()}[/dim]")
    else:
        console.print(f"[red]Commit failed:[/red] {err.strip()}")
        sys.exit(1)


def _generate_with_spinner(diff, files, config):
    if config.get("provider") in ("local", "none", "heuristic"):
        text = "[bold blue]Analyzing changes...[/bold blue]"
    else:
        text = "[bold blue]Generating commit message...[/bold blue]"
    with console.status(text, spinner="dots"):
        return generate(diff, files, config)


def _render_findings(findings, title="Secrets detected"):
    lines = []
    for f in findings:
        lines.append(f"[bold red]{f.rule}[/bold red]  [dim]{f.file}:{f.line}[/dim]")
        lines.append(f"    [yellow]{f.preview}[/yellow]")
    console.print()
    console.print(
        Panel(
            "\n".join(lines),
            title=f"[bold]{title} ({len(findings)})[/bold]",
            border_style="red",
        )
    )
    console.print()


def _render_issues(issues, title="Review"):
    lines = []
    for i in issues:
        lines.append(f"[bold yellow]{i.kind}[/bold yellow]  [dim]{i.file}:{i.line}[/dim]")
        lines.append(f"    {i.detail}")
    console.print()
    console.print(
        Panel(
            "\n".join(lines),
            title=f"[bold]{title} ({len(issues)})[/bold]",
            border_style="yellow",
        )
    )
    console.print()


def _secret_gate(diff, yes):
    """Scan the diff and block the commit if secrets are found.

    Aborts (exit 1) under --yes; otherwise asks for an explicit override.
    """
    findings = scan_diff(diff)
    if not findings:
        return
    _render_findings(findings)
    console.print("[red]Possible secrets in your staged changes.[/red]")
    if yes:
        console.print("[red]✗ Aborting (--yes won't auto-commit secrets).[/red]")
        console.print("[dim]Review, then re-run with scan_secrets disabled to override.[/dim]")
        sys.exit(1)
    try:
        confirm = input("Commit anyway? [y/N] > ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        console.print("\n[dim]Aborted.[/dim]")
        sys.exit(1)
    if confirm != "y":
        console.print("[dim]Aborted.[/dim]")
        sys.exit(1)


# ──────────────────────────────────────────────────────────────────────────────
# Main command
# ──────────────────────────────────────────────────────────────────────────────


@click.group(invoke_without_command=True)
@click.pass_context
@click.option(
    "--style",
    "-s",
    type=click.Choice(["conventional", "angular", "simple"]),
    help="Commit message style",
)
@click.option("--emoji", "-e", is_flag=True, default=None, help="Add emoji prefix to type")
@click.option("--body", "-b", is_flag=True, default=None, help="Include a commit body")
@click.option(
    "--provider",
    "-p",
    type=click.Choice(PROVIDER_CHOICES),
    help="LLM provider ('local' = no-AI offline heuristic)",
)
@click.option(
    "--no-ai", "no_ai", is_flag=True, help="Generate offline with no API key (heuristic mode)"
)
@click.option(
    "--all", "-a", "stage_all_files", is_flag=True, help="Stage all changes first (git add -A)"
)
@click.option(
    "--yes", "-y", is_flag=True, help="Auto-accept the first suggestion without prompting"
)
def cli(ctx, style, emoji, body, provider, no_ai, stage_all_files, yes):
    """AI-powered git commit message generator.

    Run inside any git repo. Reads your staged diff and generates a
    conventional commit message using Claude or GPT — or fully offline
    with --no-ai if you don't have an API key.

    \b
    Quick start:
      export ANTHROPIC_API_KEY=sk-ant-...
      autocommit              # generate from staged changes
      autocommit -a           # stage everything, then generate
      autocommit -a -y        # stage + auto-accept (great for hooks)
      autocommit --no-ai      # no API key needed — offline heuristic
    """
    if ctx.invoked_subcommand is not None:
        return

    if not is_git_repo():
        console.print("[red]✗ Not inside a git repository.[/red]")
        sys.exit(1)

    config = load_config()

    # CLI flag overrides
    if style:
        config["style"] = style
    if emoji is not None:
        config["emoji"] = emoji
    if body is not None:
        config["include_body"] = body
    if provider:
        config["provider"] = provider
    if no_ai:
        config["provider"] = "local"

    if stage_all_files:
        stage_all()

    diff, err = get_staged_diff()
    if err:
        console.print(f"[red]Git error:[/red] {err}")
        sys.exit(1)

    if not diff.strip():
        console.print("[yellow]Nothing staged.[/yellow]  Stage changes first:\n")
        console.print("  [dim]git add <file>[/dim]        stage specific files")
        console.print("  [dim]autocommit -a[/dim]         stage everything and generate")
        sys.exit(1)

    files, _ = get_staged_files()

    # Keep the full diff for secret scanning before any truncation
    full_diff = diff

    # Truncate very large diffs
    max_lines = config.get("max_diff_lines", 500)
    lines = diff.split("\n")
    if len(lines) > max_lines:
        diff = "\n".join(lines[:max_lines])
        console.print(f"[dim]Diff truncated to {max_lines} lines.[/dim]")

    # Show what's staged
    console.print(f"\n[dim]Staged ({len(files)} file{'s' if len(files) != 1 else ''}):[/dim]")
    for f in files[:8]:
        console.print(f"  [dim]· {f}[/dim]")
    if len(files) > 8:
        console.print(f"  [dim]· ... and {len(files) - 8} more[/dim]")

    # Block the commit if the staged diff introduces secrets
    if config.get("scan_secrets", True):
        _secret_gate(full_diff, yes)

    # Generate + interactive loop
    message = None
    while True:
        try:
            message = _generate_with_spinner(diff, files, config)
        except (EnvironmentError, ImportError) as e:
            console.print(f"\n[red]✗ {e}[/red]")
            sys.exit(1)
        except Exception as e:
            console.print(f"\n[red]✗ Unexpected error:[/red] {e}")
            sys.exit(1)

        _show_message(message)

        if yes:
            _do_commit(message)
            break

        console.print(
            "[dim]\\[Enter][/dim] commit   [bold]e[/bold] edit   [bold]r[/bold] regenerate   [bold]q[/bold] quit"
        )
        try:
            choice = input("> ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Aborted.[/dim]")
            sys.exit(0)

        if choice == "":
            _do_commit(message)
            break

        elif choice == "e":
            edited = click.edit(message)
            if edited and edited.strip():
                message = edited.strip()
                _show_message(message, title="Edited message", style="yellow")
                try:
                    confirm = input("Commit with this message? [y/N] > ").strip().lower()
                except (KeyboardInterrupt, EOFError):
                    console.print("\n[dim]Aborted.[/dim]")
                    sys.exit(0)
                if confirm == "y":
                    _do_commit(message)
                    break
            else:
                console.print("[dim]No changes made.[/dim]")

        elif choice == "r":
            console.print("[dim]Regenerating...[/dim]")
            continue

        elif choice == "q":
            console.print("[dim]Aborted.[/dim]")
            sys.exit(0)

        else:
            console.print(
                "[dim]Press Enter to commit, e to edit, r to regenerate, q to quit.[/dim]"
            )


# ──────────────────────────────────────────────────────────────────────────────
# Subcommands
# ──────────────────────────────────────────────────────────────────────────────


@cli.command()
def configure():
    """Interactive setup — choose provider, style, and preferences."""
    config = load_config()

    provider = click.prompt(
        "LLM provider ('ollama' = local LLM, 'local' = no-AI offline mode)",
        type=click.Choice(PROVIDER_CHOICES),
        default=config.get("provider", "anthropic"),
    )
    if provider == "ollama":
        config["ollama_model"] = click.prompt(
            "Ollama model", default=config.get("ollama_model", "llama3.2")
        )
        config["ollama_host"] = click.prompt(
            "Ollama host", default=config.get("ollama_host", "http://localhost:11434")
        )
    style = click.prompt(
        "Commit style",
        type=click.Choice(["conventional", "angular", "simple"]),
        default=config.get("style", "conventional"),
    )
    include_scope = click.confirm(
        "Include scope in commit message?", default=config.get("include_scope", True)
    )
    include_body = click.confirm(
        "Include a commit body?", default=config.get("include_body", False)
    )
    emoji = click.confirm("Add emoji prefixes?", default=config.get("emoji", False))
    scan_secrets = click.confirm(
        "Scan staged changes for secrets before committing?",
        default=config.get("scan_secrets", True),
    )

    config.update(
        {
            "provider": provider,
            "style": style,
            "include_scope": include_scope,
            "include_body": include_body,
            "emoji": emoji,
            "scan_secrets": scan_secrets,
        }
    )

    path = save_config(config)
    console.print(f"\n[green]✓ Config saved to {path}[/green]")
    if provider == "local":
        console.print(
            "\n[dim]Offline mode — no API key needed. Just run [bold]autocommit[/bold].[/dim]"
        )
    elif provider == "ollama":
        console.print(
            "\n[dim]Local LLM via Ollama — no API key needed. Make sure Ollama is running:[/dim]"
        )
        console.print("  [dim]ollama serve[/dim]")
        console.print(f"  [dim]ollama pull {config.get('ollama_model', 'llama3.2')}[/dim]")
    elif provider == "anthropic":
        console.print("\n[dim]Set your API key:[/dim]")
        console.print("  [dim]export ANTHROPIC_API_KEY=sk-ant-...[/dim]")
    else:
        console.print("\n[dim]Set your API key:[/dim]")
        console.print("  [dim]export OPENAI_API_KEY=sk-...[/dim]")


@cli.command("install-hook")
def install_hook():
    """Install autocommit as a prepare-commit-msg git hook in the current repo.

    After installing, running `git commit` will automatically suggest a message.
    You can still edit it in your editor as usual.
    """
    import stat
    from pathlib import Path

    hooks_dir = Path(".git/hooks")
    if not hooks_dir.exists():
        console.print("[red]No .git/hooks directory found. Are you in a git repo?[/red]")
        sys.exit(1)

    hook_path = hooks_dir / "prepare-commit-msg"

    hook_script = """\
#!/bin/sh
# autocommit — AI commit message generator
# https://github.com/suryaSPS/autocommit
COMMIT_MSG_FILE="$1"
COMMIT_SOURCE="$2"

# Only run on blank commits (skip merge, squash, fixup, etc.)
if [ -z "$COMMIT_SOURCE" ]; then
    autocommit --yes 2>/dev/null || true
fi
"""

    hook_path.write_text(hook_script)
    hook_path.chmod(hook_path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    console.print(f"[green]✓ Hook installed at {hook_path}[/green]")
    console.print("[dim]Now `git commit` will auto-generate and accept a message.[/dim]")
    console.print("[dim]To uninstall: rm .git/hooks/prepare-commit-msg[/dim]")


@cli.command()
def scan():
    """Scan the staged diff for secrets and credentials.

    Exits non-zero if anything is found, so it works as a pre-commit gate.
    Only ADDED lines are scanned; the full secret is never printed.
    """
    if not is_git_repo():
        console.print("[red]✗ Not inside a git repository.[/red]")
        sys.exit(1)

    diff, err = get_staged_diff()
    if err:
        console.print(f"[red]Git error:[/red] {err}")
        sys.exit(1)
    if not diff.strip():
        console.print("[yellow]Nothing staged.[/yellow]")
        return

    findings = scan_diff(diff)
    if not findings:
        console.print("[green]✓ No secrets detected in staged changes.[/green]")
        return

    _render_findings(findings)
    sys.exit(1)


@cli.command()
@click.option(
    "--provider",
    "-p",
    type=click.Choice(PROVIDER_CHOICES),
    help="LLM provider to review with",
)
@click.option("--no-ai", "no_ai", is_flag=True, help="Offline pattern checks only (no API key)")
def review(provider, no_ai):
    """Review the staged diff for bugs and issues before committing.

    AI providers give a real review; --no-ai runs deterministic pattern
    checks (leftover debug code, conflict markers, new TODOs) only.
    """
    if not is_git_repo():
        console.print("[red]✗ Not inside a git repository.[/red]")
        sys.exit(1)

    config = load_config()
    if provider:
        config["provider"] = provider
    if no_ai:
        config["provider"] = "local"

    diff, err = get_staged_diff()
    if err:
        console.print(f"[red]Git error:[/red] {err}")
        sys.exit(1)
    if not diff.strip():
        console.print("[yellow]Nothing staged.[/yellow]  Stage changes first.")
        sys.exit(1)

    files, _ = get_staged_files()

    try:
        with console.status("[bold blue]Reviewing changes...[/bold blue]", spinner="dots"):
            text, is_offline = _review(diff, files, config)
    except (EnvironmentError, ImportError) as e:
        console.print(f"\n[red]✗ {e}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]✗ Unexpected error:[/red] {e}")
        sys.exit(1)

    if is_offline:
        issues = offline_review(diff)
        if not issues:
            console.print("[green]✓ No obvious issues found.[/green]")
            console.print("[dim]Offline mode runs pattern checks only, not a correctness review.[/dim]")
        else:
            _render_issues(issues)
    else:
        _show_message(text, title="Code review", style="cyan")


@cli.command()
@click.option("--base", help="Base branch to compare against (default: autodetected)")
@click.option(
    "--provider",
    "-p",
    type=click.Choice(PROVIDER_CHOICES),
    help="LLM provider to write the description with",
)
@click.option("--no-ai", "no_ai", is_flag=True, help="Assemble offline from commit subjects")
def pr(base, provider, no_ai):
    """Generate a pull request title and description for the current branch."""
    if not is_git_repo():
        console.print("[red]✗ Not inside a git repository.[/red]")
        sys.exit(1)

    config = load_config()
    if provider:
        config["provider"] = provider
    if no_ai:
        config["provider"] = "local"

    branch = get_current_branch()
    base = base or get_default_branch()
    if not base:
        console.print(
            "[red]Could not determine a base branch.[/red]  Pass one with [dim]--base <branch>[/dim]."
        )
        sys.exit(1)
    if base == branch:
        console.print(
            f"[yellow]Current branch [bold]{branch}[/bold] is the base branch.[/yellow]"
        )
        console.print("[dim]Check out a feature branch, or pass --base <branch>.[/dim]")
        sys.exit(1)

    commits, cerr = get_branch_commits(base)
    if cerr:
        console.print(f"[red]Git error:[/red] {cerr}")
        sys.exit(1)
    diff, derr = get_branch_diff(base)
    if derr:
        console.print(f"[red]Git error:[/red] {derr}")
        sys.exit(1)

    if not commits and not (diff or "").strip():
        console.print(f"[yellow]No commits on [bold]{branch}[/bold] beyond [bold]{base}[/bold].[/yellow]")
        sys.exit(1)

    console.print(
        f"\n[dim]{len(commits)} commit{'s' if len(commits) != 1 else ''} on "
        f"[bold]{branch}[/bold] vs [bold]{base}[/bold][/dim]"
    )

    try:
        with console.status("[bold blue]Writing PR description...[/bold blue]", spinner="dots"):
            title, body = write_pr(branch, base, commits, diff or "", config)
    except (EnvironmentError, ImportError) as e:
        console.print(f"\n[red]✗ {e}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]✗ Unexpected error:[/red] {e}")
        sys.exit(1)

    from rich.markdown import Markdown

    _show_message(title, title="PR title", style="magenta")
    console.print(Markdown(body))
    console.print()


@cli.command()
def version():
    """Show version."""
    from . import __version__

    console.print(f"autocommit {__version__}")
