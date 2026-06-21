"""Tests for app/core/proxy.py — setup_proxy and _make_proxy."""

from __future__ import annotations

from typing import Any

import pytest
from mcp.server.fastmcp import FastMCP

from app.core.proxy import _make_proxy, setup_proxy
from app.game_client import GameClient, ParamSchema, ToolSchema
from app.transports.stub import STUB_TOOLS, StubTransport


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class RecordingTransport:
    """Transport that records calls and returns a fixed response."""

    def __init__(self, tools: list[ToolSchema] | None = None) -> None:
        self.calls: list[tuple[str, dict]] = []
        self._tools = tools or list(STUB_TOOLS)

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> str:
        self.calls.append((tool_name, arguments))
        return f"ok:{tool_name}"

    async def list_tools(self) -> list[ToolSchema]:
        return list(self._tools)


class FailingTransport:
    """Transport whose list_tools() always raises."""

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> str:
        return "ok"

    async def list_tools(self) -> list[ToolSchema]:
        raise RuntimeError("connection refused")


def make_mcp() -> FastMCP:
    return FastMCP(name="test-proxy")


# ---------------------------------------------------------------------------
# _make_proxy unit tests
# ---------------------------------------------------------------------------

class TestMakeProxy:
    def _simple_tool(self) -> ToolSchema:
        return ToolSchema(
            name="spacemolt",
            description="test tool",
            params=[
                ParamSchema("action", "string", True),
                ParamSchema("id",     "string", False),
            ],
        )

    def test_proxy_has_correct_name(self):
        transport = RecordingTransport()
        client = GameClient(transport=transport, session_id="s")
        fn = _make_proxy(client, self._simple_tool())
        assert fn.__name__ == "spacemolt"

    async def test_proxy_calls_client(self):
        transport = RecordingTransport()
        client = GameClient(transport=transport, session_id="s")
        fn = _make_proxy(client, self._simple_tool())
        await fn(action="mine")
        assert len(transport.calls) == 1
        assert transport.calls[0][0] == "spacemolt"

    async def test_proxy_injects_session_id(self):
        transport = RecordingTransport()
        client = GameClient(transport=transport, session_id="real-session")
        fn = _make_proxy(client, self._simple_tool())
        await fn(action="mine")
        _, args = transport.calls[0]
        assert args["session_id"] == "real-session"

    async def test_proxy_forwards_required_param(self):
        transport = RecordingTransport()
        client = GameClient(transport=transport, session_id="s")
        fn = _make_proxy(client, self._simple_tool())
        await fn(action="travel")
        _, args = transport.calls[0]
        assert args["action"] == "travel"

    async def test_proxy_returns_string(self):
        transport = RecordingTransport()
        client = GameClient(transport=transport, session_id="s")
        fn = _make_proxy(client, self._simple_tool())
        result = await fn(action="mine")
        assert isinstance(result, str)

    def test_required_param_in_schema(self):
        import inspect
        transport = RecordingTransport()
        client = GameClient(transport=transport, session_id="s")
        fn = _make_proxy(client, self._simple_tool())
        sig = inspect.signature(fn)
        assert sig.parameters["action"].default is inspect.Parameter.empty

    def test_optional_param_has_default(self):
        import inspect
        transport = RecordingTransport()
        client = GameClient(transport=transport, session_id="s")
        fn = _make_proxy(client, self._simple_tool())
        sig = inspect.signature(fn)
        assert sig.parameters["id"].default == ""


# ---------------------------------------------------------------------------
# setup_proxy integration tests
# ---------------------------------------------------------------------------

class TestSetupProxy:
    async def test_registers_stub_tools(self):
        transport = RecordingTransport()
        client = GameClient(transport=transport, session_id="s")
        mcp = make_mcp()
        await setup_proxy(mcp, client)
        names = {t.name for t in await mcp.list_tools()}
        assert "spacemolt" in names
        assert "spacemolt_auth" in names

    async def test_all_stub_tools_registered(self):
        transport = RecordingTransport()
        client = GameClient(transport=transport, session_id="s")
        mcp = make_mcp()
        await setup_proxy(mcp, client)
        names = {t.name for t in await mcp.list_tools()}
        expected = {t.name for t in STUB_TOOLS}
        assert expected <= names

    async def test_proxy_callable_after_registration(self):
        transport = RecordingTransport()
        client = GameClient(transport=transport, session_id="s")
        mcp = make_mcp()
        await setup_proxy(mcp, client)
        await mcp.call_tool("spacemolt", {"action": "mine"})
        assert any(t == "spacemolt" for t, _ in transport.calls)

    async def test_fallback_on_list_tools_failure(self):
        """setup_proxy must not raise if list_tools() fails."""
        client = GameClient(transport=FailingTransport(), session_id="s")
        mcp = make_mcp()
        await setup_proxy(mcp, client)          # should not raise
        tools = await mcp.list_tools()
        assert tools == []                      # nothing registered

    async def test_session_id_injected_via_mcp_call(self):
        transport = RecordingTransport()
        client = GameClient(transport=transport, session_id="sess-xyz")
        mcp = make_mcp()
        await setup_proxy(mcp, client)
        await mcp.call_tool("spacemolt", {"action": "get_status"})
        _, args = transport.calls[0]
        assert args["session_id"] == "sess-xyz"
