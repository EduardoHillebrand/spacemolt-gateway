"""SpaceMolt Gateway -- MCP server entry point.

No game logic lives here. Only wiring and startup.

Startup sequence (inside lifespan):
  1. init_dev_logging  -- WebSocket log channel on port 7788
  2. client.connect()  -- opens transport session (no-op for StubTransport)
  3. setup_proxy       -- discovers SpaceMolt tools and registers proxies
  4. register_skills   -- registers high-level skills (mining_run, ...)
  5. (yield)
  6. client.disconnect() -- closes transport session cleanly
"""

import logging
import os
from contextlib import asynccontextmanager
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


@asynccontextmanager
async def lifespan(server: FastMCP) -> AsyncIterator[None]:
    """Async startup: devlog -> transport connect -> proxy discovery -> skills."""
    await init_dev_logging(port=_DEV_LOG_PORT)
    if _client is not None:
        try:
            await _client.connect()
            await setup_proxy(mcp, _client)
        except Exception as exc:
            log.error("lifespan: transport connect/proxy failed: %s", exc)
        # Skills are always registered, even without a live transport.
        register_skills(mcp, _client)
    yield
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
