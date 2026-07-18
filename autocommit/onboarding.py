"""First-run onboarding.

Triggers the first time someone runs `autocommit` with no saved config.
Walks them through picking a provider and getting a key in place.

Security: this flow NEVER writes an API key to disk. A key entered here is
used for the current process only (set in os.environ); to persist it we
print the exact shell command for the user to add themselves. This mirrors
the guarantee load_config/save_config already make.
"""

import os

import click
from rich.console import Console
from rich.panel import Panel

from .config import save_config

# provider -> (env var name, sample key prefix)
PROVIDER_ENV = {
    "anthropic": ("ANTHROPIC_API_KEY", "sk-ant-..."),
    "openai": ("OPENAI_API_KEY", "sk-..."),
}

PROVIDER_CHOICES = ["anthropic", "openai", "ollama", "local"]

PROVIDER_BLURB = {
    "anthropic": "Anthropic Claude — best quality (needs an API key)",
    "openai": "OpenAI GPT — needs an API key",
    "ollama": "Ollama — a local model on your machine, free, no key",
    "local": "Offline heuristic — no AI, no key, works anywhere",
}


def is_first_run(config_path) -> bool:
    """True when no config file exists yet."""
    return not config_path.exists()


def _shell_rc_hint(env_name: str) -> str:
    shell = os.environ.get("SHELL", "")
    if shell.endswith("zsh"):
        return "~/.zshrc"
    if shell.endswith("bash"):
        return "~/.bashrc"
    return "your shell profile"


def _setup_key(console: Console, provider: str) -> bool:
    """Ensure a usable key for provider. Returns True if AI is ready this run."""
    env_name, sample = PROVIDER_ENV[provider]

    if os.getenv(env_name):
        console.print(f"[green]✓ {env_name} is already set in your environment.[/green]")
        return True

    console.print(f"\n[bold]{provider.title()} needs an API key[/bold] ([dim]{env_name}[/dim]).")
    key = click.prompt(
        f"  Paste your key ({sample}), or press Enter to skip for now",
        hide_input=True,
        default="",
        show_default=False,
    ).strip()

    if not key:
        console.print("[yellow]Skipped.[/yellow] You can set it later:")
        console.print(f"  [dim]export {env_name}={sample}[/dim]")
        return False

    # Session-only: used by this process, never persisted by us.
    os.environ[env_name] = key
    rc = _shell_rc_hint(env_name)
    console.print("[green]✓ Key accepted for this session.[/green]  [dim](not written to disk)[/dim]")
    console.print(f"[dim]To keep it for next time, add this line to {rc}:[/dim]")
    console.print(f"  [dim]export {env_name}=<the key you just entered>[/dim]")
    return True


def _setup_ollama(console: Console, config: dict) -> None:
    model = click.prompt("  Ollama model", default=config.get("ollama_model", "llama3.2"))
    config["ollama_model"] = model
    console.print("[dim]Make sure Ollama is running before you commit:[/dim]")
    console.print("  [dim]ollama serve[/dim]")
    console.print(f"  [dim]ollama pull {model}[/dim]")


def run_onboarding(console: Console, config: dict) -> dict:
    """Interactive first-run setup. Returns the config to use for this run.

    Persists non-secret preferences (creating the config file, so this won't
    trigger again). If the chosen AI provider has no key available, falls back
    to offline mode for THIS run only so the first commit still succeeds — the
    chosen provider is still saved for next time.
    """
    console.print(
        Panel(
            "Welcome to [bold]autocommit[/bold] 👋\n\n"
            "Let's set up how your commit messages get generated.\n"
            "[dim]Takes about 20 seconds. Change anything later with "
            "[bold]autocommit configure[/bold].[/dim]",
            title="[bold]First-time setup[/bold]",
            border_style="cyan",
        )
    )

    console.print("\n[bold]Providers[/bold]")
    for name in PROVIDER_CHOICES:
        console.print(f"  [cyan]{name}[/cyan] — {PROVIDER_BLURB[name]}")
    console.print()

    provider = click.prompt(
        "Which provider?",
        type=click.Choice(PROVIDER_CHOICES),
        default="anthropic",
    )
    config["provider"] = provider

    ready = True
    if provider in PROVIDER_ENV:
        ready = _setup_key(console, provider)
    elif provider == "ollama":
        _setup_ollama(console, config)
    else:  # local
        console.print("[green]✓ Offline mode — no key needed.[/green]")

    path = save_config(config)
    console.print(f"\n[green]✓ Setup saved to {path}[/green]")

    run_config = dict(config)
    if provider in PROVIDER_ENV and not ready:
        console.print(
            "\n[yellow]No key yet — using offline mode for this commit.[/yellow] "
            f"[dim]Next time, with {PROVIDER_ENV[provider][0]} set, it'll use {provider}.[/dim]"
        )
        run_config["provider"] = "local"

    console.print()
    return run_config
