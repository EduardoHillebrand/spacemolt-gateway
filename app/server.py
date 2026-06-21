"""SpaceMolt Gateway -- MCP server entry point.

No game logic lives here. Only wiring and startup.
"""

import os

from mcp.server.fastmcp import FastMCP

from app.game_client import GameClient
from app.registry import register_raw_tools, register_skills
from app.transports.stub import StubTransport

mcp = FastMCP(name="spacemolt-gateway")


def build_client() -> GameClient:
    """Build a GameClient from environment variables.

    SPACEMOLT_SESSION_ID: session from spacemolt_auth (required for live use).
    Falls back to stub-session for local inspection.
    """
    session_id = os.environ.get("SPACEMOLT_SESSION_ID", "stub-session")
    transport = StubTransport()
    return GameClient(transport=transport, session_id=session_id)


def register_all(client: GameClient) -> None:
    """Register all raw proxy tools and skills on the global mcp instance."""
    register_raw_tools(mcp, client)
    register_skills(mcp, client)


def main() -> None:
    """Build the client, register tools, and run the gateway over stdio."""
    client = build_client()
    register_all(client)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
