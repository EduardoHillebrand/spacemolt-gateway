"""Tool registry -- plugs skills into the MCP server.

Raw tool proxying is now handled dynamically by app.core.proxy.setup_proxy,
which discovers all SpaceMolt tools at startup and registers them automatically.

This file only registers high-level skills.
"""

from mcp.server.fastmcp import FastMCP

from app.game_client import GameClient


def register_skills(mcp: FastMCP, client: GameClient) -> None:
    """Register high-level skill tools on *mcp*.

    Each skill module exposes a register(mcp, client) function.
    Add calls here as new skills are built.
    """
    from app.skills.mining import tool as mining_tool
    mining_tool.register(mcp, client)
