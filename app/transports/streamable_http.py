"""Real MCP transport via streamablehttp_client + ClientSession.

Connects to the SpaceMolt MCP server at a given URL, implements throttling
(300 ms min gap between calls) and retry on 429 (15 / 30 / 60 s backoff).

Usage::

    transport = StreamableHTTPTransport("https://game.spacemolt.com/mcp")
    await transport.connect()
    result = await transport.call_tool("spacemolt", {"action": "mine", "session_id": "…"})
    tools  = await transport.list_tools()
    await transport.disconnect()
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from contextlib import AsyncExitStack
from typing import Any

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
    """MCPTransport that connects to SpaceMolt via streamable HTTP.

    Implements ``connect`` / ``disconnect`` for lifecycle management, plus
    ``call_tool`` and ``list_tools`` from the MCPTransport protocol.
    """

    def __init__(self, url: str) -> None:
        self._url = url
        self._session: ClientSession | None = None
        self._exit_stack: AsyncExitStack | None = None
        self._last_call_t: float = 0.0

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """Open the MCP session. Must be called before any call_tool / list_tools."""
        self._exit_stack = AsyncExitStack()
        transport = await self._exit_stack.enter_async_context(
            streamablehttp_client(self._url)
        )
        read_stream, write_stream, _ = transport
        self._session = await self._exit_stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )
        await self._session.initialize()
        log.info("StreamableHTTPTransport: connected to %s", self._url)

    async def disconnect(self) -> None:
        """Close the MCP session cleanly."""
        if self._exit_stack is not None:
            try:
                await asyncio.wait_for(self._exit_stack.aclose(), timeout=5.0)
            except Exception as exc:
                log.warning("StreamableHTTPTransport: disconnect error: %s", exc)
            finally:
                self._exit_stack = None
                self._session = None
        log.info("StreamableHTTPTransport: disconnected")

    # ------------------------------------------------------------------
    # MCPTransport protocol
    # ------------------------------------------------------------------

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """Call a tool, parse the response, throttle, and retry on 429."""
        if self._session is None:
            raise RuntimeError("Not connected — call connect() first")

        # Throttle: ensure minimum gap between consecutive calls
        now = time.monotonic()
        gap = now - self._last_call_t
        if gap < _MIN_CALL_GAP_S:
            await asyncio.sleep(_MIN_CALL_GAP_S - gap)

        # Call with 429 retry backoff
        for attempt in range(len(_RETRY_WAITS) + 1):
            try:
                raw = await self._session.call_tool(tool_name, arguments)
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
        if self._session is None:
            raise RuntimeError("Not connected — call connect() first")
        response = await self._session.list_tools()
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
