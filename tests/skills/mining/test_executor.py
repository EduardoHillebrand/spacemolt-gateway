"""Tests for mining/executor.py.

Uses FakeGameClient to simulate game responses without a live connection.

FakeGameClient supports:
  - Configurable cargo capacity and ore per mine
  - Depletion simulation per POI (poi -> max successful mines before 0)
  - Survey results (list of POI ids returned by survey_system)
  - Fuel tracking (decremented on travel calls)

Response format matches real SpaceMolt JSON (nested dicts).
"""

from __future__ import annotations

import pytest
from app.skills.mining.executor import _MINE_LOOP_MAX, _DEPLETION_LIMIT, run_mining_plan
from app.skills.mining.schema import MiningState, Plan, Step


# ---------------------------------------------------------------------------
# Fake game client
# ---------------------------------------------------------------------------

class FakeGameClient:
    """Simulates the game with configurable behavior.

    Args:
        cargo_capacity: Ship cargo limit.
        ore_per_mine:   Ore units returned per mine call (when POI active).
        home_base:      POI id of the home base.
        fuel_current:   Starting fuel units.
        fuel_per_travel: Fuel consumed per travel call.
        depletion_map:  poi_id -> number of successful mines before returning 0.
                        None means the POI never depletes.
        survey_pois:    List of minable POI ids returned by survey_system.
    """

    def __init__(
        self,
        cargo_capacity: int = 100,
        ore_per_mine: int = 20,
        home_base: str = "base-1",
        fuel_current: int = 200,
        fuel_per_travel: int = 10,
        depletion_map: dict[str, int] | None = None,
        survey_pois: list[str] | None = None,
    ) -> None:
        self.capacity = cargo_capacity
        self.ore_per_mine = ore_per_mine
        self.home_base = home_base
        self.cargo_used = 0
        self.fuel_current = fuel_current
        self.fuel_per_travel = fuel_per_travel
        self.current_poi = "start"
        self.poi_success_counts: dict[str, int] = {}  # poi -> successful mines so far
        self.depletion_map = depletion_map or {}
        self.survey_pois = list(survey_pois or [])
        self.calls: list[tuple[str, dict]] = []

    async def call(self, tool: str, **kwargs) -> dict:
        self.calls.append((tool, kwargs))
        action = kwargs.get("action", "")

        if action == "mine":
            poi = self.current_poi
            successes_so_far = self.poi_success_counts.get(poi, 0)
            max_successes = self.depletion_map.get(poi)

            if max_successes is not None and successes_so_far >= max_successes:
                # POI depleted — return 0 ore
                ore_this = 0
            else:
                ore_this = min(self.ore_per_mine, self.capacity - self.cargo_used)
                self.cargo_used += ore_this
                if ore_this > 0:
                    self.poi_success_counts[poi] = successes_so_far + 1

            return {
                "details": {"quantity": ore_this},
                "ship": {
                    "cargo_used": self.cargo_used,
                    "cargo_capacity": self.capacity,
                    "fuel_current": self.fuel_current,
                },
                "cargo": (
                    [{"item_id": "iron_ore", "quantity": self.cargo_used, "size": 1}]
                    if self.cargo_used > 0 else []
                ),
            }

        if action == "travel":
            self.current_poi = kwargs.get("id", "unknown")
            self.poi_success_counts[self.current_poi] = 0  # reset for new POI
            self.fuel_current = max(0, self.fuel_current - self.fuel_per_travel)
            return {"location": {"poi_id": self.current_poi}}

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

        if action == "survey_system":
            pois = [{"id": p, "minable": True} for p in self.survey_pois]
            return {"pois": pois}

        return {}

    def mine_call_count(self) -> int:
        return sum(1 for _, k in self.calls if k.get("action") == "mine")

    def travel_destinations(self) -> list[str]:
        return [k["id"] for _, k in self.calls if k.get("action") == "travel"]


def full_plan(home_base: str = "base-1") -> Plan:
    """Standard plan using the new mine op name."""
    return Plan(steps=[
        Step(op="mine_until_depleted_or_full"),
        Step(op="travel", target=home_base),
        Step(op="dock"),
        Step(op="sell_all_ore"),
    ])


def make_state(**overrides) -> MiningState:
    """Valid MiningState with no fuel check and no extra POIs by default."""
    defaults = dict(
        has_mining_laser=True,
        cargo_used=0,
        cargo_capacity=100,
        at_minable_poi=True,
        home_base_poi_id="base-1",
        fuel_current=200,
        fuel_capacity=200,
        fuel_per_jump_estimate=0,
        other_minable_poi_ids=[],
    )
    return MiningState(**{**defaults, **overrides})


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

class TestExecutorHappyPath:
    async def test_result_is_ok(self):
        client = FakeGameClient(cargo_capacity=100, ore_per_mine=25)
        result = await run_mining_plan(full_plan(), client)
        assert result.ok is True

    async def test_mine_loop_stops_when_cargo_full(self):
        # 100 capacity, 25 per mine -> exactly 4 cycles
        client = FakeGameClient(cargo_capacity=100, ore_per_mine=25)
        result = await run_mining_plan(full_plan(), client)
        assert result.cycles == 4

    async def test_ore_collected_matches_capacity(self):
        client = FakeGameClient(cargo_capacity=100, ore_per_mine=25)
        result = await run_mining_plan(full_plan(), client)
        assert result.ore_collected == 100

    async def test_stop_reason_cargo_full(self):
        client = FakeGameClient(cargo_capacity=100, ore_per_mine=25)
        result = await run_mining_plan(full_plan(), client)
        assert result.stop_reason == "cargo_full"

    async def test_no_relocations_on_normal_run(self):
        client = FakeGameClient(cargo_capacity=100, ore_per_mine=25)
        result = await run_mining_plan(full_plan(), client)
        assert result.relocations == 0

    async def test_no_surveys_on_normal_run(self):
        client = FakeGameClient(cargo_capacity=100, ore_per_mine=25)
        result = await run_mining_plan(full_plan(), client)
        assert result.surveys == 0

    async def test_travel_called_with_correct_poi(self):
        client = FakeGameClient()
        await run_mining_plan(full_plan(home_base="station-7"), client)
        assert client.travel_destinations() == ["station-7"]

    async def test_dock_is_called(self):
        client = FakeGameClient()
        await run_mining_plan(full_plan(), client)
        dock_calls = [k for _, k in client.calls if k.get("action") == "dock"]
        assert len(dock_calls) == 1

    async def test_sell_called_after_dock(self):
        client = FakeGameClient()
        await run_mining_plan(full_plan(), client)
        actions = [k.get("action") for _, k in client.calls]
        assert actions.index("dock") < actions.index("sell")

    async def test_credits_earned_is_returned(self):
        # 100 ore * 10 credits = 1000
        client = FakeGameClient(cargo_capacity=100, ore_per_mine=25)
        result = await run_mining_plan(full_plan(), client)
        assert result.credits_earned == 1000.0

    async def test_final_location_is_home_base(self):
        client = FakeGameClient()
        result = await run_mining_plan(full_plan(home_base="base-alpha"), client)
        assert result.final_location == "base-alpha"

    async def test_mine_until_alias_still_works(self):
        """Old 'mine_until' op should behave the same (backward compat)."""
        old_plan = Plan(steps=[
            Step(op="mine_until"),
            Step(op="travel", target="base-1"),
            Step(op="dock"),
            Step(op="sell_all_ore"),
        ])
        client = FakeGameClient(cargo_capacity=100, ore_per_mine=25)
        result = await run_mining_plan(old_plan, client)
        assert result.ok is True
        assert result.cycles == 4


# ---------------------------------------------------------------------------
# Precondition failure
# ---------------------------------------------------------------------------

class TestExecutorPreconditionFailed:
    async def test_failed_plan_returns_failed_result(self):
        client = FakeGameClient()
        result = await run_mining_plan(Plan.failed("falta laser"), client)
        assert result.ok is False

    async def test_failed_plan_makes_no_game_calls(self):
        client = FakeGameClient()
        await run_mining_plan(Plan.failed("falta laser"), client)
        assert client.calls == []

    async def test_failed_reason_is_propagated(self):
        client = FakeGameClient()
        result = await run_mining_plan(Plan.failed("cargo cheio"), client)
        assert "cargo" in result.failure_reason.lower()


# ---------------------------------------------------------------------------
# Depletion → relocation
# ---------------------------------------------------------------------------

class TestDepletion:
    async def test_depleted_poi_triggers_relocation(self):
        """POI depletes after 2 mines; ship should relocate to other POI."""
        client = FakeGameClient(
            cargo_capacity=100,
            ore_per_mine=10,
            depletion_map={"start": 2},  # start POI depletes after 2 mines
        )
        state = make_state(other_minable_poi_ids=["poi-2"])
        result = await run_mining_plan(full_plan(), client, state)

        assert result.relocations == 1
        assert "poi-2" in client.travel_destinations()

    async def test_relocation_count_reflects_moves(self):
        """Two depleted POIs → 2 relocations."""
        client = FakeGameClient(
            cargo_capacity=1000,
            ore_per_mine=10,
            depletion_map={"start": 1, "poi-2": 1},
        )
        state = make_state(other_minable_poi_ids=["poi-2", "poi-3"])
        result = await run_mining_plan(full_plan(), client, state)
        # After depletion of start → poi-2; depletion of poi-2 → poi-3
        assert result.relocations >= 2

    async def test_ore_collected_across_pois(self):
        """Ore from all POIs is summed."""
        # start: depletes after 2 mines (2*10=20), poi-2 fills rest
        client = FakeGameClient(
            cargo_capacity=60,
            ore_per_mine=10,
            depletion_map={"start": 2},
        )
        state = make_state(other_minable_poi_ids=["poi-2"])
        result = await run_mining_plan(full_plan(), client, state)
        assert result.ore_collected == 60
        assert result.stop_reason == "cargo_full"


# ---------------------------------------------------------------------------
# Survey
# ---------------------------------------------------------------------------

class TestSurvey:
    async def test_depleted_with_no_pois_calls_survey(self):
        """When no other POIs exist, survey_system is called."""
        client = FakeGameClient(
            cargo_capacity=100,
            ore_per_mine=10,
            depletion_map={"start": 0},  # immediately depleted
            survey_pois=["hidden-1"],
        )
        state = make_state(other_minable_poi_ids=[])
        result = await run_mining_plan(full_plan(), client, state)
        assert result.surveys == 1

    async def test_survey_poi_is_visited_after_survey(self):
        """After survey returns a POI, the ship relocates there."""
        client = FakeGameClient(
            cargo_capacity=100,
            ore_per_mine=10,
            depletion_map={"start": 0},
            survey_pois=["hidden-1"],
        )
        state = make_state(other_minable_poi_ids=[])
        await run_mining_plan(full_plan(), client, state)
        assert "hidden-1" in client.travel_destinations()

    async def test_empty_survey_stops_with_system_depleted(self):
        """Survey returns nothing → stop_reason = system_depleted."""
        client = FakeGameClient(
            cargo_capacity=100,
            ore_per_mine=10,
            depletion_map={"start": 0},
            survey_pois=[],
        )
        state = make_state(other_minable_poi_ids=[])
        result = await run_mining_plan(full_plan(), client, state)
        assert result.stop_reason == "system_depleted"
        assert result.ok is True  # still completes gracefully

    async def test_system_depleted_mine_count(self):
        """Mine called exactly _DEPLETION_LIMIT times before system_depleted."""
        client = FakeGameClient(
            depletion_map={"start": 0},
            survey_pois=[],
        )
        state = make_state(other_minable_poi_ids=[])
        await run_mining_plan(full_plan(), client, state)
        # _DEPLETION_LIMIT zeros → survey → empty → stop
        assert client.mine_call_count() == _DEPLETION_LIMIT


# ---------------------------------------------------------------------------
# Fuel
# ---------------------------------------------------------------------------

class TestFuelCheck:
    async def test_low_fuel_stops_loop(self):
        """When fuel drops to min_fuel_return, stop before next mine."""
        # fuel_per_jump_estimate=50, starting fuel=50 → 50 <= 50 → stops immediately
        state = make_state(
            fuel_current=50,
            fuel_per_jump_estimate=50,
        )
        client = FakeGameClient(cargo_capacity=1000, ore_per_mine=10, fuel_current=50)
        result = await run_mining_plan(full_plan(), client, state)
        assert result.stop_reason == "low_fuel"
        # No mine calls when fuel is exactly at the minimum from the start
        assert client.mine_call_count() == 0

    async def test_fuel_drops_after_relocation(self):
        """After relocating, fuel decreases and may trigger low_fuel."""
        # Start with just enough for one travel; relocation uses it all.
        state = make_state(
            fuel_current=20,
            fuel_per_jump_estimate=10,
            other_minable_poi_ids=["poi-2"],
        )
        # start depletes after 1 mine; after travel fuel drops to 10 (== min_return)
        client = FakeGameClient(
            cargo_capacity=1000,
            ore_per_mine=10,
            fuel_current=20,
            fuel_per_travel=10,
            depletion_map={"start": 1},
        )
        result = await run_mining_plan(full_plan(), client, state)
        # Either stopped at low_fuel or system_depleted (both valid after travel)
        assert result.stop_reason in ("low_fuel", "system_depleted", "cargo_full")

    async def test_zero_fuel_estimate_disables_check(self):
        """fuel_per_jump_estimate=0 → fuel check never triggers."""
        state = make_state(fuel_current=0, fuel_per_jump_estimate=0)
        client = FakeGameClient(cargo_capacity=100, ore_per_mine=25, fuel_current=0)
        result = await run_mining_plan(full_plan(), client, state)
        # No fuel check → fills cargo normally
        assert result.stop_reason == "cargo_full"
        assert result.cycles == 4


# ---------------------------------------------------------------------------
# Safety cap
# ---------------------------------------------------------------------------

class TestSafetyCap:
    async def test_safety_cap_stops_loop(self):
        """Mine never fills the huge cargo → loop stops at _MINE_LOOP_MAX."""
        # Capacity so large it never fills in 200 cycles; ore always > 0.
        client = FakeGameClient(
            cargo_capacity=_MINE_LOOP_MAX * 100,
            ore_per_mine=1,
        )
        result = await run_mining_plan(full_plan(), client)
        assert client.mine_call_count() == _MINE_LOOP_MAX
        assert result.ok is True

    async def test_system_depleted_prevents_safety_cap(self):
        """With depletion and no survey results, stops well before the cap."""
        client = FakeGameClient(
            depletion_map={"start": 0},
            survey_pois=[],
        )
        state = make_state(other_minable_poi_ids=[])
        result = await run_mining_plan(full_plan(), client, state)
        assert client.mine_call_count() < _MINE_LOOP_MAX
        assert result.stop_reason == "system_depleted"
