"""LLM clients, retry helper and RTI utilities - all with mocked HTTP."""

import asyncio
import json
from types import SimpleNamespace

import httpx
import pytest

from qqr.off_policy.rti.client import LLMConfig, OpenAIChatClient
from qqr.off_policy.rti.utils import metrics
from qqr.schemas import LLM
from qqr.utils import retry


# --------------------------------------------------------------------- retry
def test_retry_sync_until_success():
    calls = {"n": 0}

    @retry(stop_after_attempt=3, wait_fixed=0)
    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("boom")
        return "ok"

    assert flaky() == "ok"
    assert calls["n"] == 3


async def test_retry_async_returns_fallback():
    @retry(stop_after_attempt=2, wait_fixed=0, return_on_failure=(5.0, 5.0))
    async def always_fails():
        raise ValueError("nope")

    assert await always_fails() == (5.0, 5.0)


def test_retry_if_result():
    seq = iter([None, None, 7])

    @retry(stop_after_attempt=5, wait_fixed=0, retry_if_result=lambda r: r is None)
    def f():
        return next(seq)

    assert f() == 7


# ---------------------------------------------------------- schemas.LLM (httpx)
async def test_schema_llm_posts_openai_payload():
    seen = {}

    def handler(request: httpx.Request):
        seen["auth"] = request.headers["Authorization"]
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": "hi"}}]})

    llm = LLM(model="m", api_key="k", base_url="http://llm.test/v1")
    llm.client = httpx.AsyncClient(base_url="http://llm.test/v1", transport=httpx.MockTransport(handler), headers=llm.client.headers)
    out = await llm(messages=[{"role": "user", "content": "x"}], temperature=0)
    assert out["choices"][0]["message"]["content"] == "hi"
    assert seen["auth"] == "Bearer k"
    assert seen["body"] == {"model": "m", "messages": [{"role": "user", "content": "x"}], "temperature": 0}


# -------------------------------------------------------- qqr.llms.OpenAI
async def test_openai_wrapper_respects_concurrency_limit():
    from qqr.llms import OpenAI

    client = OpenAI(model="judge", api_key="test-key", base_url="http://unused.test/v1", concurrency_limit=2)
    active = {"now": 0, "peak": 0}

    async def fake_create(**kwargs):
        active["now"] += 1
        active["peak"] = max(active["peak"], active["now"])
        await asyncio.sleep(0.01)
        active["now"] -= 1
        return SimpleNamespace(model=kwargs["model"], n=len(kwargs["messages"]))

    client.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=fake_create)))
    results = await asyncio.gather(*[client(messages=[{"role": "user", "content": str(i)}]) for i in range(6)])
    assert all(r.model == "judge" for r in results)
    assert active["peak"] == 2


# ----------------------------------------------------------- RTI chat client
def _client(handler, **cfg):
    c = OpenAIChatClient(LLMConfig(base_url="http://rti.test/v1", api_key="k", model="policy", retry_base_backoff=0, retry_max_backoff=0, **cfg))
    c._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return c


def _completion(content, logprobs=True):
    choice = {"message": {"role": "assistant", "content": content}}
    if logprobs:
        choice["logprobs"] = {"content": [{"token": "a", "logprob": -0.1}, {"token": "b", "logprob": -0.2}]}
    else:
        choice["logprobs"] = None
    return {"choices": [choice]}


async def test_rti_client_returns_message_with_token_logprobs():
    c = _client(lambda r: httpx.Response(200, json=_completion("<think>why</think>\nanswer")))
    msg = await c.chat([{"role": "user", "content": "q"}], return_message=True)
    assert msg["content"] == "answer"
    assert msg["reasoning"] == "<think>why"
    assert msg["token_logprobs"] == [-0.1, -0.2]


async def test_rti_client_tolerates_missing_logprobs():
    """Regression: servers that omit logprobs used to raise inside the retry
    loop and exhaust every retry (with exponential backoff) before giving up."""
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return httpx.Response(200, json=_completion("fine", logprobs=False))

    c = _client(handler, max_retries=5)
    assert await c.chat([{"role": "user", "content": "q"}]) == "fine"
    assert calls["n"] == 1


async def test_rti_client_retries_transient_errors():
    statuses = iter([503, 429, 200])

    def handler(request):
        s = next(statuses)
        return httpx.Response(s, json=_completion("ok")) if s == 200 else httpx.Response(s)

    c = _client(handler, max_retries=5)
    assert await c.chat([{"role": "user", "content": "q"}]) == "ok"


async def test_rti_client_fails_fast_on_client_error(caplog):
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return httpx.Response(401, json={"error": "bad key"})

    c = _client(handler, max_retries=5)
    assert await c.chat([{"role": "user", "content": "q"}], return_message=True) == {}
    assert calls["n"] == 1
    assert "giving up" in caplog.text


async def test_rti_client_unconfigured_returns_empty():
    c = OpenAIChatClient(LLMConfig(base_url="", api_key="", model=""))
    assert await c.chat([]) == ""


# ------------------------------------------------------------ RTI PPL / KL gate
def test_ppl_and_divergences():
    assert metrics._ppl([]) == float("inf")
    assert metrics._ppl([0.0, 0.0]) == pytest.approx(1.0)
    assert metrics._ppl([-1.0, -1.0, None]) == pytest.approx(2.718281828, rel=1e-6)
    p = metrics._softmax_from_logps([-1.0, -2.0, -3.0])
    assert p.sum() == pytest.approx(1.0)
    assert metrics._kl(p, p) == pytest.approx(0.0, abs=1e-9)
    q = metrics._softmax_from_logps([-3.0, -2.0, -1.0])
    assert metrics._js(p, q) == pytest.approx(metrics._js(q, p))
    assert metrics._kl(p, q) > 0


async def test_ref_kl_gate_disabled_short_circuits():
    ok, info = await metrics.ref_kl_gate(
        args=SimpleNamespace(enable_ref_kl_gate=False),
        sample_messages=[],
        original_response="a",
        corrected_response="b",
    )
    assert ok and info["reason"] == "disabled"


async def test_ref_kl_gate_with_stub_scorer(monkeypatch):
    class StubScorer:
        def __init__(self, args, **kw):
            pass

        async def score_completion_async(self, messages, response, tools=None):
            # corrected response is much less likely under the reference policy
            return {"token_logprobs": [-0.1] * 4 if response == "raw" else [-4.0] * 4}

    monkeypatch.setattr(metrics, "_ref_scorer_cls", lambda: StubScorer)
    args = SimpleNamespace(enable_ref_kl_gate=True, ref_judge_method="ppl", ref_ppl_threshold=5.0)
    ok, info = await metrics.ref_kl_gate(args=args, sample_messages=[], original_response="raw", corrected_response="corr")
    assert not ok  # exp(4) ~ 54.6 > 5
    assert info["values"]["corr_ppl"] == pytest.approx(54.598, rel=1e-3)
