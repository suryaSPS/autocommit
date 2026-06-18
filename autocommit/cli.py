import sys

import click
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from .config import load_config, save_config
from .git import (
    get_staged_diff,
    get_staged_files,
    get_current_branch,
    get_default_branch,
    get_commit_log,
    get_full_diff_since,
    ref_exists,
    is_git_repo,
    make_commit,
    stage_all,
)
from .llm import generate, generate_review, generate_pr_description
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


def _load_config_or_exit():
    try:
        return load_config()
    except ValueError as e:
        console.print(f"[red]Config error:[/red] {e}")
        sys.exit(1)


def _apply_overrides(config, style=None, emoji=None, body=None, provider=None):
    if style:
        config["style"] = style
    if emoji is not None:
        config["emoji"] = emoji
    if body is not None:
        config["include_body"] = body
    if provider:
        config["provider"] = provider
    return config


def _collect_staged_changes(stage_all_files=False):
    if not is_git_repo():
        console.print("[red]✗ Not inside a git repository.[/red]")
        sys.exit(1)

    if stage_all_files:
        success, err = stage_all()
        if not success:
            console.print(f"[red]Failed to stage files:[/red] {err.strip()}")
            sys.exit(1)

    diff, err = get_staged_diff()
    if err:
        console.print(f"[red]Git error:[/red] {err}")
        sys.exit(1)

    if not diff.strip():
        console.print("[yellow]Nothing staged.[/yellow]  Stage changes first:\n")
        console.print("  [dim]git add <file>[/dim]        stage specific files")
        console.print("  [dim]autocommit -a[/dim]         stage everything and generate")
        sys.exit(1)

    files, err = get_staged_files()
    if err:
        console.print(f"[red]Git error:[/red] {err}")
        sys.exit(1)

    return diff, files


def _truncate_diff(diff, config):
    max_lines = config.get("max_diff_lines", 500)
    try:
        max_lines = int(max_lines)
    except (TypeError, ValueError):
        max_lines = 500
    max_lines = max(1, max_lines)

    lines = diff.split("\n")
    if len(lines) > max_lines:
        diff = "\n".join(lines[:max_lines])
        console.print(f"[dim]Diff truncated to {max_lines} lines.[/dim]")
    return diff


def _show_staged_files(files):
    console.print(f"\n[dim]Staged ({len(files)} file{'s' if len(files) != 1 else ''}):[/dim]")
    for f in files[:8]:
        console.print(f"  [dim]· {f}[/dim]")
    if len(files) > 8:
        console.print(f"  [dim]· ... and {len(files) - 8} more[/dim]")


def _scan_or_exit(diff):
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

    config = _apply_overrides(_load_config_or_exit(), style, emoji, body, provider)
    diff, files = _collect_staged_changes(stage_all_files)
    _scan_or_exit(diff)
    diff = _truncate_diff(diff, config)
    _show_staged_files(files)

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
    config = _load_config_or_exit()

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
    console.print("\n[dim]Set your API key:[/dim]")
    if provider == "anthropic":
        console.print("  [dim]export ANTHROPIC_API_KEY=sk-ant-...[/dim]")
    else:
        console.print("  [dim]export OPENAI_API_KEY=sk-...[/dim]")


@cli.command()
@click.option("--style", "-s", type=click.Choice(["conventional", "angular", "simple"]), help="Commit message style")
@click.option("--emoji", "-e", is_flag=True, default=None, help="Add emoji prefix to type")
@click.option("--body", "-b", is_flag=True, default=None, help="Include a commit body")
@click.option("--provider", "-p", type=click.Choice(["anthropic", "openai"]), help="LLM provider")
def suggest(style, emoji, body, provider):
    """Print a commit message suggestion without committing."""
    config = _apply_overrides(_load_config_or_exit(), style, emoji, body, provider)
    diff, files = _collect_staged_changes()
    diff = _truncate_diff(diff, config)
    try:
        click.echo(generate(diff, files, config))
    except (EnvironmentError, ImportError, ValueError) as e:
        click.echo(str(e), err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)


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

# Only run on blank commits (skip merge, squash, fixup, etc.).
if [ -z "$COMMIT_SOURCE" ]; then
    autocommit suggest > "$COMMIT_MSG_FILE" 2>/dev/null || true
fi
"""

    hook_path.write_text(hook_script)
    hook_path.chmod(hook_path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    console.print(f"[green]✓ Hook installed at {hook_path}[/green]")
    console.print("[dim]Now `git commit` will auto-fill a message for review.[/dim]")
    console.print("[dim]To uninstall: rm .git/hooks/prepare-commit-msg[/dim]")


@cli.command()
def review():
    """AI code review of staged changes before committing.

    Sends your staged diff to the LLM and gets back a structured review:
    bugs, security issues, breaking changes, and code quality notes.

    \b
    Example:
      git add .
      autocommit review       # review first
      autocommit              # then commit
    """
    if not is_git_repo():
        console.print("[red]✗ Not inside a git repository.[/red]")
        sys.exit(1)

    config = load_config()
    diff, err = get_staged_diff()
    if err:
        console.print(f"[red]Git error:[/red] {err}")
        sys.exit(1)

    if not diff.strip():
        console.print("[yellow]Nothing staged.[/yellow]  Run [dim]git add <file>[/dim] first.")
        sys.exit(1)

    files, _ = get_staged_files()

    max_lines = config.get("max_diff_lines", 500)
    lines = diff.split("\n")
    if len(lines) > max_lines:
        diff = "\n".join(lines[:max_lines])

    console.print(f"\n[dim]Reviewing {len(files)} file{'s' if len(files) != 1 else ''}...[/dim]")

    try:
        with console.status("[bold blue]Running AI code review...[/bold blue]", spinner="dots"):
            feedback = generate_review(diff, files, config)
    except (EnvironmentError, ImportError) as e:
        console.print(f"\n[red]✗ {e}[/red]")
        sys.exit(1)

    # Pick panel color from verdict line
    first_line = feedback.split("\n")[0]
    if "❌" in first_line:
        style = "red"
    elif "⚠" in first_line:
        style = "yellow"
    else:
        style = "green"

    console.print()
    console.print(Panel(feedback, title="[bold]Code Review[/bold]", border_style=style))
    console.print()


@cli.command("merge-check")
@click.option("--into", "target", default=None, help="Target branch to check against (default: main/master)")
def merge_check(target):
    """Dry-run merge check — detect conflicts before you push.

    Fetches the target branch and runs a merge simulation without touching
    your working tree. Reports which files would conflict and why.

    \b
    Examples:
      autocommit merge-check              # check against main/master
      autocommit merge-check --into dev   # check against a specific branch
    """
    if not is_git_repo():
        console.print("[red]✗ Not inside a git repository.[/red]")
        sys.exit(1)

    from .merge import check_merge

    with console.status("[bold blue]Checking for merge conflicts...[/bold blue]", spinner="dots"):
        result = check_merge(target)

    branch_label = f"[bold]{result.current_branch or 'HEAD'}[/bold]"
    target_label = f"[bold]{result.target_branch}[/bold]"

    if result.fetch_failed:
        console.print(f"[yellow]⚠ Could not fetch origin/{result.target_branch} — using local ref.[/yellow]")
        if result.fetch_error:
            console.print(f"[dim]{result.fetch_error}[/dim]")

    if result.error:
        console.print(f"[red]✗ {result.error}[/red]")
        sys.exit(1)

    if result.clean:
        console.print(f"\n[bold green]✓ Clean merge[/bold green] — {branch_label} merges into {target_label} with no conflicts.\n")
        return

    console.print(f"\n[bold red]✗ Merge conflicts detected[/bold red] — {branch_label} → {target_label}\n")
    for c in result.conflicts:
        console.print(f"  [red]·[/red] [bold]{c.path}[/bold]")
        if c.reason and c.reason != c.path:
            console.print(f"    [dim]{c.reason}[/dim]")
    console.print(
        f"\n[dim]Resolve these conflicts before merging. "
        f"You can pull {target_label}, merge locally, and fix the conflicts.[/dim]\n"
    )
    sys.exit(1)


@cli.command()
@click.option("--into", "target", default=None, help="Target branch for the PR (default: main/master)")
@click.option("--copy", is_flag=True, help="Copy output to clipboard")
def pr(target, copy):
    """Generate a GitHub pull request title and description.

    Reads all commits and the full diff since branching off the target,
    then generates a PR title + body ready to paste into GitHub.

    \b
    Example:
      autocommit pr                  # generate PR description
      autocommit pr --into staging   # target a specific branch
      autocommit pr --copy           # copy to clipboard
    """
    if not is_git_repo():
        console.print("[red]✗ Not inside a git repository.[/red]")
        sys.exit(1)

    config = load_config()
    branch = get_current_branch()
    if not branch:
        console.print("[red]✗ Cannot determine current branch (detached HEAD?).[/red]")
        sys.exit(1)

    if target is None:
        target = get_default_branch()

    target_ref = f"origin/{target}"
    if not ref_exists(target_ref):
        target_ref = target  # fall back to local ref

    commits = get_commit_log(base=target_ref)
    if not commits:
        console.print(f"[yellow]No commits found between {target_ref} and HEAD.[/yellow]")
        console.print("[dim]Make sure you have commits that aren't in the target branch.[/dim]")
        sys.exit(1)

    diff = get_full_diff_since(target_ref)

    console.print(f"\n[dim]Branch:[/dim] {branch} → {target}")
    commit_count = len([line for line in commits.split("\n") if line.strip()])
    console.print(f"[dim]Commits:[/dim] {commit_count}\n")

    try:
        with console.status("[bold blue]Generating PR description...[/bold blue]", spinner="dots"):
            description = generate_pr_description(commits, diff, branch, target, config)
    except (EnvironmentError, ImportError) as e:
        console.print(f"\n[red]✗ {e}[/red]")
        sys.exit(1)

    # Split TITLE: line from body for display
    lines = description.strip().split("\n")
    title_line = next((line for line in lines if line.startswith("TITLE:")), None)
    if title_line:
        title = title_line.replace("TITLE:", "").strip()
        body = "\n".join(line for line in lines if not line.startswith("TITLE:")).strip()
        console.print(Panel(title, title="[bold]PR Title[/bold]", border_style="cyan"))
        console.print()
        console.print(Panel(body, title="[bold]PR Description[/bold]", border_style="blue"))
    else:
        console.print(Panel(description, title="[bold]PR Description[/bold]", border_style="blue"))

    if copy:
        try:
            import subprocess as sp  # nosec B404
            sp.run(["pbcopy"], input=description.encode(), check=True)  # nosec B603 B607
            console.print("\n[green]✓ Copied to clipboard.[/green]")
        except Exception:
            try:
                sp.run(  # nosec B603 B607
                    ["xclip", "-selection", "clipboard"],
                    input=description.encode(),
                    check=True,
                )
                console.print("\n[green]✓ Copied to clipboard.[/green]")
            except Exception:
                console.print("\n[dim]--copy not supported on this system.[/dim]")
    console.print()


@cli.command()
def version():
    """Show version."""
    from . import __version__
    console.print(f"autocommit {__version__}")
