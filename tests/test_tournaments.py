"""Behavioural tests for the five ArenaRL tournament reward models."""

import math
import random

import pytest
from conftest import QualityJudge, make_group

from qqr.reward_models import get_reward_model
from qqr.reward_models.arena._common import JudgeResultError

ALL = ["anchor", "round_robin", "swiss", "double_elimination", "single_elimination"]
SEEDED = {"swiss", "double_elimination"}


def build(name, judge, seed=0):
    cls = get_reward_model(name)
    return cls(judge, seed=seed) if name in SEEDED else cls(judge)


async def run(name, qualities, seed=0):
    judge = QualityJudge()
    rewards = await build(name, judge, seed)(predictions=make_group(qualities), query="q")
    return rewards, judge


def zscore_ok(rewards):
    n = len(rewards)
    mean = sum(rewards) / n
    var = sum((r - mean) ** 2 for r in rewards) / (n - 1)
    return abs(mean) < 1e-5 and (var == 0 or abs(math.sqrt(var) - 1) < 1e-4)


@pytest.mark.parametrize("name", ALL)
@pytest.mark.parametrize("n", [2, 3, 5, 8, 16])
async def test_rewards_are_group_normalised(name, n):
    qualities = random.Random(n).sample(range(100), n)
    rewards, _ = await run(name, qualities)
    assert len(rewards) == n
    assert all(math.isfinite(r) for r in rewards)
    assert zscore_ok(rewards)


@pytest.mark.parametrize("name", ALL)
@pytest.mark.parametrize("seed", range(10))
async def test_best_rollout_gets_top_reward(name, seed):
    qualities = random.Random(seed).sample(range(1, 50), 8)
    rewards, _ = await run(name, qualities, seed=seed)
    best = qualities.index(max(qualities))
    worst = qualities.index(min(qualities))
    assert rewards[best] == max(rewards)
    if name != "swiss":  # 3 Swiss rounds need not isolate the last place
        assert rewards[worst] == min(rewards)


@pytest.mark.parametrize("name", ["anchor", "round_robin"])
async def test_exhaustive_methods_recover_exact_order(name):
    qualities = [4, 9, 1, 7, 3, 8]
    rewards, _ = await run(name, qualities)
    order_by_reward = sorted(range(6), key=lambda i: -rewards[i])
    assert order_by_reward == sorted(range(6), key=lambda i: -qualities[i])


@pytest.mark.parametrize("name", ["anchor", "round_robin", "swiss"])
async def test_ties_share_reward(name):
    rewards, _ = await run(name, [5, 5, 5, 5])
    assert rewards == [0.0, 0.0, 0.0, 0.0]


@pytest.mark.parametrize(
    "name,n,expected_calls",
    [
        ("anchor", 8, 7),
        ("round_robin", 8, 28),
        ("swiss", 8, 12),  # ceil(log2 8) = 3 rounds x 4 matches
        ("single_elimination", 8, 14),  # 7 seeding + 7 bracket matches
        ("round_robin", 5, 10),
        ("anchor", 5, 4),
    ],
)
async def test_judge_call_counts(name, n, expected_calls):
    _, judge = await run(name, list(range(n)))
    assert len(judge.calls) == expected_calls


async def test_double_elimination_call_count_bounds():
    for n in (4, 7, 8):
        _, judge = await run("double_elimination", list(range(n)))
        # 2N-2 matches, plus one if the grand final is played as an extra round
        assert 2 * n - 3 <= len(judge.calls) <= 2 * n - 1


@pytest.mark.parametrize("name", ALL)
@pytest.mark.parametrize("n", [0, 1])
async def test_degenerate_groups_do_not_crash(name, n):
    rewards, judge = await run(name, list(range(n)))
    assert rewards == [0.0] * n
    assert judge.calls == []


@pytest.mark.parametrize("name", ALL)
async def test_malformed_judge_output_raises_clear_error(name):
    class BadJudge(QualityJudge):
        async def compute(self, *a, **k):
            return {"winner": "A"}

    model = build(name, BadJudge())
    with pytest.raises(BaseException) as info:  # TaskGroup wraps in ExceptionGroup
        await model(predictions=make_group([1, 2, 3, 4]), query="q")
    exc = info.value
    if isinstance(exc, BaseExceptionGroup):
        assert exc.subgroup(JudgeResultError) is not None
    else:
        assert isinstance(exc, JudgeResultError)


@pytest.mark.parametrize("name", sorted(SEEDED))
async def test_seeded_methods_are_reproducible(name):
    q = [3, 8, 1, 6, 6, 2, 9, 4]
    a, _ = await run(name, q, seed=123)
    b, _ = await run(name, q, seed=123)
    assert a == b


async def test_swiss_records_results_for_the_right_players():
    """Regression: ``create_pairings`` used to shuffle ``players`` in place,
    after which ``players[i]`` no longer referred to rollout ``i`` and points
    were credited to the wrong rollouts."""
    for seed in range(25):
        q = random.Random(seed).sample(range(100), 8)
        judge = QualityJudge()
        model = build("swiss", judge, seed)
        rewards = await model(predictions=make_group(q), query="q")
        # Re-derive points from the recorded matches and compare orderings.
        points = {v: 0.0 for v in q}
        for a, b in judge.calls:
            if a > b:
                points[a] += 1
            elif b > a:
                points[b] += 1
        for i in range(8):
            for j in range(8):
                if points[q[i]] > points[q[j]]:
                    assert rewards[i] > rewards[j], (seed, q, rewards)


def test_unknown_reward_model_lists_available():
    with pytest.raises(ValueError) as info:
        get_reward_model("elo")
    for name in ALL:
        assert name in str(info.value)


def test_reward_model_name_with_variant_suffix():
    assert get_reward_model("swiss/8-rounds") is get_reward_model("swiss")
