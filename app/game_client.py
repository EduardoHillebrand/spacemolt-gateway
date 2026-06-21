"""Single point of contact with the SpaceMolt MCP server.

All credentials and session state live here.
Nothing else in the project calls SpaceMolt directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


# ---------------------------------------------------------------------------
# Tool schema types (used by transport discovery and proxy registration)
# ---------------------------------------------------------------------------

@dataclass
class ParamSchema:
    """Describes one parameter of a SpaceMolt tool."""

    name: str
    type: str          # "string" | "integer" | "number" | "boolean"
    required: bool
    description: str = ""


@dataclass
class ToolSchema:
    """Describes a SpaceMolt MCP tool (name, description, parameters)."""

    name: str
    description: str
    params: list[ParamSchema] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Transport protocol
# ---------------------------------------------------------------------------

@runtime_checkable
class MCPTransport(Protocol):
    """Minimal interface the GameClient needs from the MCP layer.

    The real implementation wraps an MCP ClientSession.
    Tests inject a fake that records calls.
    """

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """Call a tool on the remote MCP server and return the result."""
        ...

    async def list_tools(self) -> list[ToolSchema]:
        """Return the list of tools available on the remote MCP server."""
        ...


# ---------------------------------------------------------------------------
# GameClient
# ---------------------------------------------------------------------------

class GameClient:
    """Forwards tool calls to SpaceMolt, always injecting the session_id.

    Usage::

        client = GameClient(transport=real_transport, session_id="sess-abc")
        result = await client.call("spacemolt", action="mine")
        tools  = await client.list_tools()
    """

    def __init__(self, transport: MCPTransport, session_id: str) -> None:
        self._transport = transport
        self._session_id = session_id

    async def call(self, tool_name: str, **args: Any) -> Any:
        """Forward *tool_name* to SpaceMolt with *args*, plus the session_id.

        Args:
            tool_name: Name of the SpaceMolt tool (e.g. "spacemolt").
            **args:    Tool-specific arguments.

        Returns:
            Whatever the SpaceMolt tool returns.
        """
        payload = {**args, "session_id": self._session_id}
        return await self._transport.call_tool(tool_name, payload)

    async def list_tools(self) -> list[ToolSchema]:
        """Return tool schemas from the transport (used by the proxy layer)."""
        return await self._transport.list_tools()
