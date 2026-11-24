from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from .hippocampal_indexing import HippocampalIndexer
from .metacognition import MetacognitiveMonitor, RetrievalAssessment
from .prefrontal_cortex import PrefrontalCognitiveController
from .working_memory import BaddeleyWorkingMemory


@dataclass(frozen=True)
class CognitiveContext:
    working_memory: list[dict[str, str]]
    recalled_knowledge: list[dict[str, Any]]
    retrieval_assessment: RetrievalAssessment


class DigitalMind:
    """Coordinate bounded context, associative recall, and evidence monitoring.

    The module is a cognitive architecture for software. It does not assert
    consciousness, emotions, biological development, or human-level autonomy.
    """

    def __init__(
        self,
        *,
        working_memory: BaddeleyWorkingMemory | None = None,
        hippocampal_indexer: HippocampalIndexer | None = None,
        prefrontal_cortex: PrefrontalCognitiveController | None = None,
        metacognitive_monitor: MetacognitiveMonitor | None = None,
    ) -> None:
        self.working_memory = working_memory or BaddeleyWorkingMemory()
        self.hippocampal_indexer = hippocampal_indexer or HippocampalIndexer()
        self.prefrontal_cortex = prefrontal_cortex or PrefrontalCognitiveController()
        self.metacognitive_monitor = metacognitive_monitor or MetacognitiveMonitor()

    def process_turn(
        self,
        *,
        current_goal: str,
        conversation_history: Sequence[Mapping[str, Any]],
        semantic_candidates: Sequence[Mapping[str, Any]],
        recall_limit: int = 8,
    ) -> CognitiveContext:
        working_memory = self.working_memory.retain(conversation_history)
        recalled = self.prefrontal_cortex.select_relevant(
            current_goal, semantic_candidates, limit=recall_limit
        )
        assessment = self.metacognitive_monitor.assess_retrieval(recalled)
        return CognitiveContext(
            working_memory=working_memory,
            recalled_knowledge=recalled,
            retrieval_assessment=assessment,
        )
