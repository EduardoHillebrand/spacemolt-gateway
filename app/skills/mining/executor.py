"""Mining executor: runs a Plan step-by-step against the game.

Receives a Plan and a GameClient (injected). Returns a MiningResult.

Core loop: mine_until_depleted_or_full
  - Mines in a loop until cargo is full, POI is depleted, fuel is low,
    or the safety cap (_MINE_LOOP_MAX) is reached.
  - Depletion: _DEPLETION_LIMIT consecutive zero-ore returns → POI exhausted.
  - Relocation: moves to the next POI from state.other_minable_poi_ids.
  - Survey: if no POIs remain, calls survey_system to look for new ones.
  - Fuel: if fuel_per_jump_estimate > 0 and fuel_remaining <= min_fuel_return,
    stops with stop_reason="low_fuel".

SpaceMolt response format (actions return nested JSON):
  mine  -> {"details": {"quantity": N}, "ship": {"cargo_used": X, "cargo_capacity": Y,
             "fuel_current": F (optional)},
             "cargo": [{"item_id": "...", "quantity": N, "size": S}, ...]}
  sell  -> {"details": {"total_earned": F, "quantity_sold": N, ...}}
  survey_system -> {"pois": [{"id": "...", "minable": true/false}, ...]}
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from app.game_client import GameClient
from app.skills.mining.schema import MiningResult, MiningState, Plan

log = logging.getLogger(__name__)

_MINE_LOOP_MAX = 200   # hard cap: never mine more than this many times
_DEPLETION_LIMIT = 3   # consecutive zero-ore returns before POI is depleted


# ---------------------------------------------------------------------------
# Internal result type for the mine loop
# ---------------------------------------------------------------------------

@dataclass
class _MineLoopResult:
    cycles: int = 0
    ore_collected: int = 0
    cargo_items: list[dict] = field(default_factory=list)
    stop_reason: str = "cargo_full"
    relocations: int = 0
    surveys: int = 0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def run_mining_plan(
    plan: Plan,
    client: GameClient,
    state: MiningState | None = None,
) -> MiningResult:
    """Execute a mining plan step by step.

    Args:
        plan:   Built by build_mining_plan(). If plan.ok is False, returns
                MiningResult.failed immediately.
        client: GameClient for all game calls.
        state:  MiningState snapshot — used for fuel tracking and relocation.
                When None, fuel checks and relocation are disabled.

    Returns:
        MiningResult with statistics about the run.
    """
    if not plan.ok:
        log.info("run_mining_plan: plan not ok — %s", plan.failure_reason)
        return MiningResult.failed(plan.failure_reason or "plano invalido")

    effective_state = state if state is not None else _default_state()

    loop_result = _MineLoopResult()
    credits_earned = 0.0
    final_location = ""

    for step in plan.steps:
        log.info("run_mining_plan: step op=%s target=%s", step.op, step.target)

        if step.op in ("mine_until", "mine_until_depleted_or_full"):
            # "mine_until" is kept as an alias for backward compatibility.
            loop_result = await _mine_until_depleted_or_full(client, effective_state)

        elif step.op == "travel":
            await client.call("spacemolt", action="travel", id=step.target)
            final_location = step.target or ""

        elif step.op == "dock":
            await client.call("spacemolt", action="dock")

        elif step.op == "sell_all_ore":
            credits_earned = await _sell_all_ore(client, loop_result.cargo_items)

        else:
            log.warning("run_mining_plan: unknown op=%s — skipping", step.op)

    log.info(
        "run_mining_plan: done. cycles=%d ore=%d credits=%.2f "
        "relocations=%d surveys=%d stop=%s location=%s",
        loop_result.cycles, loop_result.ore_collected, credits_earned,
        loop_result.relocations, loop_result.surveys,
        loop_result.stop_reason, final_location,
    )

    return MiningResult(
        ok=True,
        cycles=loop_result.cycles,
        ore_collected=loop_result.ore_collected,
        credits_earned=credits_earned,
        final_location=final_location,
        relocations=loop_result.relocations,
        surveys=loop_result.surveys,
        stop_reason=loop_result.stop_reason,
    )


# ---------------------------------------------------------------------------
# Mine loop
# ---------------------------------------------------------------------------

async def _mine_until_depleted_or_full(
    client: GameClient,
    state: MiningState,
) -> _MineLoopResult:
    """Mine loop with depletion detection, relocation, survey, and fuel check.

    Loop exits when:
      - cargo is full         → stop_reason = "cargo_full"
      - system depleted       → stop_reason = "system_depleted"
      - fuel too low to return → stop_reason = "low_fuel"
      - safety cap reached    → stop_reason stays "cargo_full" (default)
    """
    available_pois = list(state.other_minable_poi_ids)
    consecutive_failures = 0
    fuel_remaining = state.fuel_current
    # Minimum fuel to keep: need at least one jump to get back.
    min_fuel_return = state.fuel_per_jump_estimate
    fuel_check_enabled = state.fuel_per_jump_estimate > 0

    result = _MineLoopResult()

    for _ in range(_MINE_LOOP_MAX):

        # --- Fuel check (before each mine call) ---
        if fuel_check_enabled and fuel_remaining <= min_fuel_return:
            log.info(
                "mine loop: low fuel — remaining=%d min_return=%d → stopping",
                fuel_remaining, min_fuel_return,
            )
            result.stop_reason = "low_fuel"
            break

        # --- Mine ---
        response = await client.call("spacemolt", action="mine")
        result.cycles += 1

        if not isinstance(response, dict):
            log.info("mine loop: cycle %d — unexpected format: %r", result.cycles, response)
            continue

        details = response.get("details") or {}
        ship = response.get("ship") or {}

        ore_this = int(details.get("quantity", 0))
        result.ore_collected += ore_this

        # Fuel from response (optional field)
        fuel_from_resp = ship.get("fuel_current")
        if fuel_from_resp is not None:
            fuel_remaining = int(fuel_from_resp)

        cargo_used = int(ship.get("cargo_used", 0))
        cargo_capacity = int(ship.get("cargo_capacity", 0))

        raw_cargo = response.get("cargo")
        if isinstance(raw_cargo, list):
            result.cargo_items = raw_cargo

        log.info(
            "mine loop: cycle=%d ore_this=%d total=%d cargo=%d/%d fuel=%d",
            result.cycles, ore_this, result.ore_collected,
            cargo_used, cargo_capacity, fuel_remaining,
        )

        if ore_this > 0:
            consecutive_failures = 0
            # Cargo full?
            if cargo_capacity > 0 and cargo_used >= cargo_capacity:
                log.info("mine loop: cargo full after %d cycles", result.cycles)
                result.stop_reason = "cargo_full"
                break
        else:
            # Nothing came out — possible depletion
            consecutive_failures += 1
            log.info(
                "mine loop: zero ore (consecutive=%d / limit=%d)",
                consecutive_failures, _DEPLETION_LIMIT,
            )

            if consecutive_failures >= _DEPLETION_LIMIT:
                # POI is depleted — try to relocate
                if available_pois:
                    next_poi = available_pois.pop(0)
                    log.info(
                        "mine loop: POI depleted — relocating to %s (relocation #%d)",
                        next_poi, result.relocations + 1,
                    )
                    await client.call("spacemolt", action="travel", id=next_poi)
                    fuel_remaining -= state.fuel_per_jump_estimate
                    result.relocations += 1
                    consecutive_failures = 0
                else:
                    # No known POIs — call survey and try again
                    log.info("mine loop: no more POIs — calling survey_system")
                    survey_resp = await client.call("spacemolt", action="survey_system")
                    result.surveys += 1
                    new_pois = _parse_survey_pois(survey_resp)
                    log.info("mine loop: survey returned %d new POIs", len(new_pois))

                    if new_pois:
                        available_pois.extend(new_pois)
                        next_poi = available_pois.pop(0)
                        await client.call("spacemolt", action="travel", id=next_poi)
                        fuel_remaining -= state.fuel_per_jump_estimate
                        result.relocations += 1
                        consecutive_failures = 0
                    else:
                        log.info("mine loop: system depleted — no deposits found")
                        result.stop_reason = "system_depleted"
                        break

    else:
        log.warning("mine loop: safety cap %d reached", _MINE_LOOP_MAX)

    return result


def _parse_survey_pois(response: Any) -> list[str]:
    """Extract minable POI ids from a survey_system response.

    Expected format:
        {"pois": [{"id": "...", "minable": true}, ...]}

    Returns a list of ids where minable is True.
    """
    if not isinstance(response, dict):
        return []
    pois = response.get("pois") or response.get("result") or []
    if not isinstance(pois, list):
        return []
    return [
        p.get("id") or p.get("poi_id", "")
        for p in pois
        if isinstance(p, dict) and p.get("minable", False)
    ]


def _default_state() -> MiningState:
    """Minimal state when caller doesn't provide one.

    fuel_per_jump_estimate=0 disables fuel checks.
    other_minable_poi_ids=[] disables relocation.
    """
    return MiningState(
        has_mining_laser=True,
        cargo_used=0,
        cargo_capacity=0,
        at_minable_poi=True,
        home_base_poi_id="",
        fuel_per_jump_estimate=0,
        other_minable_poi_ids=[],
    )


# ---------------------------------------------------------------------------
# Sell helper
# ---------------------------------------------------------------------------

async def _sell_all_ore(client: GameClient, cargo_items: list[dict]) -> float:
    """Sell all cargo items tracked from mine responses.

    SpaceMolt sell response format:
        {"details": {"total_earned": F, "quantity_sold": N, "unsold": N, ...}}

    Sells each item_id individually and sums total_earned.

    Returns:
        Total credits earned (float). 0.0 if nothing to sell or no buyers.
    """
    if not cargo_items:
        log.info("sell_all_ore: no cargo items to sell")
        return 0.0

    total_credits = 0.0

    for item in cargo_items:
        item_id = item.get("item_id") or item.get("id")
        qty = int(item.get("quantity", 1))

        if not item_id or qty <= 0:
            continue

        response = await client.call("spacemolt", action="sell", id=item_id, quantity=qty)

        if isinstance(response, dict):
            details = response.get("details") or {}
            earned = float(details.get("total_earned", 0.0))
            sold = int(details.get("quantity_sold", 0))
            unsold = int(details.get("unsold", 0))
            total_credits += earned
            log.info(
                "sell_all_ore: %s x%d → sold=%d unsold=%d earned=%.2f cr",
                item_id, qty, sold, unsold, earned,
            )
        else:
            log.info("sell_all_ore: unexpected response for %s: %r", item_id, response)

    log.info("sell_all_ore: total earned %.2f cr", total_credits)
    return total_credits
