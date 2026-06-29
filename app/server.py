"""SpaceMolt Gateway -- MCP server entry point.

No game logic lives here. Only wiring and startup.

Startup sequence (inside lifespan):
  1. init_dev_logging   -- WebSocket log channel on port 7788
  2. register_skills    -- registers skills immediately (fast, no IO)
  3. background task    -- connects transport + registers proxy tools
  4. (yield)            -- server is ready; accepts MCP requests right away
  5. shutdown           -- disconnect transport
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager, suppress
from typing import AsyncIterator

from mcp.server.fastmcp import FastMCP

from app.core.devlog.setup import init_dev_logging
from app.core.proxy import setup_proxy
from app.game_client import GameClient
from app.registry import register_skills
from app.transports.stub import StubTransport

_DEV_LOG_PORT = int(os.environ.get("DEVLOG_PORT", "7788"))

# Module-level mcp instance (imported by tests for smoke checks).
mcp = FastMCP(name="spacemolt-gateway")

# Set by main() before mcp.run() so the lifespan closure can access it.
_client: GameClient | None = None

log = logging.getLogger(__name__)


async def _connect_and_proxy(client: GameClient) -> None:
    """Background task: connect transport then register proxy tools.

    Runs after the server is already accepting requests, so the MCP
    client sees skills immediately and proxy tools appear a few seconds later.
    """
    try:
        await client.connect()
        await setup_proxy(mcp, client)
        log.info("_connect_and_proxy: proxy tools registered")
    except Exception as exc:
        log.error("_connect_and_proxy: failed: %s", exc)


@asynccontextmanager
async def lifespan(server: FastMCP) -> AsyncIterator[None]:
    """Async startup: devlog -> skills (sync) -> transport connect (background)."""
    await init_dev_logging(port=_DEV_LOG_PORT)
    task: asyncio.Task | None = None
    if _client is not None:
        # Skills register immediately — no IO, server is ready at once.
        register_skills(mcp, _client)
        # Transport connect runs in background so inspector doesn't time out.
        task = asyncio.create_task(_connect_and_proxy(_client))
    yield
    # Shutdown: cancel background task if still running, then disconnect.
    if task is not None and not task.done():
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
    if _client is not None:
        await _client.disconnect()


# Attach lifespan after defining it (FastMCP supports post-init assignment).
mcp.settings.lifespan = lifespan


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


def main() -> None:
    """Build the client and run the gateway over stdio."""
    global _client
    _client = build_client()
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
