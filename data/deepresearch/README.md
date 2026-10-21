# Open-DeepResearch

This directory contains the **RL Training Set** and the **Test Set** for the Open-DeepResearch domain.

## Overview

In the Open-DeepResearch domain, the agent is required to assist users in conducting multi-turn search, reading, synthesis, and generation to produce an open-ended answer. This domain focuses on complex information retrieval and synthesis tasks.

## Dataset

### Statistics

| Split           | Samples   | Description                                    |
| :-------------- | :-------- | :--------------------------------------------- |
| **RL Training** | **2,216** | Used for Reinforcement Learning (RL) training. |
| **Test**        | **100**   | High-quality benchmark for evaluation.         |
| **Total**       | **2,316** |                                                |

### Files

*   [`train.jsonl`](train.jsonl)
    *   Contains **2,216** RL samples.
    *   Used to further elicit and optimize the model’s open-ended agentic behaviors.
*   [`test.jsonl`](test.jsonl)
    *   Contains **100** Test samples.
    *   A high-quality set designed for leaderboard-style evaluation. All samples have been manually checked for representative clarity, diversity, and difficulty.

## Tasks

The samples in these files cover the following categories:

1.  **Technical Writing:** Assisting users in writing open-ended technical documents (e.g., reports, design documents, or survey-style overviews).
2.  **Ideation & Expansion:** Helping users ideate, expand, or refine research topics, solution plans, or content outlines.
3.  **Explanation & Summarization:** Providing concise yet informative explanations, overviews, or summaries of complex concepts, systems, or domains.

## License
The dataset files listed in this directory are licensed under the [Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0)](https://creativecommons.org/licenses/by-nc/4.0/).
