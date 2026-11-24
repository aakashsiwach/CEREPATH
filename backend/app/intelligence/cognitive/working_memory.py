from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


class BaddeleyWorkingMemory:
    """A bounded dialogue workspace inspired by Baddeley and Hitch's model.

    This text-only implementation approximates limited-capacity working memory.
    It does not simulate the phonological loop or visuospatial sketchpad neurons.
    The newest turn is protected; older items are dropped when the budget is full.
    """

    def __init__(self, capacity_items: int = 16, capacity_characters: int = 18_000) -> None:
        if capacity_items < 1 or capacity_characters < 1:
            raise ValueError("Working-memory capacity must be positive and usable")
        self.capacity_items = capacity_items
        self.capacity_characters = capacity_characters

    def retain(self, messages: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
        """Select a recent, chronological context window within fixed budgets."""
        retained: list[dict[str, str]] = []
        remaining = self.capacity_characters

        for message in reversed(messages[-self.capacity_items :]):
            role = str(message.get("role", "user"))
            content = str(message.get("content", ""))
            if not content:
                continue
            if len(content) > remaining:
                if not retained and remaining:
                    content = content[:remaining]
                else:
                    break
            retained.append({"role": role, "content": content})
            remaining -= len(content)
            if remaining <= 0:
                break

        retained.reverse()
        return retained
