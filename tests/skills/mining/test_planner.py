"""Tests for mining/planner.py — build_mining_plan."""

import pytest
from app.skills.mining.planner import build_mining_plan
from app.skills.mining.schema import MiningState


def make_state(**overrides) -> MiningState:
    """Return a valid MiningState with all preconditions passing."""
    defaults = dict(
        has_mining_laser=True,
        cargo_used=0,
        cargo_capacity=100,
        at_minable_poi=True,
        home_base_poi_id="base-alpha",
        # Fuel fields — default 0 means fuel check is disabled
        fuel_current=0,
        fuel_capacity=100,
        fuel_per_jump_estimate=0,
        other_minable_poi_ids=[],
    )
    return MiningState(**{**defaults, **overrides})


class TestHappyPath:
    def test_plan_is_ok(self):
        plan = build_mining_plan(make_state())
        assert plan.ok is True

    def test_plan_has_four_steps(self):
        plan = build_mining_plan(make_state())
        assert len(plan.steps) == 4

    def test_first_step_is_mine_until_depleted_or_full(self):
        plan = build_mining_plan(make_state())
        step = plan.steps[0]
        assert step.op == "mine_until_depleted_or_full"

    def test_second_step_is_travel_to_home_base(self):
        plan = build_mining_plan(make_state(home_base_poi_id="station-7"))
        step = plan.steps[1]
        assert step.op == "travel"
        assert step.target == "station-7"

    def test_third_step_is_dock(self):
        plan = build_mining_plan(make_state())
        assert plan.steps[2].op == "dock"

    def test_fourth_step_is_sell_all_ore(self):
        plan = build_mining_plan(make_state())
        assert plan.steps[3].op == "sell_all_ore"

    def test_failure_reason_is_none_on_success(self):
        plan = build_mining_plan(make_state())
        assert plan.failure_reason is None


class TestPreconditions:
    def test_no_laser_returns_failed_plan(self):
        plan = build_mining_plan(make_state(has_mining_laser=False))
        assert plan.ok is False
        assert plan.steps == []

    def test_no_laser_reason_mentions_laser(self):
        plan = build_mining_plan(make_state(has_mining_laser=False))
        assert "laser" in plan.failure_reason.lower()

    def test_not_at_minable_poi_returns_failed_plan(self):
        plan = build_mining_plan(make_state(at_minable_poi=False))
        assert plan.ok is False
        assert plan.steps == []

    def test_not_at_minable_poi_reason_is_descriptive(self):
        plan = build_mining_plan(make_state(at_minable_poi=False))
        assert plan.failure_reason is not None
        assert len(plan.failure_reason) > 0

    def test_cargo_full_returns_failed_plan(self):
        plan = build_mining_plan(make_state(cargo_used=100, cargo_capacity=100))
        assert plan.ok is False
        assert plan.steps == []

    def test_cargo_full_reason_mentions_cargo(self):
        plan = build_mining_plan(make_state(cargo_used=100, cargo_capacity=100))
        assert "cargo" in plan.failure_reason.lower()

    def test_laser_check_has_priority_over_poi(self):
        """Without laser AND not at minable POI: reason must mention laser."""
        plan = build_mining_plan(make_state(has_mining_laser=False, at_minable_poi=False))
        assert "laser" in plan.failure_reason.lower()

    def test_partial_cargo_is_valid(self):
        plan = build_mining_plan(make_state(cargo_used=99, cargo_capacity=100))
        assert plan.ok is True


class TestFuelPrecondition:
    def test_fuel_zero_estimate_skips_fuel_check(self):
        """fuel_per_jump_estimate=0 → fuel check disabled, plan passes."""
        plan = build_mining_plan(make_state(fuel_current=0, fuel_per_jump_estimate=0))
        assert plan.ok is True

    def test_sufficient_fuel_passes(self):
        plan = build_mining_plan(make_state(
            fuel_current=50,
            fuel_per_jump_estimate=10,  # need 20, have 50
        ))
        assert plan.ok is True

    def test_exactly_minimum_fuel_passes(self):
        """fuel_current == fuel_per_jump_estimate * 2 should pass."""
        plan = build_mining_plan(make_state(
            fuel_current=20,
            fuel_per_jump_estimate=10,
        ))
        assert plan.ok is True

    def test_low_fuel_returns_failed_plan(self):
        plan = build_mining_plan(make_state(
            fuel_current=5,
            fuel_per_jump_estimate=10,  # need 20, have only 5
        ))
        assert plan.ok is False
        assert plan.steps == []

    def test_low_fuel_reason_mentions_fuel(self):
        plan = build_mining_plan(make_state(
            fuel_current=5,
            fuel_per_jump_estimate=10,
        ))
        assert "fuel" in plan.failure_reason.lower()

    def test_fuel_check_before_laser_check(self):
        """Low fuel should be reported before missing laser."""
        plan = build_mining_plan(make_state(
            has_mining_laser=False,
            fuel_current=0,
            fuel_per_jump_estimate=10,
        ))
        # Low fuel fires before laser check
        assert plan.ok is False
        assert "fuel" in plan.failure_reason.lower()
