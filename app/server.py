"""SpaceMolt Gateway — MCP server entry point.

Responsibilities:
- Create the FastMCP instance.
- Register raw proxy tools and skills (via registry).
- Run the server over stdio.

No game logic lives here.
"""

from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Server instance — imported by registry and by tests
# ---------------------------------------------------------------------------

mcp = FastMCP(name="spacemolt-gateway")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the gateway over stdio (used by Claude / MCP clients)."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
