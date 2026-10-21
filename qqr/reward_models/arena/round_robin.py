import asyncio
import itertools

from qqr import registers
from qqr.schemas import GroupRewardModel, LLMRewardModel

from ._common import (
    judge_scores,
    normalize_group_rewards,
    rank_based_rewards,
    rank_min_descending,
    validate_predictions,
)


@registers.reward_model("round_robin")
class RoundRobinGroupRewardModel(GroupRewardModel):
    """Round-robin: every pair of rollouts is judged once.

    Cost: ``N * (N - 1) / 2`` pairwise judgements. A win scores 1 point, a tie
    0.5 points; rollouts are then ranked by total points.
    """

    def __init__(self, llm_judge: LLMRewardModel):
        super().__init__()

        self.llm_judge = llm_judge

    async def compute(self, predictions: list[list[dict]], query: str) -> list[float]:
        group_size = validate_predictions(predictions)
        if group_size < 2:
            return [0.0] * group_size

        wins = [0.0] * group_size
        pairs = list(itertools.combinations(range(group_size), 2))
        tasks = []
        async with asyncio.TaskGroup() as tg:
            for i, j in pairs:
                task = tg.create_task(
                    self.llm_judge(predictions[i], predictions[j], query=query)
                )
                tasks.append(task)

        for (i, j), task in zip(pairs, tasks):
            score_i, score_j = judge_scores(task.result())

            if score_i > score_j:
                wins[i] += 1.0
            elif score_j > score_i:
                wins[j] += 1.0
            else:
                wins[i] += 0.5
                wins[j] += 0.5

        ranks = rank_min_descending(wins)

        return normalize_group_rewards(rank_based_rewards(ranks))
