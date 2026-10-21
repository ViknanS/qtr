"""MCP integration: qqr's cacheable stdio server wrapper against a real
subprocess MCP server (no network, no API keys)."""

import os
import pathlib
import sys

import pytest

from qqr.mcp import MCPServerStdioCacheable, MCPServerStdioParams
from qqr.mcp.utils import get_mcp_tools

pytestmark = pytest.mark.integration

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "counter_mcp_server.py"
ROOT = pathlib.Path(__file__).resolve().parents[1]


def _text(result) -> str:
    return result.content[0].text


def _server(**kw):
    env = {"PYTHONPATH": str(ROOT), "PATH": os.environ.get("PATH", "")}
    env.update(kw.pop("env", {}))
    params = MCPServerStdioParams(command=sys.executable, args=[str(FIXTURE)], env=env)
    return MCPServerStdioCacheable(
        name="Counter", params=params, cache_tools_list=True, client_session_timeout_seconds=30, **kw
    )


async def test_tools_are_listed_and_converted_to_openai_schema():
    server = _server()
    await server.connect()
    try:
        tools = await get_mcp_tools(server)
    finally:
        await server.cleanup()
    by_name = {t["function"]["name"]: t for t in tools}
    assert set(by_name) == {"add", "env_flag"}
    params = by_name["add"]["function"]["parameters"]
    assert by_name["add"]["type"] == "function"
    assert set(params["properties"]) == {"a", "b"}


async def test_results_are_cached_per_arguments():
    server = _server()
    await server.connect()
    try:
        first = _text(await server.call_tool("add", {"a": 1, "b": 2}))
        again = _text(await server.call_tool("add", {"b": 2, "a": 1}))  # key order irrelevant
        other = _text(await server.call_tool("add", {"a": 5, "b": 5}))
    finally:
        await server.cleanup()
    assert first == "3|call=1"
    assert again == first  # served from cache: the server counter did not move
    assert other == "10|call=2"


async def test_blocklisted_tools_bypass_the_cache():
    server = _server(blocklist=["add"])  # configs pass lists
    await server.connect()
    try:
        a = _text(await server.call_tool("add", {"a": 1, "b": 1}))
        b = _text(await server.call_tool("add", {"a": 1, "b": 1}))
    finally:
        await server.cleanup()
    assert (a, b) == ("2|call=1", "2|call=2")


async def test_unset_credentials_are_dropped_not_crashing(caplog):
    """Configs build ``env`` from os.getenv(); a missing key is ``None``.
    The server must still start, and the missing variable is named in a warning."""
    server = _server(env={"QQR_TEST_MISSING_KEY": None, "QQR_TEST_PRESENT": "1"})
    assert "QQR_TEST_MISSING_KEY" in caplog.text
    await server.connect()
    try:
        assert _text(await server.call_tool("env_flag", {"name": "QQR_TEST_PRESENT"})) == "set"
        assert _text(await server.call_tool("env_flag", {"name": "QQR_TEST_MISSING_KEY"})) == "unset"
    finally:
        await server.cleanup()


def test_cache_key_handles_non_json_arguments():
    import datetime

    server = _server()
    key = server._make_cache_key("t", {"when": datetime.date(2026, 1, 1), "n": 1})
    assert key == 't:{"n": 1, "when": "2026-01-01"}'
    long_key = server._make_cache_key("t", {"x": "y" * 5000})
    assert len(long_key) == 32  # md5 for oversized keys


async def test_bundled_amap_server_starts_and_lists_tools():
    """Smoke test of a shipped MCP tool server (no API call is made)."""
    pytest.importorskip("click")
    params = MCPServerStdioParams(
        command=sys.executable,
        args=["-m", "qqr.tools.amap"],
        env={"PYTHONPATH": str(ROOT), "PATH": os.environ.get("PATH", ""), "AMAP_MAPS_API_KEY": "test-placeholder"},
    )
    server = MCPServerStdioCacheable(name="AMap", params=params, client_session_timeout_seconds=60)
    await server.connect()
    try:
        names = {t["function"]["name"] for t in await get_mcp_tools(server)}
    finally:
        await server.cleanup()
    assert "poi_search" in names
