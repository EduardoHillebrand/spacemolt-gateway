"""Stub transport for local development and manual testing.

Returns a canned response for every call so the gateway can start and be
inspected without a live SpaceMolt connection.
"""

from typing import Any


class StubTransport:
    """Logs every call and returns a descriptive placeholder response.

    Useful for verifying that the MCP protocol layer works end-to-end
    before wiring up the real SpaceMolt transport.
    """

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> str:
        args_repr = ", ".join(f"{k}={v!r}" for k, v in arguments.items())
        return f"[STUB] {tool_name}({args_repr})"
