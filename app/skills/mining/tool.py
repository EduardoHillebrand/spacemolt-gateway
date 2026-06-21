"""Mining skill tool: registers mining_run on the MCP gateway.

This module is the glue layer. It:
  1. Reads the game state via GameClient.
  2. Parses it into a MiningState.
  3. Calls the planner to build a Plan.
  4. Calls the executor to run the Plan.
  5. Returns a human-readable summary.

No mining logic lives here.

SpaceMolt get_status returns formatted TEXT (not JSON). Example:

  GatewayMiner [solarian] | 500cr | Sol
  Ship: Theoria (theoria) | Hull: 100/100 | ...
  Fuel: 99/100 | Cargo: 3/70 | CPU: 2/16 | Power: 5/28
  Security: Maximum Security (empire capital)
  Connections: sirius, alpha_centauri
  Modules (1):
  id	type	slot	size	wear	stats
  0974...  mining_laser_i	utility	10	Pristine	mining_power:5
  Resources (6):
  resource	richness	remaining
  Iron Ore	80	240
  ...

_parse_mining_state detects text vs JSON and dispatches accordingly.
"""

from __future__ import annotations

import json
import logging
import re

from mcp.server.fastmcp import FastMCP

from app.game_client import GameClient
from app.skills.mining.executor import run_mining_plan
from app.skills.mining.planner import build_mining_plan
from app.skills.mining.schema import MiningResult, MiningState

log = logging.getLogger(__name__)

_DEFAULT_HOME_BASE = "confederacy_central_command"


def register(mcp: FastMCP, client: GameClient) -> None:
    """Register the mining_run tool on the gateway."""

    @mcp.tool(description=(
        "Mine ore until the cargo is full, then travel to home_base, "
        "dock, and sell all ore. Returns a summary with credits earned. "
        "Preconditions: mining laser installed, at a minable POI, cargo not full. "
        "home_base: POI id of the station to sell at "
        "(default: confederacy_central_command)."
    ))
    async def mining_run(home_base: str = _DEFAULT_HOME_BASE) -> str:
        log.info("mining_run: called, home_base=%s", home_base)

        # 1. Read current game state
        raw = await client.call("spacemolt", action="get_status")
        state = _parse_mining_state(raw, home_base=home_base)

        log.info(
            "mining_run: state parsed — laser=%s minable=%s cargo=%d/%d home=%s",
            state.has_mining_laser, state.at_minable_poi,
            state.cargo_used, state.cargo_capacity, state.home_base_poi_id,
        )

        # 2. Build plan (precondition check happens here)
        plan = build_mining_plan(state)

        if not plan.ok:
            log.info("mining_run: precondition failed — %s", plan.failure_reason)
            return f"Nao foi possivel iniciar mineracao: {plan.failure_reason}"

        # 3. Execute
        result = await run_mining_plan(plan, client)

        # 4. Format summary
        return _format_result(result)


def _parse_mining_state(raw, *, home_base: str = _DEFAULT_HOME_BASE) -> MiningState:
    """Extract MiningState from the raw get_status response.

    Handles two formats:
    - JSON string / dict: future-proof, try json.loads then dict extraction.
    - Text string: current SpaceMolt format, parsed with regex.

    Every field has a safe default so parsing never crashes.
    """
    if isinstance(raw, str):
        # Try JSON first (future-proofing if SpaceMolt changes format)
        try:
            raw_dict = json.loads(raw)
            return _parse_from_dict(raw_dict, home_base=home_base)
        except (json.JSONDecodeError, TypeError):
            pass
        # Current SpaceMolt format: formatted text
        return _parse_from_text(raw, home_base=home_base)

    if isinstance(raw, dict):
        return _parse_from_dict(raw, home_base=home_base)

    # Unknown format — safe defaults
    log.warning("_parse_mining_state: unexpected raw type %s", type(raw).__name__)
    return MiningState(
        has_mining_laser=False,
        cargo_used=0,
        cargo_capacity=1,
        at_minable_poi=False,
        home_base_poi_id=home_base,
    )


def _parse_from_text(text: str, *, home_base: str) -> MiningState:
    """Parse the text format returned by SpaceMolt get_status.

    Patterns (all case-sensitive, matching observed output):
      Cargo: X/Y             -> cargo_used, cargo_capacity
      mining_laser (in text) -> has_mining_laser
      Resources (N):         -> at_minable_poi (section only present at minable POIs)
    """
    # has_mining_laser: 'mining_laser' appears in the Modules table
    has_laser = bool(re.search(r'\bmining_laser', text))

    # cargo: "Cargo: X/Y" on the stats line
    cargo_used = 0
    cargo_capacity = 1
    cargo_match = re.search(r'Cargo:\s*(\d+)/(\d+)', text)
    if cargo_match:
        cargo_used = int(cargo_match.group(1))
        cargo_capacity = int(cargo_match.group(2))

    # at_minable_poi: the Resources section only appears at asteroid belts / minable POIs
    at_minable = bool(re.search(r'^Resources \(\d+\):', text, re.MULTILINE))

    return MiningState(
        has_mining_laser=has_laser,
        cargo_used=cargo_used,
        cargo_capacity=cargo_capacity,
        at_minable_poi=at_minable,
        home_base_poi_id=home_base,
    )


def _parse_from_dict(raw: dict, *, home_base: str) -> MiningState:
    """Parse dict-based state (JSON format, future-proofing)."""
    # modules: check for mining laser by type name
    modules = raw.get("modules") or []
    has_laser = any(
        "mining_laser" in str(m.get("type", "")).lower()
        for m in modules
        if isinstance(m, dict)
    )

    # cargo
    cargo_raw = raw.get("cargo") or {}
    if isinstance(cargo_raw, dict):
        cargo_used = int(cargo_raw.get("used", cargo_raw.get("current", 0)))
        cargo_capacity = int(cargo_raw.get("capacity", cargo_raw.get("max", 1)))
    else:
        cargo_used = 0
        cargo_capacity = 1

    # location / poi
    location = raw.get("location") or {}
    if isinstance(location, dict):
        poi = location.get("poi") or {}
        poi_type = str(poi.get("type", "")).lower() if isinstance(poi, dict) else ""
        minable_types = {"asteroid", "asteroid_belt", "asteroid_field", "mining"}
        at_minable = poi.get("minable", False) or poi_type in minable_types
    else:
        at_minable = False

    return MiningState(
        has_mining_laser=has_laser,
        cargo_used=cargo_used,
        cargo_capacity=cargo_capacity,
        at_minable_poi=at_minable,
        home_base_poi_id=home_base,
    )


def _format_result(result: MiningResult) -> str:
    if not result.ok:
        return f"Mineracao falhou: {result.failure_reason}"

    return (
        f"Mineracao concluida!\n"
        f"  Ciclos de mineracao : {result.cycles}\n"
        f"  Minerio coletado    : {result.ore_collected} unidades\n"
        f"  Creditos ganhos     : {result.credits_earned:.2f}\n"
        f"  Localização final   : {result.final_location}"
    )
