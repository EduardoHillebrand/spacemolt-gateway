"""Mining planner: builds a Plan from a MiningState.

Pure function -- no I/O, no game calls, fully testable.

The plan follows the spec sequence:
  1. mine_until_depleted_or_full  (depletion/relocation/survey handled by executor)
  2. travel to home_base
  3. dock
  4. sell_all_ore

Preconditions (checked in priority order):
  0. Fuel sufficient for round trip (if fuel_per_jump_estimate > 0).
  1. Ship has a mining laser installed.
  2. Ship is at a minable POI.
  3. Cargo has free space.

If any precondition is unmet, returns Plan.failed(reason) with an empty
step list. The executor and the LLM can decide what to do from there.
"""

from __future__ import annotations

import logging

from app.skills.mining.schema import MiningState, Plan, Step

log = logging.getLogger(__name__)

# Minimum fuel multiplier: we need at least this many "jump units" to safely
# return to base. 2x = one jump there + margin.
_FUEL_RETURN_FACTOR = 2


def build_mining_plan(state: MiningState) -> Plan:
    """Build a mining plan from the current game state.

    Args:
        state: Snapshot of the relevant game state.

    Returns:
        A Plan with steps if all preconditions pass,
        or Plan.failed(reason) if any precondition is unmet.
    """
    log.info(
        "build_mining_plan: laser=%s at_minable=%s cargo=%d/%d fuel=%d/%d "
        "fuel_estimate=%d home=%s other_pois=%s",
        state.has_mining_laser,
        state.at_minable_poi,
        state.cargo_used,
        state.cargo_capacity,
        state.fuel_current,
        state.fuel_capacity,
        state.fuel_per_jump_estimate,
        state.home_base_poi_id,
        state.other_minable_poi_ids,
    )

    # 0. Fuel check (only when fuel_per_jump_estimate is configured)
    if state.fuel_per_jump_estimate > 0:
        min_fuel = state.fuel_per_jump_estimate * _FUEL_RETURN_FACTOR
        if state.fuel_current < min_fuel:
            reason = (
                f"fuel insuficiente para ida e volta ate a base "
                f"({state.fuel_current} < {min_fuel} unidades necessarias)"
            )
            log.info("build_mining_plan: precondition failed — %s", reason)
            return Plan.failed(reason)

    # 1. Mining laser
    if not state.has_mining_laser:
        reason = "falta laser de mineracao instalado"
        log.info("build_mining_plan: precondition failed — %s", reason)
        return Plan.failed(reason)

    # 2. Minable POI
    if not state.at_minable_poi:
        reason = "nave nao esta em ponto mineravel"
        log.info("build_mining_plan: precondition failed — %s", reason)
        return Plan.failed(reason)

    # 3. Cargo space
    if state.cargo_full:
        reason = "cargo ja esta cheio — venda antes de minerar"
        log.info("build_mining_plan: precondition failed — %s", reason)
        return Plan.failed(reason)

    steps = [
        Step(op="mine_until_depleted_or_full"),
        Step(op="travel", target=state.home_base_poi_id),
        Step(op="dock"),
        Step(op="sell_all_ore"),
    ]

    log.info("build_mining_plan: plan ready with %d steps", len(steps))
    return Plan(steps=steps)
