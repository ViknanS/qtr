"""Shared helpers for the ArenaRL tournament reward models.

These helpers reproduce the numerics previously written inline in every
tournament module (``torch.tensor(...).std()`` z-scoring and
``pandas.Series.rank(method="min")``) using NumPy only, so that the arena
reward models can be imported and unit-tested without PyTorch or pandas.

* ``normalize_group_rewards`` matches ``(x - x.mean()) / (x.std() + 1e-6)``
  on a ``torch.float32`` tensor (``torch.std`` is the unbiased estimator).
* ``rank_min_descending`` matches ``pd.Series(v).rank(method="min",
  ascending=False)``.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any

import numpy as np

EPS = 1e-6


class JudgeResultError(ValueError):
    """Raised when an LLM judge returns a malformed pairwise result."""


def validate_predictions(predictions: Sequence[Any]) -> int:
    """Return the group size after checking ``predictions`` is a sequence."""
    if predictions is None or isinstance(predictions, (str, bytes)):
        raise TypeError(
            "predictions must be a list of trajectories (one per rollout), "
            f"got {type(predictions).__name__}"
        )
    return len(predictions)


def judge_scores(result: Any) -> tuple[float, float]:
    """Extract ``(prediction_score, reference_score)`` from a judge result.

    Every judge in qqr returns ``{"prediction": float, "reference": float}``
    where ``prediction`` is the score of the first trajectory passed in and
    ``reference`` is the score of the second one.
    """
    if not isinstance(result, dict):
        raise JudgeResultError(
            "LLM judge must return a dict with 'prediction' and 'reference' "
            f"scores, got {type(result).__name__}: {result!r}"
        )
    missing = [k for k in ("prediction", "reference") if k not in result]
    if missing:
        raise JudgeResultError(
            f"LLM judge result is missing key(s) {missing}: {result!r}"
        )
    try:
        score_a = float(result["prediction"])
        score_b = float(result["reference"])
    except (TypeError, ValueError) as exc:
        raise JudgeResultError(
            f"LLM judge scores must be numeric, got {result!r}"
        ) from exc
    if not (math.isfinite(score_a) and math.isfinite(score_b)):
        raise JudgeResultError(f"LLM judge scores must be finite, got {result!r}")
    return score_a, score_b


def rank_min_descending(values: Sequence[float]) -> list[float]:
    """Competition ("min") ranking, highest value gets rank 1.

    Equivalent to ``pd.Series(values).rank(method="min", ascending=False)``.
    """
    return [float(1 + sum(1 for other in values if other > v)) for v in values]


def rank_based_rewards(ranks: Sequence[float]) -> list[float]:
    """Map ranks to ``[0, 1]`` with ``(max_rank - r) / (max_rank - 1)``.

    If every participant shares rank 1 (a complete tie) all rewards are 0.
    """
    if not ranks:
        return []
    max_rank = max(ranks)
    if max_rank == 1:
        return [0.0] * len(ranks)
    return [(max_rank - r) / (max_rank - 1) for r in ranks]


def position_rewards(ranked_indices: Sequence[int], group_size: int) -> list[float]:
    """Linear rewards from a total order: first place 1.0, last place 0.0."""
    rewards = [0.0] * group_size
    if group_size < 2:
        return rewards
    for rank_idx, player_idx in enumerate(ranked_indices):
        rewards[player_idx] = 1.0 - (rank_idx / (group_size - 1))
    return rewards


def normalize_group_rewards(rewards: Sequence[float], eps: float = EPS) -> list[float]:
    """Group z-score normalisation used by GRPO-style advantages.

    Groups with fewer than two members carry no relative signal, so they are
    mapped to zero instead of producing ``NaN`` (the unbiased standard
    deviation of a single element is undefined).
    """
    n = len(rewards)
    if n < 2:
        return [0.0] * n
    x = np.asarray(rewards, dtype=np.float32)
    mean = x.mean(dtype=np.float32)
    std = x.std(ddof=1, dtype=np.float32)
    out = (x - mean) / (std + np.float32(eps))
    return [float(v) for v in out]
