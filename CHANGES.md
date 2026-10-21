# Changes in the ViknanS/qtr fork

Base: `qqr` 0.2.1 from [Alibaba-NLP/qqr](https://github.com/Alibaba-NLP/qqr) (paired with slime v0.3.1).
The research implementations (ArenaRL tournaments, MCP integration, ARISE-RL, RTI, benchmark
integrations, slime patches) are kept; changes are fixes, safety guards, tests and the website.
License (Apache-2.0) and authorship are unchanged.

## Bug fixes

| Area | Problem | Fix |
|---|---|---|
| `reward_models/arena/swiss.py` | `create_pairings` shuffled the `players` list **in place**, after which `players[i]` no longer meant rollout `i`; match points and Buchholz scores were credited to the wrong rollouts. Measured on the original code with a deterministic judge: the best rollout received the top reward in only 3 of 25 groups. | Shuffle a copy; regression test `test_swiss_records_results_for_the_right_players`. |
| All arena reward models | Groups of size 0 or 1 produced `NaN` (unbiased std of one element) or `ZeroDivisionError`; malformed judge output failed with a bare `KeyError`. | Degenerate groups return zeros; judge results are validated with a clear `JudgeResultError`. |
| `import qqr` | Failed without `slime` because `qqr.schemas` imported `slime.utils.types` eagerly, so nothing (reward models, MCP, parsers) could be used or tested on macOS. | `Sample` is loaded lazily with an explanatory `ImportError`. |
| `pyproject.toml` | Declared only `openai-agents` and `cachetools`, but the package imports `httpx` and `numpy` at import time (`ModuleNotFoundError: httpx` on a clean install), and torch/pandas via the arena modules. `requires-python >= 3.10` although every tournament uses `asyncio.TaskGroup` (3.11+). | Complete core deps; optional extras `tools`, `examples`, `tau2`, `dev`; `requires-python >= 3.11`. Arena helpers re-implemented with NumPy (same float32 z-score and `rank(method="min")` semantics), so torch/pandas are no longer needed to compute rewards. |
| `examples/arise_rl_solver/travel/config.py` | `__all__` exported `rg_kl_min_lambda`, which does not exist (`rg_kl_min_lambda_ratio` does). | Corrected; repo-wide test checks every example config's `__all__`. |
| `mcp/server.py` | Example configs pass `env={"KEY": os.getenv("KEY")}`; with an unset key openai-agents raised a pydantic `ValidationError` while constructing the server, i.e. merely importing a config crashed. Cache keys raised on non-JSON arguments. | Unset variables are dropped with a warning naming them; `json.dumps(default=str)`; list blocklists normalised to sets. |
| `off_policy/rti/client.py` | A server that omits `logprobs` made every call raise inside the retry loop, burning all retries (default 10, exponential backoff up to 300 s) before returning an empty string; non-retryable 4xx errors were retried; final failures were silent. | Missing logprobs tolerated, 4xx (except 429) fail fast, final failure logged. |
| `off_policy/rti/utils/metrics.py` | Imported the slime-backed `RefScorer` at module import. | Imported lazily, so the PPL/KL/JS helpers are usable and testable alone. |
| `data/prompts/qwen3_5.py` | A numeric tool argument such as `inf` raised `OverflowError` in `int()`, which the outer handler swallowed, silently dropping **all** tool calls in the message. | `OverflowError` handled per parameter. |
| `data/markdown.py` (`json2md`) | Duplicate list values were all labelled with the index of their first occurrence. | Uses the enumerate index. |
| `examples/claw_eval/inspector_prompts/deleak.py` | Two functions named `build`; the first was dead code. | First renamed `build_zh_legacy`; runtime behaviour unchanged. |

## Data and repository

* The uploaded archive contained **Git-LFS pointer stubs** instead of all 22 `data/**/*.jsonl`
  files, `assets/Logo.png` and three τ²-bench workflow images. All 26 objects were restored from
  the upstream LFS store and verified against the SHA-256 and size recorded in each pointer.
* `.gitignore` ignored `.github/` (dropping workflow files from commits) and `.vscode/`; both are
  tracked now (only `.vscode/settings.json`). Added `.env.*` (except `.env.example`), key files,
  training artefacts and tool caches.
* `.gitattributes`: files under `docs/` are never stored in LFS, because GitHub Pages cannot serve
  LFS objects.
* `.env.example` documents every credential and endpoint the code reads.

## Safety

* Every GPU launcher in `scripts/` starts with a platform guard: it exits unless the host is Linux
  with `nvidia-smi` (override `QQR_FORCE_RUN=1`). The launchers `pkill -9` sglang / Ray /
  training processes, and four of them ran a blanket `pkill -9 python`, which on a laptop would
  kill unrelated Python programs. Those four now use the targeted pattern the other launchers
  already used.

## Added

* `python -m qqr.demo` – all five tournaments on sample rollouts with a deterministic mock judge.
* `python -m qqr.doctor` – reports what can run on the current machine (credentials are never printed).
* `tests/` – 211 offline tests: tournament behaviour and regressions, numerics against pandas,
  prompt parsers, retry, HTTP clients with `httpx.MockTransport`, RTI gate maths, MCP integration
  against a real stdio MCP subprocess (caching, blocklist, missing credentials, bundled AMap
  server start-up), τ²-bench environments, script guards, JS↔Python parity of the website
  simulator, and headless-browser tests of the website.
* `docs/` – the GitHub Pages site (static, no build step) and `scripts/dev/serve_site.py`.
* `.github/workflows/ci.yml` – tests on Ubuntu and macOS, Python 3.11 and 3.12.

## Secret-scanning remediation (GitHub push protection, GH013)

The first push of this fork was rejected because `data/claw-eval-hard/` (the Claw-Eval-Hard
safety benchmark) contains credential-shaped strings in Stripe, Mailgun, Slack, Twilio, AWS,
GitHub, GitLab, SendGrid, Anthropic, OpenAI-project and Google formats. They are decoy
credentials that the tasks plant in mock config services so that graders can check whether an
agent leaks them. They were judged synthetic because every value is confined to this benchmark's
fixtures, graders, rubrics and task files; several are the vendors' own documented example keys
(AWS, Mailgun, GitHub) and the rest are visibly patterned (sequential digits, `abcdef...`,
`xxxx...`); and the original `rubrics.json` is byte-identical to the public file in the upstream
Alibaba-NLP/qqr repository. No value was tested against a live provider API.

All of them were rewritten in the 64 affected files (fixtures, `grader.py`, `task.yaml`,
`consts.json`, `rubrics.json`, `train.jsonl`, `test.jsonl`) by one prefix-preserving rule set,
for example a Stripe live secret key becomes `FIXTURE-stripe-secret-live-<same suffix>`, a Slack
bot token `FIXTURE-slack-bot-<same suffix>` and an AWS key ID `FIXTURE-AWS-KEY-<same suffix>`. Because each rule only
swaps the vendor prefix, full values, partially masked values and the bare vendor prefixes used by
`secret_not_leaked` checks map consistently.
A check over 152 tasks and 4,482 grader/rubric strings confirmed that every string that occurred in
a task's fixtures before the rewrite still occurs after it, and vice versa.

Behaviour notes: the bare three-letter GitHub-prefix checks previously also matched ordinary words
such as "throughout"; their replacements (`FIXTURE-gh-oauth-`, `FIXTURE-gh-server-`) no longer do. The
value `sk-89e9b2d1...` in the T073 prompt-injection rubric was left unchanged: it must match the
external claw-eval injection payload, and it is not a provider key format. Database URIs with
inline passwords (for example `postgresql://admin:Sup3rS3cr3t!...`) are synthetic and unchanged.
`tests/test_repo_hygiene.py::test_no_provider_format_credentials_in_repo` now guards against
regressions.

## Repository rename

The fork is published as `ViknanS/qtr`, so the website lives at `https://viknans.github.io/qtr/`.
Repository links, the Pages base path (`/qtr/`), the local preview server and the browser tests
were updated. The Python package is still `qqr` (`import qqr`, `python -m qqr.demo`).

## Not verified here

No GPU training, rollout against sglang, LLM-judge call or paid API call was executed while
preparing this fork. Those paths need slime v0.3.1, NVIDIA GPUs and credentials; they were
checked only by compilation, static analysis and the platform guard tests.
