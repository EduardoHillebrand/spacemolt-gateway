"""Mining skill tool: registers mining_run on the MCP gateway.

This module is the glue layer. It:
  1. Reads the game state via GameClient.
  2. Parses it into a MiningState.
  3. Calls the planner to build a Plan.
  4. Calls the executor to run the Plan.
  5. Returns a human-readable summary.

No mining logic lives here.
"""

from __future__ import annotations

import json
import logging

from mcp.server.fastmcp import FastMCP

from app.game_client import GameClient
from app.skills.mining.executor import run_mining_plan
from app.skills.mining.planner import build_mining_plan
from app.skills.mining.schema import MiningResult, MiningState

log = logging.getLogger(__name__)


def register(mcp: FastMCP, client: GameClient) -> None:
    """Register the mining_run tool on the gateway."""

    @mcp.tool(description=(
        "Mine ore until the cargo is full, then travel to the home base, "
        "dock, and sell all ore. Returns a summary with credits earned. "
        "Preconditions: mining laser installed, at a minable POI, cargo not full."
    ))
    async def mining_run() -> str:
        log.info("mining_run: called")

        # 1. Read current game state
        raw = await client.call("spacemolt", action="get_status")
        state = _parse_mining_state(raw)

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


def _parse_mining_state(raw) -> MiningState:
    """Extract MiningState from the raw get_status response.

    Defensive: every field has a safe default so parsing never crashes
    even if the game changes its response shape.
    """
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            log.warning("_parse_mining_state: could not parse response as JSON")
            raw = {}

    if not isinstance(raw, dict):
        raw = {}

    # --- modules: check for mining laser ---
    modules = raw.get("modules") or []
    has_laser = any(
        (m.get("type") == "mining_laser" or "mining" in str(m.get("name", "")).lower())
        for m in modules
        if isinstance(m, dict)
    )

    # --- cargo ---
    cargo = raw.get("cargo") or {}
    if isinstance(cargo, dict):
        cargo_used = int(cargo.get("used", cargo.get("current", 0)))
        cargo_capacity = int(cargo.get("capacity", cargo.get("max", 1)))
    else:
        cargo_used = 0
        cargo_capacity = 1

    # --- location ---
    location = raw.get("location") or {}
    if isinstance(location, dict):
        poi = location.get("poi") or {}
        poi_type = str(poi.get("type", "")).lower() if isinstance(poi, dict) else ""
        minable_types = {"asteroid", "asteroid_belt", "asteroid_field", "mining"}
        at_minable = poi.get("minable", False) or poi_type in minable_types

        # home base: the station where we're heading to sell
        home_base = (
            location.get("base_poi_id")
            or location.get("home_base_id")
            or location.get("station_id")
            or location.get("base_id")
            or "home"
        )
    else:
        at_minable = False
        home_base = "home"

    return MiningState(
        has_mining_laser=has_laser,
        cargo_used=cargo_used,
        cargo_capacity=cargo_capacity,
        at_minable_poi=at_minable,
        home_base_poi_id=str(home_base),
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
