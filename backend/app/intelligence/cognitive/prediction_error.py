from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RewardPredictionError:
    """A scalar feedback signal inspired by reward-prediction-error models.

    The delta is a software metric (observed reward minus expected reward).
    It is not a dopamine measurement or a claim about subjective feeling.
    """

    expected_reward: float
    observed_reward: float
    delta: float

    @classmethod
    def calculate(cls, expected_reward: float, observed_reward: float) -> "RewardPredictionError":
        for name, value in (
            ("expected_reward", expected_reward),
            ("observed_reward", observed_reward),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be between 0 and 1")
        return cls(
            expected_reward=expected_reward,
            observed_reward=observed_reward,
            delta=round(observed_reward - expected_reward, 4),
        )
