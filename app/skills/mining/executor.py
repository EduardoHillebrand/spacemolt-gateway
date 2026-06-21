"""Mining executor: runs a Plan step-by-step against the game.

Receives a Plan and a GameClient (injected). Returns a MiningResult.

The key step is mine_until: it loops calling game_client.mine() and
after each call checks if cargo is full. It also enforces a hard cap
on iterations so the loop can never run forever if something breaks.

SpaceMolt response format (actions return nested JSON):
  mine  -> {"details": {"quantity": N}, "ship": {"cargo_used": X, "cargo_capacity": Y},
             "cargo": [{"item_id": "...", "quantity": N, "size": S}, ...]}
  sell  -> {"details": {"total_earned": F, "quantity_sold": N, ...}}
"""

from __future__ import annotations

import logging

from app.game_client import GameClient
from app.skills.mining.schema import MiningResult, Plan

log = logging.getLogger(__name__)

_MINE_LOOP_MAX = 200  # safety cap: never mine more than this many times


async def run_mining_plan(plan: Plan, client: GameClient) -> MiningResult:
    """Execute a mining plan step by step.

    Args:
        plan:   Built by build_mining_plan(). If plan.ok is False, returns
                MiningResult.failed immediately.
        client: GameClient for all game calls.

    Returns:
        MiningResult with statistics about the run.
    """
    if not plan.ok:
        log.info("run_mining_plan: plan not ok — %s", plan.failure_reason)
        return MiningResult.failed(plan.failure_reason or "plano invalido")

    cycles = 0
    ore_collected = 0
    cargo_items: list[dict] = []
    credits_earned = 0.0
    final_location = ""

    for step in plan.steps:
        log.info("run_mining_plan: executing step op=%s target=%s", step.op, step.target)

        if step.op == "mine_until":
            cycles, ore_collected, cargo_items = await _mine_until_full(client)

        elif step.op == "travel":
            await client.call("spacemolt", action="travel", id=step.target)
            final_location = step.target or ""

        elif step.op == "dock":
            await client.call("spacemolt", action="dock")

        elif step.op == "sell_all_ore":
            credits_earned = await _sell_all_ore(client, cargo_items)

        else:
            log.warning("run_mining_plan: unknown op=%s — skipping", step.op)

    log.info(
        "run_mining_plan: done. cycles=%d ore=%d credits=%.2f location=%s",
        cycles, ore_collected, credits_earned, final_location,
    )

    return MiningResult(
        ok=True,
        cycles=cycles,
        ore_collected=ore_collected,
        credits_earned=credits_earned,
        final_location=final_location,
    )


async def _mine_until_full(client: GameClient) -> tuple[int, int, list[dict]]:
    """Call mine() in a loop until cargo is full or safety cap is reached.

    SpaceMolt mine response format:
        {
            "details": {"quantity": N, ...},
            "ship": {"cargo_used": X, "cargo_capacity": Y, ...},
            "cargo": [{"item_id": "...", "quantity": N, "size": S}, ...]
        }

    Returns:
        (cycles, total_ore_collected, final_cargo_items)
    """
    cycles = 0
    ore_collected = 0
    cargo_items: list[dict] = []

    for _ in range(_MINE_LOOP_MAX):
        response = await client.call("spacemolt", action="mine")
        cycles += 1

        if isinstance(response, dict):
            details = response.get("details") or {}
            ship = response.get("ship") or {}

            ore_this_cycle = int(details.get("quantity", 0))
            ore_collected += ore_this_cycle

            cargo_used = int(ship.get("cargo_used", -1))
            cargo_capacity = int(ship.get("cargo_capacity", -1))

            # Update cargo item list from the mine response
            raw_cargo = response.get("cargo")
            if isinstance(raw_cargo, list):
                cargo_items = raw_cargo

            log.info(
                "mine_until: cycle %d — ore_this=%d cargo=%d/%d",
                cycles, ore_this_cycle, cargo_used, cargo_capacity,
            )

            if cargo_used >= cargo_capacity > 0:
                log.info("mine_until: cargo full after %d cycles", cycles)
                break
        else:
            # Stub or unexpected format — log and keep going until cap
            log.info("mine_until: cycle %d — response=%r", cycles, response)

    else:
        log.warning("mine_until: hit safety cap of %d iterations", _MINE_LOOP_MAX)

    return cycles, ore_collected, cargo_items


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
