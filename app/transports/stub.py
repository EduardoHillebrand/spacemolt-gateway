"""Stub transport for local development and manual testing.

Returns a canned response for every call so the gateway can start and be
inspected without a live SpaceMolt connection.

list_tools() returns a hardcoded list that mirrors the most-used SpaceMolt
tools. This is the list used by setup_proxy when no real connection exists.
"""

from __future__ import annotations

from typing import Any

from app.game_client import ParamSchema, ToolSchema

# ---------------------------------------------------------------------------
# Hardcoded tool list for stub mode
# ---------------------------------------------------------------------------

_P = ParamSchema  # alias for brevity

STUB_TOOLS: list[ToolSchema] = [
    ToolSchema(
        name="spacemolt",
        description="[PROXY] Main SpaceMolt game tool. "
                    "[LOW LEVEL] Prefer a skill when one exists for this goal.",
        params=[
            _P("action",   "string",  True,  "Action to perform (mine, travel, dock, sell, ...)"),
            _P("id",       "string",  False, "Target id (poi, item, npc, etc.)"),
            _P("quantity", "integer", False, "Quantity (sell, transfer, etc.)"),
            _P("price",    "number",  False, "Price per unit (market orders)"),
            _P("message",  "string",  False, "Text message (social actions)"),
        ],
    ),
    ToolSchema(
        name="spacemolt_auth",
        description="[PROXY] SpaceMolt authentication (login, register, logout).",
        params=[
            _P("action",            "string", True,  "login | register | logout"),
            _P("username",          "string", False, "Account username"),
            _P("password",          "string", False, "Account password"),
            _P("registration_code", "string", False, "Code for new registration"),
        ],
    ),
    ToolSchema(
        name="spacemolt_market",
        description="[PROXY] Market and trade orders. "
                    "[LOW LEVEL] Prefer a skill when one exists for this goal.",
        params=[
            _P("action",     "string",  True,  "list | buy | create_sell_order | cancel"),
            _P("id",         "string",  False, "Item id"),
            _P("quantity",   "integer", False, "Quantity"),
            _P("price_each", "number",  False, "Price per unit"),
            _P("order_id",   "string",  False, "Order id (cancel)"),
        ],
    ),
    ToolSchema(
        name="spacemolt_ship",
        description="[PROXY] Ship management (refit, modules, rename).",
        params=[
            _P("action",    "string", True,  "status | refit | rename | modules"),
            _P("id",        "string", False, "Module or ship id"),
            _P("slot",      "string", False, "Slot name for refit"),
            _P("ship_name", "string", False, "New ship name"),
        ],
    ),
    ToolSchema(
        name="spacemolt_facility",
        description="[PROXY] Station facility operations (craft, refine, produce).",
        params=[
            _P("action",      "string",  True,  "list | use | status"),
            _P("id",          "string",  False, "Facility id"),
            _P("item_id",     "string",  False, "Item to produce or refine"),
            _P("quantity",    "integer", False, "Quantity to produce"),
        ],
    ),
]


# ---------------------------------------------------------------------------
# StubTransport
# ---------------------------------------------------------------------------

class StubTransport:
    """Logs every call and returns a descriptive placeholder response.

    Useful for verifying that the MCP protocol layer works end-to-end
    before wiring up the real SpaceMolt transport.
    """

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> str:
        args_repr = ", ".join(f"{k}={v!r}" for k, v in arguments.items())
        return f"[STUB] {tool_name}({args_repr})"

    async def list_tools(self) -> list[ToolSchema]:
        return list(STUB_TOOLS)
