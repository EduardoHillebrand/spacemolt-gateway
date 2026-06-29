"""Mining skill tool: registers mining_run on the MCP gateway.

This module is the glue layer. It:
  1. Reads the game state via GameClient (get_status + optional get_system).
  2. Parses it into a MiningState (including fuel and other POIs).
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

For 0006 resilience: also calls get_system to find other minable POIs in the
system so the executor can relocate when the current POI depletes.
"""

from __future__ import annotations

import dataclasses
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
# Conservative fuel estimate per jump — updated from get_status if fuel data found.
_DEFAULT_FUEL_PER_JUMP = 0  # 0 = disabled until we can read real values


def register(mcp: FastMCP, client: GameClient) -> None:
    """Register the mining_run tool on the gateway."""

    @mcp.tool(description=(
        "Mine ore until the cargo is full (or system is depleted / fuel is low), "
        "then travel to home_base, dock, and sell all ore. "
        "Returns a summary with credits earned and resilience stats. "
        "Preconditions: mining laser installed, at a minable POI, cargo not full, "
        "sufficient fuel (when fuel data is available). "
        "home_base: POI id of the station to sell at "
        "(default: confederacy_central_command)."
    ))
    async def mining_run(home_base: str = _DEFAULT_HOME_BASE) -> str:
        log.info("mining_run: called, home_base=%s", home_base)

        # 1. Read current game state
        raw = await client.call("spacemolt", action="get_status")
        state = _parse_mining_state(raw, home_base=home_base)

        # 2. Try to enrich with other minable POIs from get_system
        state = await _enrich_with_system_pois(state, client)

        log.info(
            "mining_run: state parsed — laser=%s minable=%s cargo=%d/%d "
            "fuel=%d/%d fuel_jump=%d home=%s other_pois=%s",
            state.has_mining_laser, state.at_minable_poi,
            state.cargo_used, state.cargo_capacity,
            state.fuel_current, state.fuel_capacity,
            state.fuel_per_jump_estimate, state.home_base_poi_id,
            state.other_minable_poi_ids,
        )

        # 3. Build plan (precondition check happens here)
        plan = build_mining_plan(state)

        if not plan.ok:
            log.info("mining_run: precondition failed — %s", plan.failure_reason)
            return f"Nao foi possivel iniciar mineracao: {plan.failure_reason}"

        # 4. Execute
        result = await run_mining_plan(plan, client, state)

        # 5. Format summary
        return _format_result(result)


async def _enrich_with_system_pois(state: MiningState, client: GameClient) -> MiningState:
    """Try to add other minable POI ids from get_system.

    On failure, returns the original state unchanged (non-critical).
    """
    if state.other_minable_poi_ids:
        return state  # already populated

    try:
        raw_system = await client.call("spacemolt", action="get_system")
        other_pois = _parse_system_pois(raw_system)
        if other_pois:
            log.info("mining_run: system POIs found: %s", other_pois)
            return dataclasses.replace(state, other_minable_poi_ids=other_pois)
    except Exception as exc:
        log.warning("_enrich_with_system_pois: failed to get system POIs: %s", exc)

    return state


def _parse_system_pois(raw) -> list[str]:
    """Extract minable POI ids from a get_system response.

    Handles text and dict formats. Returns empty list on failure.
    """
    if isinstance(raw, dict):
        pois = (
            raw.get("pois")
            or (raw.get("system") or {}).get("pois")
            or []
        )
        return [
            p.get("id") or p.get("poi_id", "")
            for p in pois
            if isinstance(p, dict) and p.get("minable", False)
        ]

    # Text format — simple regex: look for minable POI ids
    # SpaceMolt text might include lines like: "sol_belt_1 (Asteroid Belt) [minable]"
    if isinstance(raw, str):
        return re.findall(r'(\w+)\s+\([^)]+\)\s+\[minable\]', raw)

    return []


def _parse_mining_state(raw, *, home_base: str = _DEFAULT_HOME_BASE) -> MiningState:
    """Extract MiningState from the raw get_status response.

    Handles two formats:
    - JSON string / dict: future-proof, try json.loads then dict extraction.
    - Text string: current SpaceMolt format, parsed with regex.

    Every field has a safe default so parsing never crashes.
    """
    if isinstance(raw, str):
        try:
            raw_dict = json.loads(raw)
            return _parse_from_dict(raw_dict, home_base=home_base)
        except (json.JSONDecodeError, TypeError):
            pass
        return _parse_from_text(raw, home_base=home_base)

    if isinstance(raw, dict):
        return _parse_from_dict(raw, home_base=home_base)

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
      Fuel: X/Y              -> fuel_current, fuel_capacity
      mining_laser (in text) -> has_mining_laser
      Resources (N):         -> at_minable_poi (section only present at minable POIs)
    """
    has_laser = bool(re.search(r'\bmining_laser', text))

    cargo_used = 0
    cargo_capacity = 1
    cargo_match = re.search(r'Cargo:\s*(\d+)/(\d+)', text)
    if cargo_match:
        cargo_used = int(cargo_match.group(1))
        cargo_capacity = int(cargo_match.group(2))

    fuel_current = 0
    fuel_capacity = 0
    fuel_match = re.search(r'Fuel:\s*(\d+)/(\d+)', text)
    if fuel_match:
        fuel_current = int(fuel_match.group(1))
        fuel_capacity = int(fuel_match.group(2))

    at_minable = bool(re.search(r'^Resources \(\d+\):', text, re.MULTILINE))

    return MiningState(
        has_mining_laser=has_laser,
        cargo_used=cargo_used,
        cargo_capacity=cargo_capacity,
        at_minable_poi=at_minable,
        home_base_poi_id=home_base,
        fuel_current=fuel_current,
        fuel_capacity=fuel_capacity,
        fuel_per_jump_estimate=_DEFAULT_FUEL_PER_JUMP,
    )


def _parse_from_dict(raw: dict, *, home_base: str) -> MiningState:
    """Parse dict-based state (JSON format, future-proofing)."""
    modules = raw.get("modules") or []
    has_laser = any(
        "mining_laser" in str(m.get("type", "")).lower()
        for m in modules
        if isinstance(m, dict)
    )

    cargo_raw = raw.get("cargo") or {}
    if isinstance(cargo_raw, dict):
        cargo_used = int(cargo_raw.get("used", cargo_raw.get("current", 0)))
        cargo_capacity = int(cargo_raw.get("capacity", cargo_raw.get("max", 1)))
    else:
        cargo_used = 0
        cargo_capacity = 1

    ship = raw.get("ship") or {}
    fuel_current = int(ship.get("fuel_current", 0))
    fuel_capacity = int(ship.get("fuel_capacity", 0))

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
        fuel_current=fuel_current,
        fuel_capacity=fuel_capacity,
        fuel_per_jump_estimate=_DEFAULT_FUEL_PER_JUMP,
    )


def _format_result(result: MiningResult) -> str:
    if not result.ok:
        return f"Mineracao falhou: {result.failure_reason}"

    lines = [
        "Mineracao concluida!",
        f"  Ciclos de mineracao : {result.cycles}",
        f"  Minerio coletado    : {result.ore_collected} unidades",
        f"  Creditos ganhos     : {result.credits_earned:.2f}",
        f"  Localização final   : {result.final_location}",
        f"  Motivo de parada    : {result.stop_reason}",
    ]
    if result.relocations > 0:
        lines.append(f"  Realocacoes         : {result.relocations}")
    if result.surveys > 0:
        lines.append(f"  Surveys realizados  : {result.surveys}")

    return "\n".join(lines)
