"""Tests for ToolSchema, ParamSchema and StubTransport.list_tools()."""

from __future__ import annotations

import pytest
from app.game_client import GameClient, ParamSchema, ToolSchema
from app.transports.stub import STUB_TOOLS, StubTransport


class TestSchemaTypes:
    def test_tool_schema_has_name_and_description(self):
        t = ToolSchema(name="mine", description="mines stuff")
        assert t.name == "mine"
        assert t.description == "mines stuff"

    def test_tool_schema_params_default_empty(self):
        t = ToolSchema(name="x", description="y")
        assert t.params == []

    def test_param_schema_required_field(self):
        p = ParamSchema(name="action", type="string", required=True)
        assert p.required is True

    def test_param_schema_optional_field(self):
        p = ParamSchema(name="id", type="string", required=False)
        assert p.required is False


class TestStubTransportListTools:
    async def test_returns_list(self):
        transport = StubTransport()
        tools = await transport.list_tools()
        assert isinstance(tools, list)

    async def test_returns_tool_schema_objects(self):
        transport = StubTransport()
        tools = await transport.list_tools()
        assert all(isinstance(t, ToolSchema) for t in tools)

    async def test_stub_includes_spacemolt_tool(self):
        transport = StubTransport()
        tools = await transport.list_tools()
        names = {t.name for t in tools}
        assert "spacemolt" in names

    async def test_spacemolt_tool_has_action_param(self):
        transport = StubTransport()
        tools = await transport.list_tools()
        spacemolt = next(t for t in tools if t.name == "spacemolt")
        param_names = {p.name for p in spacemolt.params}
        assert "action" in param_names

    async def test_action_param_is_required(self):
        transport = StubTransport()
        tools = await transport.list_tools()
        spacemolt = next(t for t in tools if t.name == "spacemolt")
        action = next(p for p in spacemolt.params if p.name == "action")
        assert action.required is True

    async def test_returns_independent_copy(self):
        transport = StubTransport()
        t1 = await transport.list_tools()
        t2 = await transport.list_tools()
        assert t1 is not t2


class TestGameClientListTools:
    async def test_delegates_to_transport(self):
        transport = StubTransport()
        client = GameClient(transport=transport, session_id="s")
        tools = await client.list_tools()
        assert len(tools) == len(STUB_TOOLS)

    async def test_returns_tool_schemas(self):
        client = GameClient(transport=StubTransport(), session_id="s")
        tools = await client.list_tools()
        assert all(isinstance(t, ToolSchema) for t in tools)
