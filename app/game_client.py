"""Single point of contact with the SpaceMolt MCP server.

All credentials and session state live here.
Nothing else in the project calls SpaceMolt directly.
"""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class MCPTransport(Protocol):
    """Minimal interface the GameClient needs from the MCP layer.

    The real implementation wraps an MCP ClientSession.
    Tests inject a fake that records calls.
    """

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """Call a tool on the remote MCP server and return the result."""
        ...


class GameClient:
    """Forwards tool calls to SpaceMolt, always injecting the session_id.

    Usage::

        client = GameClient(transport=real_transport, session_id="sess-abc")
        result = await client.call("mine", asteroid_id="A1")
    """

    def __init__(self, transport: MCPTransport, session_id: str) -> None:
        self._transport = transport
        self._session_id = session_id

    async def call(self, tool_name: str, **args: Any) -> Any:
        """Forward *tool_name* to SpaceMolt with *args*, plus the session_id.

        Args:
            tool_name: Name of the SpaceMolt tool (e.g. "mine", "travel").
            **args: Tool-specific arguments.

        Returns:
            Whatever the SpaceMolt tool returns.
        """
        payload = {**args, "session_id": self._session_id}
        return await self._transport.call_tool(tool_name, payload)
