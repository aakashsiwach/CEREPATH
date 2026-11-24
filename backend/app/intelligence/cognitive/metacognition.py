from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence


@dataclass(frozen=True)
class RetrievalAssessment:
    evidence_state: str
    retrieved_items: int
    best_attention_score: float
    explanation: str


class MetacognitiveMonitor:
    """Monitor retrieval coverage and expose its limits.

    The assessment says whether the local knowledge store found relevant
    material. It is deliberately NOT a probability that an answer is true.
    """

    def assess_retrieval(
        self, retrieved: Sequence[dict[str, Any]]
    ) -> RetrievalAssessment:
        if not retrieved:
            return RetrievalAssessment(
                evidence_state="no_local_evidence",
                retrieved_items=0,
                best_attention_score=0.0,
                explanation="No matching owner-taught knowledge was retrieved.",
            )

        best_score = max(float(item.get("attention_score", 0.0)) for item in retrieved)
        if best_score >= 0.70:
            state = "strong_retrieval_match"
            explanation = "The local knowledge store contains a strong lexical/context match."
        elif best_score >= 0.35:
            state = "partial_retrieval_match"
            explanation = "Some relevant local knowledge was retrieved; coverage may be incomplete."
        else:
            state = "weak_retrieval_match"
            explanation = "Retrieved material is weakly related; do not present it as decisive evidence."

        return RetrievalAssessment(
            evidence_state=state,
            retrieved_items=len(retrieved),
            best_attention_score=round(best_score, 4),
            explanation=explanation,
        )
