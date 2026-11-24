from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any


_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "do", "does",
    "for", "from", "how", "i", "in", "is", "it", "of", "on", "or", "the",
    "this", "to", "was", "what", "when", "where", "which", "with", "you",
}


def _terms(value: str) -> set[str]:
    return {
        term
        for term in re.findall(r"[a-z0-9]{2,}", value.casefold())
        if term not in _STOP_WORDS
    }


class PrefrontalCognitiveController:
    """Allocate a limited context budget to goal-relevant knowledge.

    This is an explicit, deterministic attention policy inspired by selective
    attention and prefrontal cognitive-control research. It is not a model of
    prefrontal neurophysiology.
    """

    def select_relevant(
        self,
        goal: str,
        candidates: Sequence[Mapping[str, Any]],
        *,
        limit: int = 8,
    ) -> list[dict[str, Any]]:
        if limit < 1:
            return []
        goal_terms = _terms(goal)
        if not goal_terms:
            return []

        scored: list[tuple[float, int, dict[str, Any]]] = []
        for index, candidate in enumerate(candidates):
            item = dict(candidate)
            searchable = " ".join(
                str(item.get(key, ""))
                for key in ("title", "content", "knowledge_type", "tags")
            )
            overlap = len(goal_terms & _terms(searchable)) / len(goal_terms)
            database_score = max(0.0, min(float(item.get("retrieval_score", 0.0) or 0.0), 1.0))
            provenance_confidence = max(
                0.0, min(float(item.get("confidence", 0.0) or 0.0), 1.0)
            )
            reinforcement_count = max(0, int(item.get("reinforcement_count", 1) or 1))
            reinforcement = min(reinforcement_count, 5) / 5.0

            # Relevance dominates. Confidence/reinforcement only break ties;
            # they cannot make an unrelated record relevant.
            if overlap <= 0 and database_score <= 0:
                continue
            attention_score = (
                0.75 * overlap
                + 0.15 * database_score
                + 0.07 * provenance_confidence
                + 0.03 * reinforcement
            )
            item["attention_score"] = round(min(attention_score, 1.0), 4)
            item["query_overlap"] = round(overlap, 4)
            scored.append((item["attention_score"], -index, item))

        scored.sort(key=lambda entry: (entry[0], entry[1]), reverse=True)
        return [entry[2] for entry in scored[:limit]]
