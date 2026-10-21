"""The website simulator (docs/assets/js/arena.js) must implement the same
ranking rules as the Python reward models. Requires Node.js; skipped otherwise."""

import json
import pathlib
import random
import shutil
import subprocess

import pytest
from conftest import QualityJudge, make_group

from qqr.reward_models import get_reward_model

ROOT = pathlib.Path(__file__).resolve().parents[1]
ARENA_JS = ROOT / "docs" / "assets" / "js" / "arena.js"
NODE = shutil.which("node")

pytestmark = pytest.mark.skipif(NODE is None, reason="Node.js not installed")

GROUPS = [random.Random(s).choices(range(1, 12), k=n) for s, n in enumerate([2, 3, 4, 5, 6, 7, 8, 8, 9, 12, 16, 16])]

NODE_SCRIPT = """
const Arena = require(process.argv[1]);
const groups = JSON.parse(process.argv[2]);
const out = {};
for (const m of Arena.METHODS) {
  out[m] = groups.map((q, k) => {
    const r = Arena.run(m, q, { seed: k, noise: 0 });
    return { rewards: r.rewards, calls: r.calls, order: r.order || null };
  });
}
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def js_results():
    res = subprocess.run(
        [NODE, "-e", NODE_SCRIPT, str(ARENA_JS), json.dumps(GROUPS)],
        capture_output=True, text=True, check=True,
    )
    return json.loads(res.stdout)


async def _python(method, qualities):
    judge = QualityJudge()
    rewards = await get_reward_model(method)(judge)(predictions=make_group(qualities), query="q")
    return rewards, len(judge.calls)


@pytest.mark.parametrize("method", ["anchor", "round_robin", "single_elimination"])
async def test_deterministic_methods_match_python(method, js_results):
    for k, q in enumerate(GROUPS):
        py_rewards, py_calls = await _python(method, q)
        js = js_results[method][k]
        assert js["calls"] == py_calls, (method, q)
        assert js["rewards"] == pytest.approx(py_rewards, abs=1e-5), (method, q)


@pytest.mark.parametrize("method", ["swiss", "double_elimination"])
async def test_randomised_methods_share_invariants(method, js_results):
    for k, q in enumerate(GROUPS):
        js = js_results[method][k]
        py_rewards, py_calls = await _python(method, q)
        n = len(q)
        # same number of judge calls for swiss; double-elim depends on byes
        if method == "swiss":
            assert js["calls"] == py_calls
        else:
            assert 2 * n - 3 <= js["calls"] <= 2 * n - 1
        # normalised group advantages
        assert sum(js["rewards"]) == pytest.approx(0.0, abs=1e-5)
        # a strictly best rollout is always ranked first
        if q.count(max(q)) == 1:
            best = q.index(max(q))
            assert js["rewards"][best] == pytest.approx(max(js["rewards"]))
            assert py_rewards[best] == pytest.approx(max(py_rewards))
