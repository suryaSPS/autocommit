import os
import sys

import click
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from .config import load_config, save_config
from .git import (
    get_staged_diff,
    get_staged_files,
    is_git_repo,
    make_commit,
    stage_all,
)
from .llm import generate
from .scanner import scan_diff

console = Console()


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _show_message(message, title="Suggested commit message", style="green"):
    console.print()
    console.print(Panel(Text(message, style=f"bold {style}"), title=f"[bold]{title}[/bold]", border_style=style))
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
    with console.status("[bold blue]Generating commit message...[/bold blue]", spinner="dots"):
        return generate(diff, files, config)


# ──────────────────────────────────────────────────────────────────────────────
# Main command
# ──────────────────────────────────────────────────────────────────────────────

@click.group(invoke_without_command=True)
@click.pass_context
@click.option("--style", "-s", type=click.Choice(["conventional", "angular", "simple"]), help="Commit message style")
@click.option("--emoji", "-e", is_flag=True, default=None, help="Add emoji prefix to type")
@click.option("--body", "-b", is_flag=True, default=None, help="Include a commit body")
@click.option("--provider", "-p", type=click.Choice(["anthropic", "openai"]), help="LLM provider")
@click.option("--all", "-a", "stage_all_files", is_flag=True, help="Stage all changes first (git add -A)")
@click.option("--yes", "-y", is_flag=True, help="Auto-accept the first suggestion without prompting")
def cli(ctx, style, emoji, body, provider, stage_all_files, yes):
    """AI-powered git commit message generator.

    Run inside any git repo. Reads your staged diff and generates a
    conventional commit message using Claude or GPT.

    \b
    Quick start:
      export ANTHROPIC_API_KEY=sk-ant-...
      autocommit              # generate from staged changes
      autocommit -a           # stage everything, then generate
      autocommit -a -y        # stage + auto-accept (great for hooks)
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

    # Pre-commit scan — secrets, debug artifacts, conflict markers
    scan = scan_diff(diff)

    if scan.conflict_markers:
        console.print("\n[bold red]✗ Conflict markers found in staged changes:[/bold red]")
        for f in scan.conflict_markers:
            console.print(f"  [red]line {f.line}:[/red] {f.preview}")
        console.print("[dim]Resolve conflict markers before committing.[/dim]")
        sys.exit(1)

    if scan.secrets:
        console.print("\n[bold red]✗ Possible secrets detected in staged changes:[/bold red]")
        for f in scan.secrets:
            console.print(f"  [red]line {f.line} ({f.label}):[/red] {f.preview}")
        console.print("[dim]Remove secrets and use environment variables instead.[/dim]")
        console.print("[dim]To override (not recommended): git commit directly.[/dim]")
        sys.exit(1)

    if scan.debug_artifacts:
        console.print("\n[bold yellow]⚠ Debug artifacts found:[/bold yellow]")
        for f in scan.debug_artifacts:
            console.print(f"  [yellow]line {f.line} ({f.label}):[/yellow] {f.preview}")
        try:
            if not click.confirm("\nContinue anyway?", default=False):
                sys.exit(0)
        except (KeyboardInterrupt, EOFError):
            sys.exit(0)

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

        console.print("[dim]\\[Enter][/dim] commit   [bold]e[/bold] edit   [bold]r[/bold] regenerate   [bold]q[/bold] quit")
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
            console.print("[dim]Press Enter to commit, e to edit, r to regenerate, q to quit.[/dim]")


# ──────────────────────────────────────────────────────────────────────────────
# Subcommands
# ──────────────────────────────────────────────────────────────────────────────

@cli.command()
def configure():
    """Interactive setup — choose provider, style, and preferences."""
    config = load_config()

    provider = click.prompt(
        "LLM provider",
        type=click.Choice(["anthropic", "openai"]),
        default=config.get("provider", "anthropic"),
    )
    style = click.prompt(
        "Commit style",
        type=click.Choice(["conventional", "angular", "simple"]),
        default=config.get("style", "conventional"),
    )
    include_scope = click.confirm("Include scope in commit message?", default=config.get("include_scope", True))
    include_body = click.confirm("Include a commit body?", default=config.get("include_body", False))
    emoji = click.confirm("Add emoji prefixes?", default=config.get("emoji", False))

    config.update({
        "provider": provider,
        "style": style,
        "include_scope": include_scope,
        "include_body": include_body,
        "emoji": emoji,
    })

    path = save_config(config)
    console.print(f"\n[green]✓ Config saved to {path}[/green]")
    console.print(f"\n[dim]Set your API key:[/dim]")
    if provider == "anthropic":
        console.print("  [dim]export ANTHROPIC_API_KEY=sk-ant-...[/dim]")
    else:
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
# https://github.com/yourname/autocommit
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
def version():
    """Show version."""
    from . import __version__
    console.print(f"autocommit {__version__}")
