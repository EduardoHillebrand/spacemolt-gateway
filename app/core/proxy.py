"""Dynamic proxy: discovers SpaceMolt tools at startup and registers them on FastMCP.

How it works:
  1. setup_proxy() calls client.list_tools() to get ToolSchema list from transport.
  2. For each tool, _make_proxy() creates an async function with a typed signature
     that mirrors the tool's ParamSchema list.
  3. The function is registered on the FastMCP instance via mcp.add_tool().
  4. Every call is logged at INFO before and after the forwarding.
  5. session_id is never exposed to the LLM — it is injected by GameClient.call().

If list_tools() raises, setup_proxy() logs the error and returns without
crashing the gateway (fallback to whatever tools were already registered).
"""

from __future__ import annotations

import inspect
import keyword
import logging
from typing import Any

from mcp.server.fastmcp import FastMCP

from app.game_client import GameClient, ToolSchema

log = logging.getLogger(__name__)

# Python type objects mapped from JSON Schema type strings
_PY_TYPES: dict[str, type] = {
    "string":  str,
    "integer": int,
    "number":  float,
    "boolean": bool,
}

# Safe defaults for optional parameters
_DEFAULTS: dict[type, Any] = {
    str:   "",
    int:   0,
    float: 0.0,
    bool:  False,
}


async def setup_proxy(mcp: FastMCP, client: GameClient) -> None:
    """Discover SpaceMolt tools via *client* and register a proxy for each.

    Called from the FastMCP lifespan so the event loop is already running.
    Safe to call multiple times (each call re-registers; FastMCP replaces).

    Args:
        mcp:    The FastMCP server instance to register proxies on.
        client: GameClient connected to a transport that implements list_tools().
    """
    try:
        tools = await client.list_tools()
    except Exception as exc:
        log.error(
            "setup_proxy: list_tools() failed (%s) — starting without dynamic proxies",
            exc,
        )
        return

    for tool_schema in tools:
        fn = _make_proxy(client, tool_schema)
        mcp.add_tool(fn, name=tool_schema.name, description=tool_schema.description)
        log.info("setup_proxy: registered proxy '%s'", tool_schema.name)

    log.info("setup_proxy: %d proxies registered", len(tools))


def _make_proxy(client: GameClient, tool: ToolSchema):
    """Create an async proxy function whose signature mirrors *tool*.

    FastMCP inspects the function's __signature__ to build the JSON Schema
    for the tool. We set that signature dynamically from the ToolSchema params
    so the MCP client sees proper parameter names and types.

    Args:
        client: GameClient used to forward the call.
        tool:   ToolSchema describing the tool to proxy.

    Returns:
        An async callable suitable for mcp.add_tool().
    """
    tool_name = tool.name

    # Map sanitized param names back to original SpaceMolt names.
    # e.g. "class_" -> "class" (Python keyword avoidance).
    _orig_names: dict[str, str] = {}
    for p in tool.params:
        safe = p.name + "_" if keyword.iskeyword(p.name) else p.name
        if safe != p.name:
            _orig_names[safe] = p.name

    # Inner implementation — called via **kwargs after FastMCP unpacks args.
    async def _impl(**kwargs: Any) -> str:
        # Restore original names for any sanitized keywords.
        call_kwargs = {_orig_names.get(k, k): v for k, v in kwargs.items()}
        log.info("proxy.%s: %s", tool_name, call_kwargs)
        result = await client.call(tool_name, **call_kwargs)
        log.info("proxy.%s: done", tool_name)
        return str(result)

    # Build inspect.Parameter list from ParamSchema list.
    # Required params MUST come before optional ones — Python rejects the opposite.
    required_params = [p for p in tool.params if p.required]
    optional_params = [p for p in tool.params if not p.required]

    params: list[inspect.Parameter] = []
    for p in required_params + optional_params:
        py_type = _PY_TYPES.get(p.type, str)
        # Sanitize Python reserved keywords (e.g. "class" -> "class_")
        safe_name = p.name + "_" if keyword.iskeyword(p.name) else p.name
        if p.required:
            param = inspect.Parameter(
                safe_name,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                annotation=py_type,
            )
        else:
            param = inspect.Parameter(
                safe_name,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                default=_DEFAULTS.get(py_type, ""),
                annotation=py_type,
            )
        params.append(param)

    _impl.__signature__ = inspect.Signature(params, return_annotation=str)
    _impl.__name__ = tool_name
    _impl.__qualname__ = tool_name
    return _impl