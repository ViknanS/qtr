import math

import pytest

from qqr.reward_models.arena._common import (
    JudgeResultError,
    judge_scores,
    normalize_group_rewards,
    position_rewards,
    rank_based_rewards,
    rank_min_descending,
    validate_predictions,
)


@pytest.mark.parametrize(
    "values",
    [
        [3.0, 1.0, 2.0],
        [1.0, 1.0, 1.0],
        [5.0, 7.0, 7.0, 2.0, 5.0],
        [0.5],
        [2.0, 2.0, 1.0, 3.0, 3.0, 3.0, 0.0, 1.5],
    ],
)
def test_rank_min_matches_pandas(values):
    pd = pytest.importorskip("pandas")
    expected = pd.Series(values).rank(method="min", ascending=False).tolist()
    assert rank_min_descending(values) == expected


def test_rank_based_rewards_complete_tie_is_zero():
    assert rank_based_rewards([1.0, 1.0, 1.0]) == [0.0, 0.0, 0.0]
    assert rank_based_rewards([]) == []


def test_rank_based_rewards_linear():
    assert rank_based_rewards([1.0, 2.0, 3.0]) == [1.0, 0.5, 0.0]


def test_normalize_matches_torch_formula():
    # (x - mean) / (std_unbiased + 1e-6), as previously computed with torch
    x = [1.0, 0.5, 0.0]
    mean = sum(x) / 3
    std = math.sqrt(sum((v - mean) ** 2 for v in x) / 2)
    expected = [(v - mean) / (std + 1e-6) for v in x]
    assert normalize_group_rewards(x) == pytest.approx(expected, abs=1e-6)


def test_normalize_small_groups_are_finite():
    assert normalize_group_rewards([]) == []
    assert normalize_group_rewards([0.7]) == [0.0]
    out = normalize_group_rewards([0.3, 0.3, 0.3])
    assert out == [0.0, 0.0, 0.0]


def test_position_rewards():
    assert position_rewards([2, 0, 1], 3) == [0.5, 0.0, 1.0]
    assert position_rewards([0], 1) == [0.0]


@pytest.mark.parametrize(
    "bad",
    [None, 3.0, {"prediction": 1.0}, {"prediction": "x", "reference": 1}, {"prediction": float("nan"), "reference": 1}],
)
def test_judge_scores_rejects_malformed(bad):
    with pytest.raises(JudgeResultError):
        judge_scores(bad)


def test_judge_scores_accepts_numeric_strings():
    assert judge_scores({"prediction": "7", "reference": 3}) == (7.0, 3.0)


def test_validate_predictions():
    assert validate_predictions([[], []]) == 2
    with pytest.raises(TypeError):
        validate_predictions("not a list")
