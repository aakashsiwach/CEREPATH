from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ModelReply:
    text: str
    provider: str
    model: str


class ModelProvider(Protocol):
    """Interface for a future model adapter. Implementations must declare privacy/cost metadata."""

    name: str
    async def complete(self, prompt: str) -> ModelReply: ...


class NoModelConfigured(RuntimeError):
    pass


class DisabledModelProvider:
    """Default provider. Fails closed and never makes a network request."""

    name = "disabled"

    async def complete(self, prompt: str) -> ModelReply:
        raise NoModelConfigured(
            "No model provider is configured. External AI calls are disabled in milestone 0."
        )
