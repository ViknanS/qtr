from .llm import LLM
from .prompt import Prompt
from .reward_model import GroupRewardModel, LLMRewardModel, RewardModel

__all__ = [
    "LLM",
    "Prompt",
    "RewardModel",
    "GroupRewardModel",
    "LLMRewardModel",
    "Sample",
]


def __getattr__(name: str):
    # ``Sample`` extends ``slime.utils.types.Sample``. slime is only available
    # in the Linux/CUDA training stack, so it is imported lazily: ``import qqr``
    # (and the reward models, MCP tooling and prompts) keep working on
    # machines without slime, and ``from qqr.schemas import Sample`` raises a
    # clear error only when it is actually needed.
    if name == "Sample":
        try:
            from .sample import Sample
        except ModuleNotFoundError as exc:
            if exc.name and exc.name.split(".")[0] == "slime":
                raise ImportError(
                    "qqr.schemas.Sample requires `slime` (https://github.com/THUDM/slime), "
                    "which is only needed for training. Install the slime version listed in "
                    "docs/en/get_started/compatibility.md (slime v0.3.1 for qqr v0.2.1)."
                ) from exc
            raise
        globals()["Sample"] = Sample
        return Sample
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
