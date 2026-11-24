from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass(frozen=True)
class SpacedRepetitionResult:
    repetition_count: int
    interval_days: int
    ease_factor: float
    lapse_count: int
    due_at: datetime
    mastery_score: float


class SM2SpacedRepetitionScheduler:
    """A transparent SuperMemo-2-inspired schedule for user-rated retrieval practice.

    Grades are supplied by the learner (0–5). This is a software learning aid,
    not a model of human synaptic plasticity or a guarantee of retention.
    """

    MIN_EASE_FACTOR = 1.30

    def review(
        self,
        *,
        grade: int,
        repetition_count: int,
        interval_days: int,
        ease_factor: float,
        lapse_count: int,
        mastery_score: float,
        reviewed_at: datetime | None = None,
    ) -> SpacedRepetitionResult:
        if not 0 <= grade <= 5:
            raise ValueError("grade must be between 0 and 5")
        if repetition_count < 0 or interval_days < 0 or lapse_count < 0:
            raise ValueError("Schedule counters cannot be negative")
        if ease_factor < self.MIN_EASE_FACTOR:
            raise ValueError(f"ease_factor cannot be below {self.MIN_EASE_FACTOR}")
        if not 0.0 <= mastery_score <= 1.0:
            raise ValueError("mastery_score must be between 0 and 1")

        now = reviewed_at or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        # SM-2 ease adjustment. A grade below 3 means the learner could not
        # reliably retrieve the item, so the repetition sequence restarts.
        delta = 0.1 - (5 - grade) * (0.08 + (5 - grade) * 0.02)
        new_ease = max(self.MIN_EASE_FACTOR, ease_factor + delta)

        if grade < 3:
            new_repetitions = 0
            new_interval = 1
            new_lapses = lapse_count + 1
        else:
            new_repetitions = repetition_count + 1
            if new_repetitions == 1:
                new_interval = 1
            elif new_repetitions == 2:
                new_interval = 6
            else:
                new_interval = max(1, round(max(interval_days, 1) * new_ease))
            new_lapses = lapse_count

        # Self-rated recall is noisy; use a conservative moving average and
        # keep it separate from factual confidence in semantic_knowledge.
        observed_mastery = grade / 5.0
        new_mastery = min(1.0, max(0.0, 0.7 * mastery_score + 0.3 * observed_mastery))
        due_at = now + timedelta(days=new_interval)

        return SpacedRepetitionResult(
            repetition_count=new_repetitions,
            interval_days=new_interval,
            ease_factor=round(new_ease, 2),
            lapse_count=new_lapses,
            due_at=due_at,
            mastery_score=round(new_mastery, 4),
        )
