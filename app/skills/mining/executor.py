"""Mining executor: runs a Plan step-by-step against the game.

Receives a Plan and a GameClient (injected). Returns a MiningResult.

The key step is mine_until: it loops calling game_client.mine() and
after each call checks if cargo is full. It also enforces a hard cap
on iterations so the loop can never run forever if something breaks.
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
    ore_before = 0  # tracked via cargo readings from mine responses
    credits_earned = 0.0
    final_location = ""

    for step in plan.steps:
        log.info("run_mining_plan: executing step op=%s target=%s", step.op, step.target)

        if step.op == "mine_until":
            cycles, ore_before = await _mine_until_full(client)

        elif step.op == "travel":
            await client.call("spacemolt", action="travel", id=step.target)
            final_location = step.target or ""

        elif step.op == "dock":
            await client.call("spacemolt", action="dock")

        elif step.op == "sell_all_ore":
            credits_earned = await _sell_all_ore(client)

        else:
            log.warning("run_mining_plan: unknown op=%s — skipping", step.op)

    log.info(
        "run_mining_plan: done. cycles=%d ore=%d credits=%.2f location=%s",
        cycles, ore_before, credits_earned, final_location,
    )

    return MiningResult(
        ok=True,
        cycles=cycles,
        ore_collected=ore_before,
        credits_earned=credits_earned,
        final_location=final_location,
    )


async def _mine_until_full(client: GameClient) -> tuple[int, int]:
    """Call mine() in a loop until cargo is full or safety cap is reached.

    Returns:
        (cycles, total_ore_collected)
    """
    cycles = 0
    ore_collected = 0

    for _ in range(_MINE_LOOP_MAX):
        response = await client.call("spacemolt", action="mine")
        cycles += 1

        # Parse the response to check cargo status and ore collected.
        # The game returns a dict; we extract what we can defensively.
        if isinstance(response, dict):
            ore_this_cycle = int(response.get("quantity", 0))
            ore_collected += ore_this_cycle
            cargo_used = int(response.get("cargo_used", -1))
            cargo_capacity = int(response.get("cargo_capacity", -1))

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

    return cycles, ore_collected


async def _sell_all_ore(client: GameClient) -> float:
    """Sell all ore in cargo.

    For now calls sell with item_id='ore' and a large quantity.
    The game handles the actual amount in cargo.

    Returns:
        Credits earned (float), or 0.0 if the response can't be parsed.
    """
    response = await client.call("spacemolt", action="sell", id="ore", quantity=9999)

    if isinstance(response, dict):
        credits = float(response.get("credits_earned", 0.0))
        log.info("sell_all_ore: earned %.2f credits", credits)
        return credits

    log.info("sell_all_ore: response=%r (stub or unexpected)", response)
    return 0.0
