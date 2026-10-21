"""Shared fixtures. Every test here runs offline: no GPU, slime, network or API key."""

from __future__ import annotations

import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:  # allow `pytest` without `pip install -e .`
    sys.path.insert(0, str(ROOT))

import qqr  # noqa: E402,F401  (populates the registries)
from qqr.schemas import LLMRewardModel  # noqa: E402


class QualityJudge(LLMRewardModel):
    """Deterministic pairwise judge: score = hidden quality of the trajectory.

    Each trajectory is ``[{"role": "assistant", "quality": q}]``. Records
    every comparison so tests can assert on call counts and pairings.
    """

    def __init__(self):
        super().__init__(llm=None)
        self.calls: list[tuple[float, float]] = []

    async def compute(self, prediction, reference=None, *args, query: str = "", **kwargs):
        a = prediction[-1]["quality"]
        b = reference[-1]["quality"]
        self.calls.append((a, b))
        return {"prediction": a, "reference": b}


def make_group(qualities):
    return [[{"role": "assistant", "quality": float(q)}] for q in qualities]


@pytest.fixture
def judge():
    return QualityJudge()
