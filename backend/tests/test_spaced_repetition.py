from datetime import datetime, timezone

import pytest

from app.intelligence.cognitive.spaced_repetition import SM2SpacedRepetitionScheduler


def test_sm2_first_success_schedules_one_day_then_six_days():
    scheduler = SM2SpacedRepetitionScheduler()
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)

    first = scheduler.review(
        grade=4, repetition_count=0, interval_days=0,
        ease_factor=2.5, lapse_count=0, mastery_score=0.0,
        reviewed_at=now,
    )
    assert first.repetition_count == 1
    assert first.interval_days == 1
    assert first.due_at == datetime(2026, 1, 2, tzinfo=timezone.utc)

    second = scheduler.review(
        grade=4, repetition_count=first.repetition_count,
        interval_days=first.interval_days, ease_factor=first.ease_factor,
        lapse_count=first.lapse_count, mastery_score=first.mastery_score,
        reviewed_at=first.due_at,
    )
    assert second.repetition_count == 2
    assert second.interval_days == 6


def test_failed_recall_resets_repetition_sequence_and_increments_lapses():
    result = SM2SpacedRepetitionScheduler().review(
        grade=1, repetition_count=4, interval_days=30,
        ease_factor=2.5, lapse_count=2, mastery_score=0.8,
        reviewed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    assert result.repetition_count == 0
    assert result.interval_days == 1
    assert result.lapse_count == 3
    assert result.mastery_score < 0.8


def test_ease_factor_has_sm2_lower_bound():
    result = SM2SpacedRepetitionScheduler().review(
        grade=0, repetition_count=0, interval_days=0,
        ease_factor=1.3, lapse_count=0, mastery_score=0.5,
    )
    assert result.ease_factor >= 1.3


@pytest.mark.parametrize("grade", [-1, 6])
def test_invalid_grades_are_rejected(grade):
    with pytest.raises(ValueError, match="grade"):
        SM2SpacedRepetitionScheduler().review(
            grade=grade, repetition_count=0, interval_days=0,
            ease_factor=2.5, lapse_count=0, mastery_score=0.0,
        )
