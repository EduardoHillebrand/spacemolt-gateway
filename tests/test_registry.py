"""Tests for the raw proxy tool registry."""

from typing import Any

import pytest
from mcp.server.fastmcp import FastMCP

from app.game_client import GameClient
from app.registry import register_raw_tools


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class FakeTransport:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self._response: Any = "ok"

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        self.calls.append((tool_name, arguments))
        return self._response


def make_server_and_client() -> tuple[FastMCP, GameClient, FakeTransport]:
    transport = FakeTransport()
    client = GameClient(transport=transport, session_id="sess-test")
    mcp = FastMCP(name="test-server")
    register_raw_tools(mcp, client)
    return mcp, client, transport


# ---------------------------------------------------------------------------
# Registration tests
# ---------------------------------------------------------------------------


async def test_raw_tools_are_registered() -> None:
    mcp, _, _ = make_server_and_client()
    names = {t.name for t in await mcp.list_tools()}
    assert {"get_status", "mine", "travel"} <= names


async def test_tool_descriptions_contain_low_level_notice() -> None:
    mcp, _, _ = make_server_and_client()
    tools = {t.name: t for t in await mcp.list_tools()}
    for name in ("get_status", "mine", "travel"):
        assert "LOW LEVEL" in (tools[name].description or ""), (
            f"Tool '{name}' is missing the LOW LEVEL notice"
        )


# ---------------------------------------------------------------------------
# Forwarding tests
# ---------------------------------------------------------------------------


async def test_get_status_calls_spacemolt_with_correct_action() -> None:
    mcp, _, transport = make_server_and_client()

    await mcp.call_tool("get_status", {})

    assert len(transport.calls) == 1
    tool_name, args = transport.calls[0]
    assert tool_name == "spacemolt"
    assert args["action"] == "get_status"


async def test_mine_calls_spacemolt_with_correct_action() -> None:
    mcp, _, transport = make_server_and_client()

    await mcp.call_tool("mine", {})

    tool_name, args = transport.calls[0]
    assert tool_name == "spacemolt"
    assert args["action"] == "mine"


async def test_travel_forwards_poi_id() -> None:
    mcp, _, transport = make_server_and_client()

    await mcp.call_tool("travel", {"poi_id": "asteroid-belt-7"})

    tool_name, args = transport.calls[0]
    assert tool_name == "spacemolt"
    assert args["action"] == "travel"
    assert args["id"] == "asteroid-belt-7"


async def test_session_id_is_injected_in_every_call() -> None:
    transport = FakeTransport()
    client = GameClient(transport=transport, session_id="real-session")
    mcp = FastMCP(name="test-server")
    register_raw_tools(mcp, client)

    for tool in ("get_status", "mine"):
        await mcp.call_tool(tool, {})

    for _, args in transport.calls:
        assert args["session_id"] == "real-session"
