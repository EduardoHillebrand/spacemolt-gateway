"""SpaceMolt Gateway -- MCP server entry point.

No game logic lives here. Only wiring and startup.

Startup sequence (inside main_async, single event loop):
  1. init_dev_logging   -- WebSocket log channel on port 7788
  2. register_skills    -- high-level skills registered before server starts
  3. client.connect()   -- opens transport (no-op for StubTransport)
  4. setup_proxy        -- discovers SpaceMolt tools and registers proxies
  5. run_stdio_async()  -- server starts; all tools already visible to clients
     OR run_streamable_http_async() when --http flag is used
  6. (on shutdown)      -- client.disconnect()

All tool registration happens before the server starts so FastMCP exposes
tools immediately on the first list_tools() request.

Usage:
  stdio (Claude Desktop config):
    python -m app.server

  HTTP (register by URL like SpaceMolt):
    python -m app.server --http --port 8080
    # then register http://localhost:8080/mcp in Claude Desktop / Cowork
"""

import argparse
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
_DEFAULT_HTTP_PORT = 8080

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


async def main_async(http: bool = False, port: int = _DEFAULT_HTTP_PORT) -> None:
    """Full startup in one event loop: setup -> server -> cleanup."""
    client = build_client()

    await init_dev_logging(port=_DEV_LOG_PORT)

    # Skills registered immediately — no IO needed.
    register_skills(mcp, client)

    # Transport connect + proxy discovery before server starts.
    # Tools must be registered before the server runs to be visible.
    try:
        await client.connect()
        await setup_proxy(mcp, client)
    except Exception as exc:
        log.error("startup: transport connect/proxy failed: %s", exc)

    # Server runs here until shutdown (Ctrl-C or client disconnect).
    try:
        if http:
            log.info("gateway: starting HTTP server on port %d", port)
            log.info("gateway: register URL http://localhost:%d/mcp", port)
            await mcp.run_streamable_http_async(host="localhost", port=port)
        else:
            await mcp.run_stdio_async()
    finally:
        await client.disconnect()


def main() -> None:
    """Entry point: parse args and run the gateway event loop."""
    parser = argparse.ArgumentParser(description="SpaceMolt Gateway MCP server")
    parser.add_argument(
        "--http",
        action="store_true",
        help="Run as HTTP server instead of stdio (for URL-based registration)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=_DEFAULT_HTTP_PORT,
        help=f"HTTP port (default: {_DEFAULT_HTTP_PORT}, only used with --http)",
    )
    args = parser.parse_args()
    asyncio.run(main_async(http=args.http, port=args.port))


if __name__ == "__main__":
    main()
