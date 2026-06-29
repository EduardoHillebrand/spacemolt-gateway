"""Unit tests for StreamableHTTPTransport.

On-demand model: each call_tool / list_tools opens its own session.
Tests patch ``streamablehttp_client`` and ``ClientSession`` to inject a fake
session — no real network connection needed.
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager, contextmanager
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.transports.streamable_http import (
    SpaceMoltError,
    StreamableHTTPTransport,
    _parse_content,
    _tool_to_schema,
)
from app.game_client import ParamSchema, ToolSchema


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_text_content(text: str):
    return SimpleNamespace(text=text)


def _make_raw_response(*texts: str):
    """Build a fake MCP call_tool result with text blocks."""
    return SimpleNamespace(content=[_make_text_content(t) for t in texts])


def _make_mcp_tool(name: str, description: str, properties: dict, required: list[str]):
    """Build a fake mcp.types.Tool-like object."""
    return SimpleNamespace(
        name=name,
        description=description,
        inputSchema={
            "type": "object",
            "properties": properties,
            "required": required,
        },
    )


def _make_session(*, call_tool_return: Any = None, list_tools_return: Any = None,
                  call_tool_side_effect: Any = None) -> AsyncMock:
    """Build a fake ClientSession."""
    session = AsyncMock()
    session.initialize = AsyncMock()
    if call_tool_side_effect is not None:
        session.call_tool = AsyncMock(side_effect=call_tool_side_effect)
    elif call_tool_return is not None:
        session.call_tool = AsyncMock(return_value=call_tool_return)
    if list_tools_return is not None:
        session.list_tools = AsyncMock(return_value=list_tools_return)
    return session


@contextmanager
def _patch_open_session(session):
    """Patch _open_session to yield *session* directly."""
    @asynccontextmanager
    async def fake_open_session(self):
        yield session

    with patch.object(StreamableHTTPTransport, "_open_session", fake_open_session):
        yield


def _transport() -> StreamableHTTPTransport:
    return StreamableHTTPTransport("http://fake")


# ---------------------------------------------------------------------------
# Lifecycle — no-ops
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_connect_is_noop():
    t = _transport()
    await t.connect()   # must not raise


@pytest.mark.asyncio
async def test_disconnect_is_noop():
    t = _transport()
    await t.disconnect()   # must not raise


# ---------------------------------------------------------------------------
# _parse_content
# ---------------------------------------------------------------------------

def test_parse_content_json_object():
    raw = _make_raw_response('{"ok": true}')
    assert _parse_content(raw) == {"ok": True}


def test_parse_content_plain_text():
    raw = _make_raw_response("hello world")
    assert _parse_content(raw) == {"result": "hello world"}


def test_parse_content_empty():
    raw = SimpleNamespace(content=[])
    assert _parse_content(raw) == {}


def test_parse_content_raises_spacemolt_error():
    raw = _make_raw_response('{"error": {"code": "NO_FUEL", "message": "out of fuel"}}')
    with pytest.raises(SpaceMoltError) as exc_info:
        _parse_content(raw)
    err = exc_info.value
    assert err.code == "NO_FUEL"
    assert err.message == "out of fuel"
    assert "[NO_FUEL]" in str(err)


def test_parse_content_raises_error_string():
    raw = _make_raw_response('{"error": "something bad"}')
    with pytest.raises(SpaceMoltError) as exc_info:
        _parse_content(raw)
    assert exc_info.value.code == "unknown"


# ---------------------------------------------------------------------------
# _tool_to_schema
# ---------------------------------------------------------------------------

def test_tool_to_schema_converts_correctly():
    tool = _make_mcp_tool(
        name="spacemolt",
        description="The main tool",
        properties={
            "action":     {"type": "string",  "description": "what to do"},
            "quantity":   {"type": "integer", "description": "how many"},
            "session_id": {"type": "string",  "description": "injected"},
        },
        required=["action", "session_id"],
    )
    schema = _tool_to_schema(tool)
    assert schema.name == "spacemolt"
    assert schema.description == "The main tool"
    names = [p.name for p in schema.params]
    assert "session_id" not in names
    assert "action" in names
    assert "quantity" in names


def test_tool_to_schema_required_flag():
    tool = _make_mcp_tool(
        name="x",
        description="",
        properties={
            "action": {"type": "string"},
            "id":     {"type": "string"},
        },
        required=["action"],
    )
    schema = _tool_to_schema(tool)
    by_name = {p.name: p for p in schema.params}
    assert by_name["action"].required is True
    assert by_name["id"].required is False


# ---------------------------------------------------------------------------
# list_tools
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_tools_converts_mcp_schema():
    fake_tool = _make_mcp_tool(
        name="spacemolt",
        description="Main tool",
        properties={
            "action":     {"type": "string", "description": "action verb"},
            "session_id": {"type": "string"},
        },
        required=["action"],
    )
    session = _make_session(list_tools_return=SimpleNamespace(tools=[fake_tool]))

    with _patch_open_session(session):
        schemas = await _transport().list_tools()

    assert len(schemas) == 1
    assert isinstance(schemas[0], ToolSchema)
    param_names = [p.name for p in schemas[0].params]
    assert "session_id" not in param_names
    assert "action" in param_names


# ---------------------------------------------------------------------------
# call_tool — response parsing
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_call_tool_parses_text_content():
    session = _make_session(call_tool_return=_make_raw_response('{"ok": true}'))
    with _patch_open_session(session):
        result = await _transport().call_tool("spacemolt", {"action": "mine"})
    assert result == {"ok": True}


@pytest.mark.asyncio
async def test_call_tool_parses_plain_text():
    session = _make_session(call_tool_return=_make_raw_response("travelling..."))
    with _patch_open_session(session):
        result = await _transport().call_tool("spacemolt", {"action": "travel"})
    assert result == {"result": "travelling..."}


@pytest.mark.asyncio
async def test_call_tool_raises_spacemolt_error():
    raw = _make_raw_response('{"error": {"code": "DOCKED", "message": "already docked"}}')
    session = _make_session(call_tool_return=raw)
    with _patch_open_session(session):
        with pytest.raises(SpaceMoltError) as exc_info:
            await _transport().call_tool("spacemolt", {"action": "dock"})
    assert exc_info.value.code == "DOCKED"


# ---------------------------------------------------------------------------
# Throttle
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_throttle_sleeps_between_calls():
    session = _make_session(call_tool_return=_make_raw_response('{"ok": true}'))
    t = _transport()
    t._last_call_t = time.monotonic()   # simulate a call that just happened

    slept: list[float] = []

    async def fake_sleep(duration: float) -> None:
        slept.append(duration)

    with _patch_open_session(session):
        with patch("app.transports.streamable_http.asyncio.sleep", side_effect=fake_sleep):
            await t.call_tool("spacemolt", {"action": "status"})

    assert len(slept) == 1
    assert slept[0] > 0


# ---------------------------------------------------------------------------
# Retry on 429
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_retry_on_429():
    good = _make_raw_response('{"ok": true}')
    session = _make_session(
        call_tool_side_effect=[Exception("HTTP 429 Too Many Requests"), good]
    )

    slept: list[float] = []

    async def fake_sleep(duration: float) -> None:
        slept.append(duration)

    with _patch_open_session(session):
        with patch("app.transports.streamable_http.asyncio.sleep", side_effect=fake_sleep):
            result = await _transport().call_tool("spacemolt", {"action": "mine"})

    assert result == {"ok": True}
    assert session.call_tool.call_count == 2
    assert any(s == 15 for s in slept)


@pytest.mark.asyncio
async def test_retry_exhausted_reraises():
    session = _make_session(call_tool_side_effect=Exception("429 rate limit"))

    async def fake_sleep(_: float) -> None:
        pass

    with _patch_open_session(session):
        with patch("app.transports.streamable_http.asyncio.sleep", side_effect=fake_sleep):
            with pytest.raises(Exception, match="429"):
                await _transport().call_tool("spacemolt", {})

    # 1 original + 3 retries = 4 attempts
    assert session.call_tool.call_count == 4


# ---------------------------------------------------------------------------
# SpaceMoltError
# ---------------------------------------------------------------------------

def test_spacemolt_error_attributes():
    err = SpaceMoltError("NO_FUEL", "out of fuel")
    assert err.code == "NO_FUEL"
    assert err.message == "out of fuel"
    assert isinstance(err, Exception)
