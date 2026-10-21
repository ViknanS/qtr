"""Offline ArenaRL tournament demo.

Runs every built-in tournament reward model on a small sample group of
trajectories using a deterministic *mock* pairwise judge, so the ranking
logic can be inspected on any machine (no GPU, no API key, no network).

    python -m qqr.demo                 # pretty table
    python -m qqr.demo --json          # machine-readable output
    python -m qqr.demo --noise 0.5 --seed 7

The mock judge is NOT a language model: it scores each trajectory from a
hand-set latent ``quality`` value (plus optional seeded noise). The numbers
are illustrations of how the tournaments turn pairwise outcomes into
group-normalised rewards - they are not training or benchmark results.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
from dataclasses import dataclass

from qqr.reward_models import get_reward_model
from qqr.schemas import LLMRewardModel

SAMPLE_QUERY = "Plan a relaxed 2-day trip in Hangzhou for two people with a mid-range budget."

# Eight illustrative rollouts for SAMPLE_QUERY. ``quality`` is the hidden
# ground truth the mock judge uses; real training uses an LLM judge instead.
SAMPLE_ROLLOUTS: list[dict] = [
    {"id": "R0", "quality": 6.0, "summary": "Reasonable itinerary, misses opening hours"},
    {"id": "R1", "quality": 8.5, "summary": "Checks weather + transit, balanced pacing"},
    {"id": "R2", "quality": 4.0, "summary": "Generic list, no tool calls"},
    {"id": "R3", "quality": 7.0, "summary": "Good POIs, budget slightly over"},
    {"id": "R4", "quality": 9.0, "summary": "Verified routes, costs and backups"},
    {"id": "R5", "quality": 3.0, "summary": "Hallucinated attraction"},
    {"id": "R6", "quality": 7.0, "summary": "Solid plan, terse explanation"},
    {"id": "R7", "quality": 5.5, "summary": "Over-packed day one"},
]

METHODS = ["anchor", "round_robin", "swiss", "double_elimination", "single_elimination"]


def _as_trajectory(rollout: dict) -> list[dict]:
    """Represent a rollout as the message list the reward models receive."""
    return [
        {"role": "user", "content": SAMPLE_QUERY},
        {"role": "assistant", "content": rollout["summary"], "_mock_quality": rollout["quality"]},
    ]


@dataclass
class MockPairwiseJudge(LLMRewardModel):
    """Deterministic stand-in for an LLM judge (counts its calls)."""

    noise: float = 0.0
    seed: int = 0

    def __post_init__(self):
        self.llm = None
        self.calls = 0
        self._rng = random.Random(self.seed)

    def _score(self, trajectory: list[dict]) -> float:
        quality = float(trajectory[-1].get("_mock_quality", 0.0))
        if self.noise:
            quality += self._rng.gauss(0.0, self.noise)
        return quality

    async def compute(self, prediction, reference=None, *args, query: str = "", **kwargs):
        self.calls += 1
        return {"prediction": self._score(prediction), "reference": self._score(reference)}


async def run_demo(noise: float = 0.0, seed: int = 0) -> dict:
    predictions = [_as_trajectory(r) for r in SAMPLE_ROLLOUTS]
    results = {}
    for method in METHODS:
        judge = MockPairwiseJudge(noise=noise, seed=seed)
        cls = get_reward_model(method)
        kwargs = {"seed": seed} if method in {"swiss", "double_elimination"} else {}
        model = cls(judge, **kwargs)
        rewards = await model(predictions=predictions, query=SAMPLE_QUERY)
        results[method] = {"rewards": rewards, "judge_calls": judge.calls}
    return {
        "query": SAMPLE_QUERY,
        "rollouts": SAMPLE_ROLLOUTS,
        "judge": f"mock (quality + N(0, {noise}^2)), seed={seed}",
        "results": results,
    }


def _print_table(report: dict) -> None:
    rollouts = report["rollouts"]
    print(f"Query : {report['query']}")
    print(f"Judge : {report['judge']}  -- illustrative, not an LLM\n")
    header = f"{'rollout':8s} {'quality':>7s} " + " ".join(f"{m[:12]:>12s}" for m in METHODS)
    print(header)
    print("-" * len(header))
    for i, r in enumerate(rollouts):
        row = f"{r['id']:8s} {r['quality']:7.1f} "
        row += " ".join(f"{report['results'][m]['rewards'][i]:12.3f}" for m in METHODS)
        print(row)
    print("-" * len(header))
    calls = " ".join(f"{report['results'][m]['judge_calls']:12d}" for m in METHODS)
    print(f"{'calls':8s} {'':7s} {calls}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--noise", type=float, default=0.0, help="std-dev of judge noise")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--json", action="store_true", help="print JSON instead of a table")
    args = parser.parse_args(argv)
    if args.noise < 0:
        parser.error("--noise must be >= 0")

    report = asyncio.run(run_demo(noise=args.noise, seed=args.seed))
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        _print_table(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
