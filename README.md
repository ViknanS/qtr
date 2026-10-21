# qqr

<p align="center">
  <a href="https://viknans.github.io/qtr/"><b>🌐 Project website &amp; interactive tournament simulator → viknans.github.io/qtr</b></a>
</p>

<p align="center">
  <a href="https://viknans.github.io/qtr/"><img alt="Website" src="https://img.shields.io/badge/website-viknans.github.io%2Fqtr-6d4ee8"></a>
  <a href="https://github.com/ViknanS/qtr/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/ViknanS/qtr/actions/workflows/ci.yml/badge.svg"></a>
  <img alt="Python" src="https://img.shields.io/badge/python-3.11%2B-3776ab">
  <img alt="License" src="https://img.shields.io/badge/license-Apache--2.0-blue">
</p>

> This is the **ViknanS/qtr** fork of [Alibaba-NLP/qqr](https://github.com/Alibaba-NLP/qqr). All research code (ArenaRL, ARISE-RL, RTI, SecRespond) is by the original authors under Apache-2.0. The fork adds bug fixes, macOS-friendly installs, an offline test suite and the project website; see [CHANGES.md](CHANGES.md).

<h4 align="center">
    <p>
        <b>English</b>&nbsp; | &nbsp;
        <a href="README_zh.md">中文</a>
    </p>
</h4>

<p align="center">
    <img src="assets/Logo.png" width="540"/>
<p>

<p align="center">
    🤗 <a href="https://huggingface.co/collections/Alibaba-NLP/arenarl">HuggingFace</a>&nbsp; | &nbsp;
    🤖 <a href="https://modelscope.cn/datasets/iic/Open-Travel">ModelScope</a>&nbsp; | &nbsp;
    📰 <a href="https://tongyi-agent.github.io/blog/arenarl/">Blog</a>&nbsp; | &nbsp;
    📑 <a href="https://huggingface.co/papers/2601.06487">Paper</a>
<p>

`qqr` (a.k.a. hilichurl) is a lightweight, non-intrusive extension for [`slime`](https://github.com/THUDM/slime). It seamlessly integrates the [Model Context Protocol (MCP)](https://github.com/modelcontextprotocol) standard to enable the evolution of open-ended agents via [**ArenaRL**](https://arxiv.org/abs/2601.06487).

## 📰 News
- **[2026.10.12]** 🔥 We release [**RTI**](https://arxiv.org/abs/2610.13438) (Rollout-Time Intervention), which leverages reward-side evidence to intervene on and correct failed trajectories, enabling agentic RL to surpass the policy's original capability boundary and stably learn from successful trajectories beyond its own exploration capacity.
- **[2026.08.28]** 🔥 We release [**ARISE-RL**](https://arxiv.org/abs/2609.01058) (Agentic Rubric-Grounded Iterative Self-Evolution with RL), a full-cycle self-evolution RL framework for open-ended agents, together with the [Generator/Solver training code](qqr/examples/) and the expert-calibrated rubric benchmark suite [**ECR-Bench**](data/) (ECR-DeepResearch + ECR-Travel).
- **[2026.07.30]** 🔥 We release [**SecRespond**](https://arxiv.org/abs/2607.26791), a benchmark for real-world post-compromise incident response, together with its [dataset and evaluation scripts](data/secrespond/).
- **[2026.05.01]** 🎉 Our paper ArenaRL has been accepted by **ICML 2026**!

## 🌟 Key Features

- **ArenaRL Algorithm**: Full implementation of the core algorithms described in the paper. It includes built-in topologies for Anchor-Based, Round-Robin, Swiss-System, Double-Elimination, and Seeded Single-Elimination tournaments.
- **Built for Open-Ended Agents**: Specifically engineered to tackle discriminative collapse in complex, open-ended tasks, ensuring continuous policy improvement via relative ranking even when reward model scores stagnate.
- **MCP Support**: Seamlessly integration with the [MCP]((https://github.com/modelcontextprotocol)) standardizes the decoupling of LLM inference and tool environments. Developers can reuse existing MCP Servers as training environments without rewriting interfaces.
- **High-Performance Training**: Built on top of [`slime`](https://github.com/THUDM/slime) to deliver high-throughput, distributed rollout generation and training for large-scale agent evolution.

## 📦 Installation

`qqr` needs **Python 3.11+**. The core package (tournament reward models, MCP integration, prompt parsers, LLM clients) installs on any machine, including macOS on Apple silicon; **training** additionally needs [`slime`](https://github.com/THUDM/slime) on a Linux host with NVIDIA GPUs.

```bash
git clone https://github.com/ViknanS/qtr.git
cd qtr
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,tools]"     # core + MCP tool servers + test tooling

python -m qqr.doctor              # reports what can run on this machine
python -m qqr.demo                # all 5 tournaments on sample data, mock judge, offline
pytest                            # offline test suite (no GPU, no API keys)
```

Optional extras: `.[tau2]` (vendored τ²-bench environments), `.[examples]` (runtime deps of the example rollouts). For training, first install slime at the paired version (see [Compatibility](docs/en/get_started/compatibility.md) and slime's [Quick Start](https://thudm.github.io/slime/get_started/quick_start.html)), then `pip install -e ".[tools,examples]"`.

Credentials are read from environment variables. Copy [`.env.example`](.env.example) to `.env` (git-ignored), fill in only what your experiment needs, and load it with `set -a; source .env; set +a`.

### Platform support

| Component | macOS / Linux laptop | Linux + NVIDIA GPUs |
|---|---|---|
| Tournament reward models (`qqr.reward_models.arena`) | ✅ | ✅ |
| MCP client wrapper + bundled MCP tool servers | ✅ (tools need their API keys) | ✅ |
| Qwen3 / Qwen3.5 parsers, data utils, RTI helper maths | ✅ | ✅ |
| τ²-bench environments (`.[tau2]`) | ✅ | ✅ |
| Agent rollout, RTI reference scoring, training scripts | ❌ needs slime + sglang | ✅ 8 GPUs/node by default |

The launchers in `scripts/` force-kill leftover sglang / Ray / training processes before starting, so they **refuse to run** unless the host is Linux with `nvidia-smi` (override with `QQR_FORCE_RUN=1` on a dedicated GPU node only).

### Website

The site in [`docs/`](docs/) is plain HTML/CSS/JS with no build step and is published by GitHub Pages from the `/docs` folder of `main`. Preview it locally under the same `/qtr/` base path:

```bash
python scripts/dev/serve_site.py      # http://127.0.0.1:8000/qtr/
```

## 🚀 Quick Start

On a Linux GPU node with slime installed, run the travel experiment with:

```bash
bash scripts/travel/run-qwen3-8B.sh
```

To try the ranking logic without GPUs, run `python -m qqr.demo` or open the [interactive simulator](https://viknans.github.io/qtr/#simulator).

You can configure the experiment in [`qqr/examples/travel/config.py`](qqr/examples/travel/config.py).

## 🧭 ARISE-RL

**ARISE-RL** couples a task/rubric **Generator** and a reasoning **Solver** into a rubric-mediated self-evolution loop. The Generator grounds tool-related rubric criteria in real tool observations and is trained with a difficulty-shaped reward (`R_G = R_tool · R_fmt · (1 + R_diff)`, a triangular reward peaking when the Solver succeeds on about half of its attempts), so that generated tasks track the Solver's capability boundary. The Solver learns from fine-grained rubric satisfaction rewards (`r = 0.8·s + 0.2·𝟙[s=1]`) through multi-step reasoning and tool use. **RG-SED** (Reward-Gated Self-Evolution Distillation) builds a transient teacher from the *same* policy conditioned on coach memory, and applies token-level reverse KL self-distillation only when the memory empirically improves reward (sigmoid gate `σ((Δ_r−τ)/T)`).

### Layout

| Path | Description |
|---|---|
| [`qqr/examples/arise_rl_generator/`](qqr/examples/arise_rl_generator/) | Generator training (deepresearch / travel / vitabench) |
| [`qqr/examples/arise_rl_solver/`](qqr/examples/arise_rl_solver/) | Solver training (deepresearch / travel / vitabench) |
| [`scripts/arise_rl_generator/`](scripts/arise_rl_generator/), [`scripts/arise_rl_solver/`](scripts/arise_rl_solver/) | Training scripts |
| [`data/ecr_deepresearch/`](data/ecr_deepresearch/), [`data/ecr_travel/`](data/ecr_travel/) | **ECR-Bench**: expert-calibrated rubric benchmarks (100 research queries / 5×100 travel-planning queries) |
| [`patches/slime-rg-sed.patch`](patches/) | slime backend patch required by RG-SED |

### Quick Start

```bash
# 0. Apply the RG-SED patch (see patches/README.md)
cd /path/to/slime && git apply /path/to/qqr/patches/slime-rg-sed.patch

# 1. Solver training, e.g. travel planning
bash scripts/arise_rl_solver/travel/run-qwen3.5-9B.sh

# 2. Generator training: start the Solver (executor) service first, then train
bash scripts/arise_rl_generator/travel/start_executor_server.sh
bash scripts/arise_rl_generator/travel/run-qwen3.5-9B.sh
```

Default hyperparameters follow the paper: G=16 rollouts per query (temperature 0.8, up to 40 rounds of tool interaction); K=8 Solver rollouts with success threshold γ=0.9 for the difficulty-shaped Generator reward; Solver reward weighting (0.8, 0.2); RG-SED λ₀=0.5, τ=0.05. Required API credentials are injected via environment variables (`DASHSCOPE_API_KEY`, `AMAP_MAPS_API_KEY`, `SEARCH_API_KEY`/`SEARCH_API_URL`, ...). VitaBench environment data should be obtained from the [official repository](https://github.com/meituan-longcat/vitabench) with `VITABENCH_DATA_DIR` set accordingly.

## 🧭 RTI

**RTI** leverages reward-side evidence (evaluation rubrics) at rollout time to convert erroneous trajectories into successful ones, eliciting learning signals beyond the policy's intrinsic exploration capacity: the intervention pipeline — an MAS consisting of a Reward-Oriented **Validity Judge**, a Policy-Aligned **Corrector** and an Integrity-Constrained **Post-Check** (all instantiated with the policy model itself by default; minimal, leak-suppressed rewrites of the decisive error) — is invoked only when *every* rollout in a group fails. Since intervened trajectories are inherently off-policy (sampled from a calibration behavior distribution π_cal), a **perplexity-based distribution gate** (drop intervened responses with `PPL_roll(ũ_k) > δ`) discards excessive distributional shifts, and **reasoning-shift-aware token reweighting** (the `π_cal/π_roll` likelihood ratio, two-sided clipped to `1±ε_cal` and applied to intervened tokens only) focuses policy updates on the decisive correction tokens; groups without intervention reduce exactly to GRPO. On Navigation, τ²-bench (Telecom/Retail/Airline) and Claw-Eval-Hard20.

### Layout

| Path | Description |
|---|---|
| [`qqr/off_policy/rti/`](qqr/off_policy/rti/) | RTI intervention pipeline: validity judge / corrector / de-leak / post-check agents and PPL reference scoring (`ref_scorer`) |
| [`qqr/off_policy/`](qqr/off_policy/) | Two-stage group rollout and the async training entry (`python3 -m qqr.off_policy.train_async`) |
| [`qqr/reward_models/utils.py`](qqr/reward_models/utils.py) | Reasoning-shift-aware token reweighting (GT-TIS): `reshape_gt_tis_function` |
| [`qqr/examples/navigation/`](qqr/examples/navigation/), [`qqr/examples/tau2_bench/`](qqr/examples/tau2_bench/), [`qqr/examples/claw_eval/`](qqr/examples/claw_eval/) | RTI training examples for the three benchmarks (rollout / reward / inspector prompts) |
| [`scripts/navigation/`](scripts/navigation/), [`scripts/tau2_bench/`](scripts/tau2_bench/), [`scripts/claw_eval/`](scripts/claw_eval/) | Corresponding training scripts |
| [`data/navigation/`](data/navigation/), [`data/tau2_bench/`](data/tau2_bench/), [`data/claw-eval-hard/`](data/claw-eval-hard/) | Training/eval data: multi-waypoint Navigation (Amap Open Platform); τ²-bench Telecom/Retail/Airline with the RL environment database; Claw-Eval-Hard20 + 160 synthesized training tasks |

### Quick Start

```bash
# Navigation (Qwen3-8B / Qwen3.5-9B; requires AMAP_MAPS_API_KEY)
bash scripts/navigation/run-qwen3-8B.sh        # or scripts/navigation/run-qwen3.5-9B.sh

# τ²-bench Telecom (Qwen3-8B; the user-simulator and judge endpoints are configured in the script)
bash scripts/tau2_bench/run-qwen3-8B.sh

# Claw-Eval-Hard (Qwen3.5-9B; requires DASHSCOPE_API_KEY, IDEALAB_API_KEY and E2B_API_KEY)
bash scripts/claw_eval/run-qwen3.5-9B.sh
```

Default hyperparameters follow the paper: G=8 rollouts per query (temperature 0.8); Stage-2 triggers only when the whole group fails and replaces failed samples with calibrated ones (1 sample for τ²-bench / Navigation; up to 2 for Claw-Eval, where a trajectory counts as a success when its official-grader score ≥ 0.75); the PPL gate uses δ=5 (Navigation) / 20 (τ²-bench, Claw-Eval); GT-TIS reweighting is clipped to [0.8, 1.2]. The validity judge / corrector / post-check point by default to a separately served policy endpoint via `INSPECTOR_OPENAI_BASE_URL` / `INSPECTOR_OPENAI_MODEL` / `INSPECTOR_OPENAI_API_KEY` (replace the in-script defaults with your own deployment). Required credentials are injected via environment variables: `AMAP_MAPS_API_KEY`; `USER_SIM_BASE_URL` (with optional `JUDGE_*`) for τ²-bench; `DASHSCOPE_API_KEY`, `IDEALAB_API_KEY`, `E2B_API_KEY` and, when claw_eval is not pip-installed, `CLAW_EVAL_ROOT` pointing to its source checkout.

## 📋 Compatibility

Due to `slime` version upgrades, specifically regarding rollout changes, please use one of the tested version combinations listed in [Compatibility](docs/en/get_started/compatibility.md).

## Acknowledgements

[**slime**](https://github.com/THUDM/slime): For providing a powerful post-training framework.

[**openai-agents-python**](https://github.com/openai/openai-agents-python): For providing excellent MCP interfaces.

## Citation
 
If you use `qqr` or the ArenaRL algorithm in your research, please cite our papers:

```bibtex
@misc{zhang2026arenarlscalingrlopenended,
      title={ArenaRL: Scaling RL for Open-Ended Agents via Tournament-based Relative Ranking}, 
      author={Qiang Zhang and Boli Chen and Fanrui Zhang and Ruixue Ding and Shihang Wang and Qiuchen Wang and Yinfeng Huang and Haonan Zhang and Rongxiang Zhu and Pengyong Wang and Ailin Ren and Xin Li and Pengjun Xie and Jiawei Liu and Ning Guo and Jingren Zhou and Zheng-Jun Zha},
      year={2026},
      eprint={2601.06487},
      archivePrefix={arXiv},
      primaryClass={cs.LG},
      url={https://arxiv.org/abs/2601.06487}, 
}

@article{wang2026secrespond,
  title={SecRespond: Benchmarking AI Agents for Real-World Post-Compromise Incident Response},
  author={Wang, Lehan and Chen, Boli and Ding, Ruixue and Xie, Pengjun and Huang, Jinwei and Liu, Zhendong and Wang, Shuo and Lei, Tao and Ouyang, Xin and Li, Xiaomeng},
  journal={arXiv preprint arXiv:2607.26791},
  year={2026}
}

@misc{zhang2026ariserl,
  title={ARISE-RL: Agentic Rubric-Grounded Iterative Self-Evolution with Reinforcement Learning},
  author={Zhang, Fanrui and Ding, Ruixue and Zhang, Qiang and Chen, Xi
          and Chen, Boli and Wang, Shihang and Wang, Qiuchen
          and Zhan, Hongmin and Bian, Jinxin and Li, Xingchao
          and Zheng, Peijin and Cheng, Hao and Xie, Pengjun
          and Zhang, Kaipeng and Liu, Jiawei and Zha, Zheng-Jun},
  year={2026},
  eprint={2609.01058},
  archivePrefix={arXiv},
  primaryClass={cs.AI}
}

@misc{chen2026rollouttimeinterventionunlockingagentic,
      title={Rollout-Time Intervention: Unlocking Agentic Reinforcement Learning Beyond Policy Limits}, 
      author={Xi Chen and Ruixue Ding and Zhigaoyuan Wang and Fanrui Zhang and Qiang Zhang and Boli Chen and Shihang Wang and Tianfu Wang and Ailin Ren and Pengyong Wang and Pengjun Xie and Hui Xiong},
      year={2026},
      eprint={2610.13438},
      archivePrefix={arXiv},
      primaryClass={cs.AI},
      url={https://arxiv.org/abs/2610.13438}, 
}

```
