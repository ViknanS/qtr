import asyncio

import numpy as np

from qqr import registers
from qqr.schemas import GroupRewardModel, LLMRewardModel

from ._common import (
    judge_scores,
    normalize_group_rewards,
    rank_based_rewards,
    rank_min_descending,
    validate_predictions,
)


@registers.reward_model("anchor")
class AnchorBasedRankingGroupRewardModel(GroupRewardModel):
    """Anchor-based ranking: every rollout is compared against rollout 0.

    Cost: ``N - 1`` pairwise judgements. The anchor's own score is the mean of
    the scores it received across all comparisons.
    """

    def __init__(self, llm_judge: LLMRewardModel):
        super().__init__()

        self.llm_judge = llm_judge

    async def compute(self, predictions: list[list[dict]], query: str) -> list[float]:
        group_size = validate_predictions(predictions)
        if group_size < 2:
            return [0.0] * group_size

        pivot_idx = 0
        pivot_prediction = predictions[pivot_idx]
        pivot_scores = [5.0] * group_size
        other_scores = [5.0] * group_size
        indices = list(range(1, group_size))
        tasks = []
        async with asyncio.TaskGroup() as tg:
            for idx in indices:
                task = tg.create_task(
                    self.llm_judge(predictions[idx], pivot_prediction, query=query)
                )
                tasks.append(task)

        for idx, task in zip(indices, tasks):
            other_score, pivot_score = judge_scores(task.result())
            other_scores[idx] = other_score
            pivot_scores[idx] = pivot_score

        pivot_scores = pivot_scores[1:]
        pivot_mean_score = float(np.mean(pivot_scores))
        scores = [pivot_mean_score] + other_scores[1:]
        ranks = rank_min_descending(scores)

        return normalize_group_rewards(rank_based_rewards(ranks))
