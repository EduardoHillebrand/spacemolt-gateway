"""Tests for mining/executor.py.

Uses FakeGameClient to simulate cargo filling up without a live game.

FakeGameClient mirrors the real SpaceMolt response format:
  mine  -> {"details": {"quantity": N}, "ship": {"cargo_used": X, "cargo_capacity": Y},
             "cargo": [{"item_id": "iron_ore", "quantity": N, "size": 1}]}
  sell  -> {"details": {"total_earned": F, "quantity_sold": N, "unsold": 0}}
"""

from __future__ import annotations

import pytest
from app.skills.mining.executor import run_mining_plan, _MINE_LOOP_MAX
from app.skills.mining.schema import MiningState, Plan, Step


# ---------------------------------------------------------------------------
# Fake game client
# ---------------------------------------------------------------------------

class FakeGameClient:
    """Simulates the game: cargo fills after a set number of mine calls.

    Response format matches real SpaceMolt JSON (nested dicts).
    """

    def __init__(
        self,
        cargo_capacity: int = 100,
        ore_per_mine: int = 20,
        home_base: str = "base-1",
    ) -> None:
        self.capacity = cargo_capacity
        self.ore_per_mine = ore_per_mine
        self.home_base = home_base
        self.cargo_used = 0
        self.calls: list[tuple[str, dict]] = []

    async def call(self, tool: str, **kwargs) -> dict:
        self.calls.append((tool, kwargs))
        action = kwargs.get("action", "")

        if action == "mine":
            added = min(self.ore_per_mine, self.capacity - self.cargo_used)
            self.cargo_used += added
            return {
                "details": {"quantity": added},
                "ship": {
                    "cargo_used": self.cargo_used,
                    "cargo_capacity": self.capacity,
                },
                "cargo": [
                    {"item_id": "iron_ore", "quantity": self.cargo_used, "size": 1}
                ],
            }

        if action == "travel":
            return {"location": {"poi_id": kwargs.get("id", "")}}

        if action == "dock":
            return {"details": {"action": "dock"}}

        if action == "sell":
            sold = self.cargo_used
            credits = float(sold * 10)
            self.cargo_used = 0
            return {
                "details": {
                    "total_earned": credits,
                    "quantity_sold": sold,
                    "unsold": 0,
                }
            }

        return {}


def full_plan(home_base: str = "base-1") -> Plan:
    return Plan(steps=[
        Step(op="mine_until", condition="cargo_full"),
        Step(op="travel", target=home_base),
        Step(op="dock"),
        Step(op="sell_all_ore"),
    ])


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestExecutorHappyPath:
    async def test_result_is_ok(self):
        client = FakeGameClient(cargo_capacity=100, ore_per_mine=25)
        result = await run_mining_plan(full_plan(), client)
        assert result.ok is True

    async def test_mine_loop_stops_when_cargo_full(self):
        # 100 capacity, 25 per mine -> needs exactly 4 cycles
        client = FakeGameClient(cargo_capacity=100, ore_per_mine=25)
        result = await run_mining_plan(full_plan(), client)
        assert result.cycles == 4

    async def test_ore_collected_matches_capacity(self):
        client = FakeGameClient(cargo_capacity=100, ore_per_mine=25)
        result = await run_mining_plan(full_plan(), client)
        assert result.ore_collected == 100

    async def test_travel_is_called_with_correct_poi(self):
        client = FakeGameClient()
        await run_mining_plan(full_plan(home_base="station-7"), client)
        travel_calls = [(t, k) for t, k in client.calls if k.get("action") == "travel"]
        assert len(travel_calls) == 1
        assert travel_calls[0][1]["id"] == "station-7"

    async def test_dock_is_called(self):
        client = FakeGameClient()
        await run_mining_plan(full_plan(), client)
        dock_calls = [k for _, k in client.calls if k.get("action") == "dock"]
        assert len(dock_calls) == 1

    async def test_sell_is_called_after_dock(self):
        client = FakeGameClient()
        await run_mining_plan(full_plan(), client)
        actions = [k.get("action") for _, k in client.calls]
        dock_idx = actions.index("dock")
        sell_idx = actions.index("sell")
        assert sell_idx > dock_idx

    async def test_credits_earned_is_returned(self):
        # 100 ore * 10 credits each = 1000
        client = FakeGameClient(cargo_capacity=100, ore_per_mine=25)
        result = await run_mining_plan(full_plan(), client)
        assert result.credits_earned == 1000.0

    async def test_final_location_is_home_base(self):
        client = FakeGameClient()
        result = await run_mining_plan(full_plan(home_base="base-alpha"), client)
        assert result.final_location == "base-alpha"


class TestExecutorPreconditionFailed:
    async def test_failed_plan_returns_failed_result(self):
        client = FakeGameClient()
        failed = Plan.failed("falta laser")
        result = await run_mining_plan(failed, client)
        assert result.ok is False

    async def test_failed_plan_makes_no_game_calls(self):
        client = FakeGameClient()
        await run_mining_plan(Plan.failed("falta laser"), client)
        assert client.calls == []

    async def test_failed_reason_is_propagated(self):
        client = FakeGameClient()
        result = await run_mining_plan(Plan.failed("cargo cheio"), client)
        assert "cargo" in result.failure_reason.lower()


class TestExecutorSafetyCap:
    async def test_loop_stops_at_safety_cap_when_cargo_never_fills(self):
        """Simulate a broken mine() that never fills the cargo."""
        class NeverFillsClient(FakeGameClient):
            async def call(self, tool, **kwargs):
                self.calls.append((tool, kwargs))
                if kwargs.get("action") == "mine":
                    # Always returns 0 ore -- cargo never fills
                    return {
                        "details": {"quantity": 0},
                        "ship": {"cargo_used": 0, "cargo_capacity": 100},
                        "cargo": [],
                    }
                return await super().call(tool, **kwargs)

        client = NeverFillsClient()
        result = await run_mining_plan(full_plan(), client)
        mine_calls = sum(1 for _, k in client.calls if k.get("action") == "mine")
        assert mine_calls == _MINE_LOOP_MAX
        assert result.ok is True  # still completes, just capped
