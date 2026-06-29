"""Real MCP transport via streamablehttp_client + ClientSession.

On-demand connection model: instead of keeping a persistent GET SSE stream
open (which the SpaceMolt server closes quickly, causing rapid reconnect
loops), each call_tool / list_tools opens a fresh ClientSession, does the
work, and closes it immediately.  No idle stream → no reconnect noise.

Throttle (300 ms min gap) and retry on 429 (15 / 30 / 60 s backoff) are
preserved as instance-level state so they still work across calls.

Usage::

    transport = StreamableHTTPTransport("https://game.spacemolt.com/mcp")
    await transport.connect()    # no-op
    result = await transport.call_tool("spacemolt", {"action": "mine", ...})
    tools  = await transport.list_tools()
    await transport.disconnect() # no-op
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from contextlib import AsyncExitStack, asynccontextmanager
from typing import Any, AsyncIterator

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from app.game_client import ParamSchema, ToolSchema

log = logging.getLogger(__name__)

_MIN_CALL_GAP_S: float = 0.30          # throttle: minimum seconds between calls
_RETRY_WAITS: tuple[int, ...] = (15, 30, 60)  # backoff on 429


class SpaceMoltError(Exception):
    """Semantic error returned by the game (code + message).

    Raised when the tool response contains ``{"error": {"code": …, "message": …}}``.
    """

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


class StreamableHTTPTransport:
    """MCPTransport that connects to SpaceMolt via on-demand streamable HTTP.

    A fresh MCP session is opened for every call_tool / list_tools call and
    closed immediately afterwards.  This avoids the idle GET SSE reconnect
    loop that occurs when a persistent session is kept open.
    """

    def __init__(self, url: str) -> None:
        self._url = url
        self._last_call_t: float = 0.0

    # ------------------------------------------------------------------
    # Lifecycle (no-ops: on-demand model needs no persistent connection)
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """No-op: sessions are opened per-call, not at startup."""
        log.debug("StreamableHTTPTransport: on-demand mode, no persistent connection")

    async def disconnect(self) -> None:
        """No-op: no persistent session to close."""

    # ------------------------------------------------------------------
    # Internal: open a fresh session for one operation
    # ------------------------------------------------------------------

    @asynccontextmanager
    async def _open_session(self) -> AsyncIterator[ClientSession]:
        """Open a fresh MCP session, yield it, then close on exit."""
        async with AsyncExitStack() as stack:
            transport = await stack.enter_async_context(
                streamablehttp_client(self._url)
            )
            read_stream, write_stream, _ = transport
            session = await stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )
            await session.initialize()
            yield session

    # ------------------------------------------------------------------
    # MCPTransport protocol
    # ------------------------------------------------------------------

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """Call a tool on a fresh session, throttle, and retry on 429."""
        # Throttle: ensure minimum gap between consecutive calls
        now = time.monotonic()
        gap = now - self._last_call_t
        if gap < _MIN_CALL_GAP_S:
            await asyncio.sleep(_MIN_CALL_GAP_S - gap)

        async with self._open_session() as session:
            for attempt in range(len(_RETRY_WAITS) + 1):
                try:
                    raw = await session.call_tool(tool_name, arguments)
                    self._last_call_t = time.monotonic()
                    break
                except Exception as exc:
                    s = str(exc).lower()
                    is_rate_limit = "429" in s or "too many requests" in s
                    if is_rate_limit and attempt < len(_RETRY_WAITS):
                        wait = _RETRY_WAITS[attempt]
                        log.warning(
                            "call_tool %s: rate-limited (attempt %d), waiting %ds",
                            tool_name, attempt + 1, wait,
                        )
                        await asyncio.sleep(wait)
                    else:
                        raise

        return _parse_content(raw)

    async def list_tools(self) -> list[ToolSchema]:
        """Return the list of tools from the MCP server as ToolSchema objects."""
        async with self._open_session() as session:
            response = await session.list_tools()
        return [_tool_to_schema(t) for t in response.tools]


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _parse_content(raw: Any) -> Any:
    """Extract and parse the text content from an MCP call_tool response.

    - Joins all TextContent blocks into one string.
    - Tries json.loads; falls back to ``{"result": text}`` for plain text.
    - Raises SpaceMoltError if the parsed JSON contains ``{"error": …}``.
    """
    text = "".join(
        block.text
        for block in raw.content
        if hasattr(block, "text")
    )

    if not text:
        return {}

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {"result": text}

    if isinstance(data, dict) and data.get("error"):
        err = data["error"]
        if isinstance(err, dict):
            raise SpaceMoltError(
                err.get("code", "unknown"),
                err.get("message", str(err)),
            )
        raise SpaceMoltError("unknown", str(err))

    return data


def _tool_to_schema(tool: Any) -> ToolSchema:
    """Convert an mcp.types.Tool to the gateway's ToolSchema.

    Skips the ``session_id`` parameter — it is injected by GameClient,
    never exposed to the LLM.
    """
    schema: dict = tool.inputSchema if isinstance(tool.inputSchema, dict) else {}
    props: dict = schema.get("properties", {})
    required: set[str] = set(schema.get("required", []))

    params = [
        ParamSchema(
            name=name,
            type=prop.get("type", "string"),
            required=name in required,
            description=prop.get("description", ""),
        )
        for name, prop in props.items()
        if name != "session_id"
    ]

    return ToolSchema(
        name=tool.name,
        description=tool.description or "",
        params=params,
    )
