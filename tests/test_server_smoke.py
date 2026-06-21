"""Smoke tests for the MCP server.

Checks that the server can be imported and that tool registration works,
without actually starting a network listener.
"""

import pytest

from app.server import mcp


async def test_server_has_a_name() -> None:
    assert mcp.name == "spacemolt-gateway"


async def test_server_starts_with_no_tools() -> None:
    tools = await mcp.list_tools()
    assert tools == []


async def test_registered_tool_appears_in_list() -> None:
    @mcp.tool()
    def _dummy_tool() -> str:
        """A temporary tool registered only during this test."""
        return "ok"

    try:
        tools = await mcp.list_tools()
        names = [t.name for t in tools]
        assert "_dummy_tool" in names
    finally:
        # Clean up so this test does not affect others.
        mcp._tool_manager.remove_tool("_dummy_tool")
