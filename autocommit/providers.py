"""LLM provider backends.

Each provider turns a prompt into text. New backends (Gemini, Groq, a
company-internal gateway, ...) plug in by subclassing LLMProvider and
calling register() — no core code changes needed.
"""

import os
from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """One completion backend."""

    name: str = ""

    @abstractmethod
    def complete(self, prompt: str, config: dict, max_tokens: int = 1024) -> str:
        """Return the model's text response for a prompt."""


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def complete(self, prompt: str, config: dict, max_tokens: int = 1024) -> str:
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


class OpenAIProvider(LLMProvider):
    name = "openai"

    def complete(self, prompt: str, config: dict, max_tokens: int = 1024) -> str:
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


class OllamaProvider(LLMProvider):
    """Local LLM via Ollama's native HTTP API — stdlib only, no SDK, no API key."""

    name = "ollama"

    def complete(self, prompt: str, config: dict, max_tokens: int = 1024) -> str:
        import json
        import urllib.error
        import urllib.request

        host = config.get("ollama_host", "http://localhost:11434")
        payload = json.dumps(
            {
                "model": config.get("ollama_model", "llama3.2"),
                "prompt": prompt,
                "stream": False,
                "options": {"num_predict": max_tokens},
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


PROVIDERS: dict = {}


def register(provider: LLMProvider) -> None:
    PROVIDERS[provider.name] = provider


def get(name: str) -> LLMProvider:
    try:
        return PROVIDERS[name]
    except KeyError:
        raise ValueError(f"Unknown provider: {name}") from None


for _p in (AnthropicProvider(), OpenAIProvider(), OllamaProvider()):
    register(_p)
