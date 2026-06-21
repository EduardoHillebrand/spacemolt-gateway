"""Mining planner: builds a Plan from a MiningState.

Pure function -- no I/O, no game calls, fully testable.

The plan follows the spec sequence:
  1. mine_until cargo_full
  2. travel to home_base
  3. dock
  4. sell_all_ore

If any precondition is unmet, returns Plan.failed(reason) with an empty
step list. The executor and the LLM can decide what to do from there.
"""

from __future__ import annotations

import logging

from app.skills.mining.schema import MiningState, Plan, Step

log = logging.getLogger(__name__)


def build_mining_plan(state: MiningState) -> Plan:
    """Build a mining plan from the current game state.

    Preconditions (checked in priority order):
      1. Ship has a mining laser installed.
      2. Ship is at a minable POI.
      3. Cargo has free space.

    Args:
        state: Snapshot of the relevant game state.

    Returns:
        A Plan with steps if all preconditions pass,
        or Plan.failed(reason) if any precondition is unmet.
    """
    log.info(
        "build_mining_plan: laser=%s at_minable=%s cargo=%d/%d home=%s",
        state.has_mining_laser,
        state.at_minable_poi,
        state.cargo_used,
        state.cargo_capacity,
        state.home_base_poi_id,
    )

    if not state.has_mining_laser:
        reason = "falta laser de mineracao instalado"
        log.info("build_mining_plan: precondition failed — %s", reason)
        return Plan.failed(reason)

    if not state.at_minable_poi:
        reason = "nave nao esta em ponto mineravel"
        log.info("build_mining_plan: precondition failed — %s", reason)
        return Plan.failed(reason)

    if state.cargo_full:
        reason = "cargo ja esta cheio — venda antes de minerar"
        log.info("build_mining_plan: precondition failed — %s", reason)
        return Plan.failed(reason)

    steps = [
        Step(op="mine_until", condition="cargo_full"),
        Step(op="travel", target=state.home_base_poi_id),
        Step(op="dock"),
        Step(op="sell_all_ore"),
    ]

    log.info("build_mining_plan: plan ready with %d steps", len(steps))
    return Plan(steps=steps)
