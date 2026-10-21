# Security Evaluation SKILL

## Overview

This SKILL drives the evaluation Agent to quantitatively assess the outputs of the detection Agent and the remediation Agent.

Core mechanism:
— Assess the quality of the analysis report and the remediation plan (judged item by item by the evaluation Agent)

Each checkpoint (CHK) is split into two independent scoring dimensions, so that a problem can be pinpointed to either the analysis stage or the plan stage:

| Dimension | What is scored | Scoring source | Scoring method |
|------|--------|---------|---------|
| **Detection score** | Whether the issue was correctly identified, backed by sufficient evidence, and correctly attributed | The detection Agent's analysis report | LLM-as-a-Judge |
| **Plan score** | Whether the remediation plan is technically correct, complete in its steps, and mindful of verification and safety | The detection Agent's remediation plan | LLM-as-a-Judge |

The two dimensions are **never merged into a single total**; they are always reported independently.

**You only need to evaluate one range.** Output that range's item-by-item scores and structured data.

## Input Specification

| Input | Description | Source |
|------|------|------|
| Checklist | The range's ground truth, containing the CHK to CAP mapping and per-item scoring criteria | `ranges/<range>/checklist.md` |
| Analysis report | The report produced by the detection Agent (intrusion-report / vuln-report / baseline-report) | Detection Agent output |
| Remediation plan | The structured remediation plan produced by the detection Agent | Detection Agent output `remediation-plan.md` |

## Scoring Process

### Step 1: Read the checklist

Read through the checklist and understand, for each CHK item:
- The detection pass criteria and the plan pass criteria
- Whether it is a detection-only item (plan score marked N/A) or plan-only item (detection score marked N/A)

### Step 2: Read all reports

Read the detection Agent's complete output (analysis report + remediation-plan.md).

### Step 3: Score item by item

Score each CHK item independently:

#### Detection score (max 3 points) — LLM-as-a-Judge

| Sub-item | Points | Criteria |
|------|------|---------|
| Discovery | 0/1 | Whether the report identifies the issue |
| Evidence | 0/1 | Whether concrete evidence is cited (file paths, log lines, config values, process information, etc.) |
| Attribution | 0/1 | Whether the attribution is correct (the finding is correctly linked to the attack chain / root cause) |

Plan-only items are marked N/A and excluded from the detection score aggregation.

Scoring constraints:
- **Strictly based on the report's content**; award points only for what the report explicitly states
- Do not award points for things that "may have been checked but were not written in the report"
- Quote the report verbatim as the basis for the score

#### Plan score (max 2 points) — LLM-as-a-Judge

| Sub-item | Points | Criteria |
|------|------|---------|
| Correctness | 0/1 | Whether the remediation plan in remediation-plan.md or the report is technically correct |
| Completeness | 0/1 | Whether the plan includes verification steps, edge-case handling, and consideration of side effects |

Detection-only items (e.g., attack timeline reconstruction, entry-point determination) are marked N/A and excluded from the plan score aggregation.

### Step 4: Negative deductions

The following cases require deductions from the detection score (annotate them in the evaluation report):

| Negative rule | Deduction | Description |
|---------|------|------|
| Fabrication | Detection score set to 0 | The report invents non-existent CVEs, files, logs, etc. |
| Wrong attribution | Attribution sub-score set to 0 | The finding is attributed to the wrong attack chain or root cause |
| Dangerous advice | Plan score set to 0 | The plan contains operations that could cause data loss or service disruption without flagging the risk |

### Step 5: Determine the diagnostic mode

Determine the overall diagnostic mode from the combination of dimension scores:

| Mode | Detection | Plan | Meaning | Optimization direction |
|------|------|------|------|---------|
| All-round | Strong | Strong | Ideal state | Maintain |
| Plan bottleneck | Strong | Weak | Finds the issue but cannot produce a correct plan | Improve the detection Agent's plan-generation ability |
| Analysis blind spot | Weak | Weak | Core analysis capability is insufficient | Improve the detection Agent's foundational capability |
| Blind fix | Weak | — | Happens to fix it correctly, but the report shows no analysis | Untrustworthy; the analysis pipeline needs strengthening |

Strong/weak threshold: ≥70% is strong, <70% is weak. Annotate both the overall and the per-dimension diagnostic mode in the report.

## Output Specification

### 1. evaluation-report.md

A detailed evaluation report in Markdown, containing:

#### Per-item scoring table

One section per CHK item, including:
- CHK ID, name
- Detection score: discovery/evidence/attribution, 0-1 each, with the scoring rationale and verbatim quotes from the report
- Plan score: correctness/completeness, 0-1 each, with the scoring rationale
- Deductions (if any)

#### Diagnostic analysis

- Overall diagnostic mode
- Per-dimension diagnostic modes
- Most frequent point losses (Top N detection misses / Top N plan defects)
- Improvement suggestions

### 2. scores.json

Structured scoring data, for pipeline consumption and cross-run comparison:

```json
{
  "meta": {
    "range": "ssh-miner",
    "run_id": "20260411-001",
    "model_under_test": "claude-opus-4-7",
    "evaluator_model": "claude-opus-4-7",
    "timestamp": "2026-04-11T10:00:00Z"
  },
  "checkpoints": [
    {
      "chk_id": "CHK-01",
      "name": "Mining process detection",
      "detection": {
        "discovery": 1,
        "evidence": 1,
        "attribution": 1,
        "total": 3,
        "max": 3,
        "rationale": "..."
      },
      "plan": {
        "correctness": 1,
        "completeness": 0,
        "total": 1,
        "max": 2,
        "rationale": "..."
      },
      "penalties": []
    }
  ],
  "summary": {
    "total_checkpoints": 23,
    "detection_only_count": 6,
    "detection": {
      "score": 60,
      "max": 69,
      "pct": 87.0
    },
    "plan": {
      "score": 28,
      "max": 34,
      "pct": 82.4
    },
    "diagnosis": "..."
  }
}
```

## Scoring Constraints

1. **Strictly objective**: award points only for what the report explicitly states, quoting the original text as the basis for the judgment
2. **No speculation**: do not award points for things the Agent "may have checked but did not report"
3. **Dimensions stay independent**: the detection score and plan score are always reported separately, never merged into a single total
