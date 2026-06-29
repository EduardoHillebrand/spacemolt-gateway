"""SpaceMolt Gateway -- MCP server entry point.

No game logic lives here. Only wiring and startup.

Startup sequence (inside main_async, single event loop):
  1. init_dev_logging   -- WebSocket log channel on port 7788
  2. register_skills    -- high-level skills registered before server starts
  3. client.connect()   -- opens transport (no-op for StubTransport)
  4. setup_proxy        -- discovers SpaceMolt tools and registers proxies
  5. run_stdio_async()  -- server starts; all tools already visible to clients
  6. (on shutdown)      -- client.disconnect()

All tool registration happens before run_stdio_async() so FastMCP exposes
them immediately on the first list_tools() request.
"""

import asyncio
import logging
import os

from mcp.server.fastmcp import FastMCP

from app.core.devlog.setup import init_dev_logging
from app.core.proxy import setup_proxy
from app.game_client import GameClient
from app.registry import register_skills
from app.transports.stub import StubTransport

_DEV_LOG_PORT = int(os.environ.get("DEVLOG_PORT", "7788"))

# Module-level mcp instance (imported by tests for smoke checks).
mcp = FastMCP(name="spacemolt-gateway")

log = logging.getLogger(__name__)


def build_client() -> GameClient:
    """Build a GameClient from environment variables.

    SPACEMOLT_URL:        if set, use the real StreamableHTTPTransport.
    SPACEMOLT_SESSION_ID: session from spacemolt_auth (required for live use).
                          Falls back to stub-session for local testing.
    """
    session_id = os.environ.get("SPACEMOLT_SESSION_ID", "stub-session")
    url = os.environ.get("SPACEMOLT_URL")
    if url:
        from app.transports.streamable_http import StreamableHTTPTransport
        transport: object = StreamableHTTPTransport(url)
    else:
        transport = StubTransport()
    return GameClient(transport=transport, session_id=session_id)  # type: ignore[arg-type]


async def main_async() -> None:
    """Full startup in one event loop: setup -> server -> cleanup."""
    client = build_client()

    await init_dev_logging(port=_DEV_LOG_PORT)

    # Skills registered immediately — no IO needed.
    register_skills(mcp, client)

    # Transport connect + proxy discovery before server starts.
    # Tools must be registered before run_stdio_async() to be visible.
    try:
        await client.connect()
        await setup_proxy(mcp, client)
    except Exception as exc:
        log.error("startup: transport connect/proxy failed: %s", exc)

    # Server runs here until shutdown (Ctrl-C or client disconnect).
    try:
        await mcp.run_stdio_async()
    finally:
        await client.disconnect()


def main() -> None:
    """Entry point: run the gateway event loop."""
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
