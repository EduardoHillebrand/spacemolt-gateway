"""Tests for the skill registry.

Raw tool proxying was moved to app.core.proxy (dynamic discovery).
This file only tests that register_skills wires up the high-level skills.
"""

from __future__ import annotations

from typing import Any

import pytest
from mcp.server.fastmcp import FastMCP

from app.game_client import GameClient
from app.registry import register_skills
from app.transports.stub import StubTransport


def make_server_and_client() -> tuple[FastMCP, GameClient]:
    client = GameClient(transport=StubTransport(), session_id="sess-test")
    mcp = FastMCP(name="test-server")
    register_skills(mcp, client)
    return mcp, client


async def test_mining_run_is_registered() -> None:
    mcp, _ = make_server_and_client()
    names = {t.name for t in await mcp.list_tools()}
    assert "mining_run" in names


async def test_mining_run_has_description() -> None:
    mcp, _ = make_server_and_client()
    tools = {t.name: t for t in await mcp.list_tools()}
    assert tools["mining_run"].description
