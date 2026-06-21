"""Tool registry -- plugs raw proxy tools and skills into the MCP server.

Pattern for adding a new raw tool:
  1. Define an async function inside register_raw_tools.
  2. Decorate with @mcp.tool().
  3. Delegate to client.call("<spacemolt-tool>", action="<action>", ...).

Pattern for adding a skill:
  Import and call its register() function from register_skills().
"""

from mcp.server.fastmcp import FastMCP

from app.game_client import GameClient

_LOW_LEVEL = "[LOW LEVEL] Prefer a skill when one exists for this goal."


def register_raw_tools(mcp: FastMCP, client: GameClient) -> None:
    """Register raw SpaceMolt proxy tools on *mcp*.

    Each tool is a thin wrapper: it injects the session and forwards the call.
    No game logic lives here.
    """

    @mcp.tool(description=(
        "Return the current ship and player status from SpaceMolt. "
        "Includes location, hull, shields, cargo, credits, and fuel. "
        + _LOW_LEVEL
    ))
    async def get_status() -> str:
        return await client.call("spacemolt", action="get_status")

    @mcp.tool(description=(
        "Extract resources at the current location. "
        "Requires a mining laser. Ship must be undocked at a mineable POI. "
        + _LOW_LEVEL
    ))
    async def mine() -> str:
        return await client.call("spacemolt", action="mine")

    @mcp.tool(description=(
        "Travel to a point of interest (POI) in the current system. "
        "poi_id: ID of the destination POI. "
        + _LOW_LEVEL
    ))
    async def travel(poi_id: str) -> str:
        return await client.call("spacemolt", action="travel", id=poi_id)


def register_skills(mcp: FastMCP, client: GameClient) -> None:
    """Register high-level skill tools on *mcp*.

    Each skill module exposes a register(mcp, client) function.
    Add calls here as new skills are built.
    """
    from app.skills.mining import tool as mining_tool
    mining_tool.register(mcp, client)
