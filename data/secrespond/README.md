# SecRespond

<h4 align="center">
    <p>
        <b>English</b>&nbsp; | &nbsp;
        <a href="README_zh.md">中文</a>
    </p>
</h4>

<p align="center">
    🤗 <a href="https://huggingface.co/datasets/Alibaba-NLP/SecRespond">Hugging Face</a>&nbsp; | &nbsp;
    🤖 <a href="https://modelscope.cn/datasets/iic/SecRespond">ModelScope</a>&nbsp; | &nbsp;
    📄 <a href="https://arxiv.org/abs/2607.26791">Paper</a>
</p>

## Introduction

**SecRespond: Benchmarking AI Agents for Real-World Post-Compromise Incident Response** evaluates whether an AI agent can investigate a compromised host after an attack has already succeeded.

For each cyber range, the responder receives a frozen forensic disk snapshot together with synthetic host-security-product outputs, then produces an evidence-backed incident analysis and remediation plan. The benchmark focuses on post-compromise investigation and response rather than pre-compromise vulnerability discovery.

## Package Layout

The full Hugging Face dataset uses the layout below. Paths are relative to the
dataset repository root:

```text
.
├── LICENSE
├── README.md
├── README_zh.md
├── task-prompts/
│   ├── linux.md
│   └── windows.md
├── evaluation/
│   ├── SKILL.md
│   └── prompt.md
└── ranges/
    └── <range>/
        ├── checklist.md
        ├── checklist.en.md
        ├── sas-mock/
        ├── disk.tar.gz
        └── disk.tar.gz.sha256
```

The GitHub tree contains the same lightweight benchmark assets but intentionally excludes `disk.tar.gz`, `disk.tar.gz.sha256`, and expanded `disk/` trees. The full Hugging Face dataset adds one archive and checksum per range.

The full dataset contains two response-agent prompts, two evaluator files, and 10 ranges. Every range has an authoritative `checklist.md`, an aligned English `checklist.en.md`, one `disk.tar.gz`, and one `disk.tar.gz.sha256`; the available `sas-mock` files vary by range.

| Path                                | Purpose                                                                                             |
| :---------------------------------- | :-------------------------------------------------------------------------------------------------- |
| `task-prompts/`                     | Platform-specific response-agent prompts.                                                           |
| `evaluation/`                       | Evaluator prompt and benchmark scoring Skill.                                                       |
| `ranges/<range>/checklist.md`       | Expert ground-truth scoring rubric.                                                                 |
| `ranges/<range>/checklist.en.md`    | Aligned English translation of the scoring rubric.                                                  |
| `ranges/<range>/sas-mock/`          | Small synthetic alerts, vulnerability findings, or baseline results. Available files vary by range. |
| `ranges/<range>/disk.tar.gz`        | Compressed synthetic forensic filesystem.                                                           |
| `ranges/<range>/disk.tar.gz.sha256` | Integrity checksum for the range archive.                                                           |
| `ranges/<range>/disk/`              | Extracted, read-only forensic workspace created at runtime.                                         |

Do not invent placeholder `sas-mock` files when a category is absent. Expanded
`disk/` trees are runtime artifacts and are not included in the dataset.

## Task and Evaluation Assets

### Response Agent

The `task-prompts/` directory contains two complete, standalone no-skill responder prompts:

| Range platform | Prompt                    |
| :------------- | :------------------------ |
| Linux          | `task-prompts/linux.md`   |
| Windows        | `task-prompts/windows.md` |

Select exactly one prompt according to the range platform. Do not concatenate the Linux and Windows prompts.

Each responder prompt uses the following placeholders:

| Placeholder       | Value supplied by the harness                       |
| :---------------- | :-------------------------------------------------- |
| `{{DISK_PATH}}`   | Path to the extracted, read-only `disk/` tree.      |
| `{{SAS_PATH}}`    | Path to the selected range's `sas-mock/` directory. |
| `{{OUTPUT_PATH}}` | Writable directory for responder outputs.           |

The responder writes five files:

| Output                | Purpose                                                                   |
| :-------------------- | :------------------------------------------------------------------------ |
| `progress.md`         | Investigation timeline and working checklist.                             |
| `intrusion-report.md` | Attack-chain reconstruction, evidence, entities, persistence, and impact. |
| `vuln-report.md`      | Verification of exploited or relevant vulnerabilities.                    |
| `baseline-report.md`  | Assessment of risky configuration and exposed services.                   |
| `remediation-plan.md` | Prioritized, correct, complete, and verifiable remediation steps.         |

All five files are required. `run_task.sh` returns exit code `4` when the
model run succeeds but any required output is missing. `run_evaluation.sh`
checks the complete set before creating its output workspace and exits before
the model call if any report is missing.

### Evaluator

The evaluator consists of a prompt plus the benchmark scoring Skill:

```text
evaluation/
├── SKILL.md
└── prompt.md
```

Render `prompt.md` with these placeholders:

| Placeholder                  | Value supplied by the harness                                                                   |
| :--------------------------- | :---------------------------------------------------------------------------------------------- |
| `{{CHECKLIST_PATH}}`         | Path to `ranges/<range>/checklist.md`.                                                          |
| `{{DETECTION_REPORTS_PATH}}` | Directory containing the responder reports. The name follows the paper's detection terminology. |
| `{{EVALUATION_SKILL_PATH}}`   | Path to `evaluation/SKILL.md`.                                                                  |
| `{{OUTPUT_PATH}}`            | Writable directory for evaluator outputs.                                                       |

The evaluator writes:

- `evaluation-report.md`: per-checkpoint scores, rationale, quoted evidence, and summaries.
- `scores.json`: structured per-checkpoint detection and plan scores with an overall summary.

## Restoring a Range Disk

After downloading the full Hugging Face dataset, each range includes
`disk.tar.gz` and `disk.tar.gz.sha256`. From the dataset repository root,
verify a selected archive before extracting it:

```bash
RANGE=ssh-miner
RANGE_DIR="ranges/${RANGE}"

(cd "$RANGE_DIR" && sha256sum -c disk.tar.gz.sha256 && tar -xzf disk.tar.gz)
```

The archive must extract beneath a single top-level `disk/` directory:

```text
ranges/ssh-miner/disk/
```

Expose the extracted directory to the responder as a read-only forensic workspace. A single aggregate archive containing every range is not a substitute for the per-range `disk.tar.gz` release contract.

## Runtime Integration Contract

The prompt and Skill files are static assets and are not discovered implicitly. A compatible harness must:

1. Select `task-prompts/linux.md` or `task-prompts/windows.md` from the range platform.
2. Render `DISK_PATH`, `SAS_PATH`, and `OUTPUT_PATH` into the selected responder prompt.
3. Run the responder on an analysis machine with the forensic disk exposed read-only.
4. Render all four evaluator placeholders and load `evaluation/SKILL.md`.
5. Evaluate the responder outputs against the selected range's `checklist.md`.

The standalone Hugging Face dataset payload does not include executable runner
code. The qqr repository provides two OpenCode runner scripts under
`scripts/secrespond/`:

- `scripts/secrespond/run_task.sh`: run the response task for one range.
- `scripts/secrespond/run_evaluation.sh`: evaluate the completed response reports for one range.

Running these scripts requires [OpenCode](https://opencode.ai/docs/en#install). Follow the official installation and configuration documentation before running the examples below.

Run both scripts from the qqr repository root:

```bash
DATA_DIR=/path/to/secrespond
TASK_OUTPUT=/path/to/task-output
EVALUATION_OUTPUT=/path/to/evaluation-output
MODEL=alibaba-cn/qwen3.7-max  # Replace with a model configured in OpenCode.

scripts/secrespond/run_task.sh ssh-miner \
  --data-dir "$DATA_DIR" \
  --disk-path "$DATA_DIR/ranges/ssh-miner/disk" \
  --output-dir "$TASK_OUTPUT" \
  --model "$MODEL"

scripts/secrespond/run_evaluation.sh ssh-miner \
  --data-dir "$DATA_DIR" \
  --reports-dir "$TASK_OUTPUT" \
  --output-dir "$EVALUATION_OUTPUT" \
  --model "$MODEL"
```

`--data-dir` must point to the dataset root containing `task-prompts/`,
`evaluation/`, and `ranges/`. The task runner defaults to
`ranges/<range>/disk` and `ranges/<range>/sas-mock` beneath that root; use
`--disk-path` or `--sas-path` when either input lives elsewhere. It reads the
selected disk directory in place and does not copy or symlink it, so expose a
read-only mount or an isolated copy when the source must be protected.

`run_task.sh` renders one standalone platform prompt. `run_evaluation.sh`
renders all four evaluator placeholders and references `evaluation/SKILL.md`
by its concrete path. Both scripts use OpenCode's normal configuration
discovery; configure providers, endpoints, and credentials in OpenCode itself.
`--model` selects a configured model and may be omitted when OpenCode has a
default. Both scripts support `--prepare-only` for validation without a model
call.

Older integrations built around the former nested `agents/` layout,
`{{SKILLS_PATH}}`, or `{{RESPONDER_OUTPUT_PATH}}` must be updated before use.
The evaluator accepts only `CHECKLIST_PATH`, `DETECTION_REPORTS_PATH`,
`EVALUATION_SKILL_PATH`, and `OUTPUT_PATH`.

## Range Inputs

Each range supplies three logical inputs:

| Input                         | Purpose                                                                                                                             |
| :---------------------------- | :---------------------------------------------------------------------------------------------------------------------------------- |
| `ranges/<range>/disk/`        | Synthetic forensic snapshot containing logs, residual files, configuration changes, persistence artifacts, and other attack traces. |
| `ranges/<range>/sas-mock/`    | Partial synthetic security-product evidence. Alerts are starting points, not complete ground truth.                                 |
| `ranges/<range>/checklist.md` | Authoritative scoring contract defining evidence, attribution, remediation expectations, and capability tags.                       |

Each range also includes `ranges/<range>/checklist.en.md` as an aligned English translation. The runner-facing authoritative contract remains `checklist.md`.

SecRespond intentionally mixes alert-visible and silent artifacts. Complete investigations require proactive disk analysis rather than simply restating alerts.

## Ranges

The current package contains 10 cyber ranges spanning four entry-point types, 21 MITRE ATT&CK techniques, and five operating systems.

| Range               | Entry type                       | Scenario summary                                                                                                            | Platform             | Checkpoints |
| :------------------ | :------------------------------- | :-------------------------------------------------------------------------------------------------------------------------- | :------------------- | ----------: |
| `ssh-miner`         | Baseline weakness                | SSH brute force followed by cryptomining and redundant persistence.                                                         | Linux (CentOS 7)     |          23 |
| `shiro-fastjson`    | Known CVE                        | Shiro default key and Fastjson deserialization leading to webshells, privilege escalation, and mining.                      | Linux (CentOS 8)     |          45 |
| `log4j-rce`         | Known CVE                        | Log4Shell exploitation followed by webshell deployment, privilege escalation, persistence, and mining.                      | Linux (CentOS 8)     |          22 |
| `docker-escape`     | Baseline weakness                | Exposed Docker API followed by container escape and host takeover.                                                          | Linux (Ubuntu 20.04) |          24 |
| `redis-rce`         | Baseline weakness                | Unauthenticated Redis used for SSH-key injection, root access, mining, and persistence.                                     | Linux (Ubuntu 22.04) |          24 |
| `jenkins-rce`       | Business code                    | Jenkins Script Console execution followed by mining, credential theft, and persistence.                                     | Linux (Ubuntu 22.04) |          24 |
| `nextjs-rce`        | Known CVE                        | Next.js RCE followed by privilege escalation, rootkit-style behavior, and mining.                                           | Linux (Ubuntu 22.04) |          37 |
| `npm-worm`          | Supply chain                     | Malicious npm package followed by worm propagation, credential theft, C2, and mining.                                       | Linux (Ubuntu 22.04) |          39 |
| `aspnet-viewstate`  | Known CVE                        | ASP.NET ViewState deserialization followed by RCE, webshell deployment, credential theft, and persistence.                  | Windows Server       |          22 |
| `rdp-service-abuse` | Baseline weakness                | RDP password spraying followed by weak-service-permission abuse, SYSTEM execution, persistence, credential dumping, and C2. | Windows Server       |          20 |

## Evaluation

Each range's `checklist.md` is the authoritative evaluation contract; `checklist.en.md` is its aligned English translation. SecRespond organizes incident-response capability into five categories:

| Capability                             | Description                                                                                                                                                |
| :------------------------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Intrusion Entity (ENT)                 | Identify and handle malicious processes, files, network endpoints, and tampered artifacts.                                                                 |
| Persistence Mechanism (PER)            | Discover and remediate reboot-surviving implants such as scheduled tasks, services, shell hooks, webshells, account backdoors, WMI, or loader-level hooks. |
| Baseline Risk (BAS)                    | Identify unsafe host configuration, exposed services, weak credentials, and privilege risks.                                                               |
| Vulnerability Risk (VUL)               | Verify exploited or otherwise relevant software vulnerabilities.                                                                                           |
| Investigation and Response Quality (Q) | Assess attack-chain reconstruction, evidence quality, honesty, completeness, remediation verification, and business-impact awareness.                      |

Detection and plan are scored independently:

| Dimension | Maximum | Meaning                                                                               |
| :-------- | ------: | :------------------------------------------------------------------------------------ |
| Detection |       3 | Discovery, concrete evidence, and correct attribution.                                |
| Plan      |       2 | Correct remediation action and completeness, including verification and side effects. |

Some checkpoints are detection-only and therefore have no plan score; others
are plan-only and therefore have no detection score. N/A dimensions are
excluded from their respective aggregates. Quality (`Q`) items may be reported
separately from capability aggregation as specified by the individual
checklist. Do not combine Detection and Plan into a single score.

## Citation

If you use SecRespond in your research, please cite:

```bibtex
@misc{wang2026secrespondbenchmarkingaiagents,
  title={SecRespond: Benchmarking AI Agents for Real-World Post-Compromise Incident Response},
  author={Lehan Wang and Boli Chen and Ruixue Ding and Pengjun Xie and Jinwei Huang and Zhendong Liu and Shuo Wang and Tao Lei and Xin Ouyang and Xiaomeng Li},
  year={2026},
  eprint={2607.26791},
  archivePrefix={arXiv},
  primaryClass={cs.CR},
  url={https://arxiv.org/abs/2607.26791},
}
```

## Ethics Statement

### Third-Party Model Evaluation

The third-party models included in our evaluation were assessed solely for academic research. All reported results were obtained in a controlled experimental environment and are presented only for capability comparison and technical discussion. The inclusion of model and provider names and scores does not imply any official position or endorsement by the corresponding providers or brands. Neither outputs obtained from these services nor the resulting evaluation records are used to train, fine-tune, or distill any competing model.

### Security Research and Use Restrictions

All benchmark data were generated in isolated experimental environments under our authorization and control, rather than collected from production systems. Each cyber range is a host that we provisioned, compromised, and snapshotted for this purpose. The released forensic and security-product artifacts are synthetic and contain no data from customer, production, or real-world business systems. We sanitized every disk snapshot by replacing real credentials, keys, and personal data with placeholders, retaining only the forensic artifacts required for analysis. The attack techniques, CVEs, and exploitation methods represented in the scenarios are derived solely from public knowledge bases and vulnerability disclosures, such as MITRE ATT&CK and public vulnerability databases. The benchmark contains forensic evidence rather than runnable exploit chains; it includes no proprietary or internally developed advanced attack techniques and no incremental attack information beyond public sources, and it cannot be directly used to conduct attacks against real-world systems. The benchmark is intended exclusively for defensive security research. Any use for unauthorized intrusion, destructive testing, offensive activity, or any other purpose that violates applicable laws or regulations is strictly prohibited.

## License

The dataset files in this repository are licensed under the [Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License (CC BY-NC-SA 4.0)](https://creativecommons.org/licenses/by-nc-sa/4.0/). See [LICENSE](LICENSE) for the full license text.
