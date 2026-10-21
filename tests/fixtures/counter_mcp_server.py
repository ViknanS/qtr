"""Tiny stdio MCP server used by the integration tests.

``add`` returns the sum plus a per-process call counter, so the tests can tell
whether a result came from qqr's tool cache or from a real server call.
"""

import os

try:
    from mcp.server.fastmcp import FastMCP  # mcp < 2
except ImportError:  # mcp >= 2
    from mcp.server.mcpserver import MCPServer as FastMCP

mcp = FastMCP("Counter")
_calls = {"n": 0}


@mcp.tool()
def add(a: int, b: int) -> str:
    """Add two integers."""
    _calls["n"] += 1
    return f"{a + b}|call={_calls['n']}"


@mcp.tool()
def env_flag(name: str) -> str:
    """Report whether an environment variable is present in the server process."""
    return "set" if name in os.environ else "unset"


if __name__ == "__main__":
    mcp.run(transport="stdio")
