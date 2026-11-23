from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Protocol, Sequence

import httpx


@dataclass(frozen=True)
class ModelReply:
    text: str
    provider: str
    model: str


class ModelProvider(Protocol):
    """A single explicitly configured chat provider; implementations never auto-fallback."""

    name: str
    model: str

    async def complete(self, messages: Sequence[dict[str, str]]) -> ModelReply: ...


class NoModelConfigured(RuntimeError):
    pass


class ModelProviderError(RuntimeError):
    pass


class DisabledModelProvider:
    """Fails closed when no usable provider has been configured."""

    name = "disabled"
    model = ""

    def __init__(self, reason: str = "No AI provider is configured.") -> None:
        self.reason = reason

    async def complete(self, messages: Sequence[dict[str, str]]) -> ModelReply:
        raise NoModelConfigured(self.reason)


@dataclass(frozen=True)
class OpenAICompatibleProvider:
    """Adapter for OpenAI-compatible /v1/chat/completions endpoints."""

    name: str
    base_url: str
    model: str
    api_key: str = ""
    proxy: str | None = None
    timeout_seconds: float = 90.0

    async def complete(self, messages: Sequence[dict[str, str]]) -> ModelReply:
        if not self.model.strip():
            raise NoModelConfigured(f"The {self.name} model name is not configured.")

        endpoint = f"{self.base_url.rstrip('/')}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model,
            "messages": list(messages),
            "stream": False,
        }

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds,
                proxy=self.proxy,
                trust_env=False,
            ) as client:
                # Google recommends exponential backoff for transient 503 overloads.
                # Keep retries bounded and never switch providers automatically.
                for attempt in range(3):
                    response = await client.post(endpoint, headers=headers, json=payload)
                    if response.status_code != 503 or attempt == 2:
                        response.raise_for_status()
                        break

                    retry_after = response.headers.get("Retry-After")
                    try:
                        delay = min(max(float(retry_after), 0.0), 8.0) if retry_after else 2**attempt
                    except ValueError:
                        delay = 2**attempt
                    await asyncio.sleep(delay)

                data = response.json()
        except httpx.TimeoutException as exc:
            raise ModelProviderError(f"{self.name} did not respond before the timeout.") from exc
        except httpx.HTTPStatusError as exc:
            # Do not echo provider response bodies: they may contain sensitive request details.
            raise ModelProviderError(
                f"{self.name} returned HTTP {exc.response.status_code}."
            ) from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise ModelProviderError(f"Could not communicate with {self.name}.") from exc

        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ModelProviderError(f"{self.name} returned an unsupported chat response.") from exc

        if isinstance(content, list):
            content = "".join(
                part.get("text", "") for part in content if isinstance(part, dict)
            )
        if not isinstance(content, str) or not content.strip():
            raise ModelProviderError(f"{self.name} returned an empty assistant response.")

        return ModelReply(text=content.strip(), provider=self.name, model=self.model)


def build_model_provider() -> ModelProvider:
    """Build exactly the configured provider. No paid or remote fallback is automatic."""
    selected = os.getenv("AI_PROVIDER", "disabled").strip().lower()

    if selected in {"", "disabled", "none"}:
        return DisabledModelProvider()

    if selected == "bynara":
        api_key = os.getenv("BYNARA_API_KEY", "").strip()
        if not api_key or api_key.startswith("CHANGE_ME"):
            return DisabledModelProvider("Set BYNARA_API_KEY in your local .env to enable Bynara.")
        return OpenAICompatibleProvider(
            name="bynara",
            base_url=os.getenv("BYNARA_BASE_URL", "https://router.bynara.id/v1"),
            model=os.getenv("BYNARA_MODEL", "gpt-5.6-luna"),
            api_key=api_key,
            proxy=os.getenv("AI_HTTP_PROXY", "http://egress-proxy:3128").strip() or None,
        )

    if selected == "gemini":
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key or api_key.startswith("CHANGE_ME"):
            return DisabledModelProvider("Set GEMINI_API_KEY in your local .env to enable Gemini.")
        return OpenAICompatibleProvider(
            name="gemini",
            base_url=os.getenv(
                "GEMINI_BASE_URL",
                "https://generativelanguage.googleapis.com/v1beta/openai",
            ),
            model=os.getenv("GEMINI_MODEL", "gemini-3.6-flash"),
            api_key=api_key,
            proxy=os.getenv("AI_HTTP_PROXY", "http://egress-proxy:3128").strip() or None,
        )

    if selected == "ollama":
        return OpenAICompatibleProvider(
            name="ollama",
            base_url=os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434/v1"),
            model=os.getenv("OLLAMA_MODEL", "qwen2.5:7b"),
            api_key=os.getenv("OLLAMA_API_KEY", "").strip(),
            proxy=None,
        )

    return DisabledModelProvider(
        f"Unsupported AI_PROVIDER '{selected}'. Choose 'bynara', 'gemini', 'ollama', or 'disabled'."
    )
