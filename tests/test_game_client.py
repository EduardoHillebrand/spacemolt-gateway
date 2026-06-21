"""Tests for GameClient.

Uses FakeTransport — no real SpaceMolt connection needed.
"""

from typing import Any

import pytest

from app.game_client import GameClient


class FakeTransport:
    """Records every call_tool invocation and returns a preset response."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self._response: Any = {}

    def set_response(self, response: Any) -> None:
        self._response = response

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        self.calls.append((tool_name, arguments))
        return self._response


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_client(session_id: str = "sess-test") -> tuple[GameClient, FakeTransport]:
    transport = FakeTransport()
    return GameClient(transport=transport, session_id=session_id), transport


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_call_forwards_tool_name() -> None:
    client, transport = make_client()

    await client.call("mine")

    tool_name, _ = transport.calls[0]
    assert tool_name == "mine"


async def test_call_injects_session_id() -> None:
    client, transport = make_client(session_id="my-session")

    await client.call("get_state")

    _, args = transport.calls[0]
    assert args["session_id"] == "my-session"


async def test_call_passes_extra_args() -> None:
    client, transport = make_client()

    await client.call("travel", destination="Sol")

    _, args = transport.calls[0]
    assert args["destination"] == "Sol"


async def test_call_returns_transport_response() -> None:
    client, transport = make_client()
    transport.set_response({"status": "ok", "ore": 10})

    result = await client.call("mine")

    assert result == {"status": "ok", "ore": 10}


async def test_session_id_does_not_override_explicit_arg() -> None:
    """session_id from the client must not be silently dropped if caller
    also passes session_id — the client's value should win (leftmost)."""
    client, transport = make_client(session_id="real-session")

    await client.call("mine", session_id="wrong-session")

    _, args = transport.calls[0]
    assert args["session_id"] == "real-session"
