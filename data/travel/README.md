# Open-Travel

This directory contains the **RL Training Set** and the **Test Set** (categorized by subtask) for the Open-Travel domain.

## Overview

In the Open-Travel domain, the agent is required to help users accomplish itinerary planning subtasks. These tasks emphasize multi-constraint reasoning, multi-tool coordination, and personalized preferences intertwined with user-specific constraints (e.g., budget limits, time windows, traveling parties, and preference profiles).

## Dataset

### Statistics

| Split           | Samples   | Description                                    |
| :-------------- | :-------- | :--------------------------------------------- |
| **RL Training** | **1,626** | Used for Reinforcement Learning (RL) training. |
| **Test**        | **250**   | Contains 5 subtask files (50 samples each).    |
| **Total**       | **1,876** |                                                |

### Files

*   [`train.jsonl`](train.jsonl)
    *   Contains **1,626** RL training samples.
*   [`test/`](test/)
    *   Contains **250** samples in total, evenly distributed across five distinct subtasks:

| File Name                                                 | Samples | Task Type | Description                                       |
| :-------------------------------------------------------- | :------ | :-------- | :------------------------------------------------ |
| [`search_around.jsonl`](test/search_around.jsonl)         | **50**  | Search    | Nearby point-of-interest (POI) search.            |
| [`direction.jsonl`](test/direction.jsonl)                 | **50**  | Direction | Route planning with multiple specified waypoints. |
| [`compare_itinerary.jsonl`](test/compare_itinerary.jsonl) | **50**  | Compare   | Transportation-mode comparison.                   |
| [`one_day_travel.jsonl`](test/one_day_travel.jsonl)       | **50**  | 1-Day     | One-day trip planning in a single city.           |
| [`multi_day_travel.jsonl`](test/multi_day_travel.jsonl)   | **50**  | M-Day     | Multi-day trip planning (Generalization task).    |

## License
The dataset files listed in this directory are licensed under the [Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0)](https://creativecommons.org/licenses/by-nc/4.0/).
