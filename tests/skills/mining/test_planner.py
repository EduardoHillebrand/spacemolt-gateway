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
    )
    return MiningState(**{**defaults, **overrides})


class TestHappyPath:
    def test_plan_is_ok(self):
        plan = build_mining_plan(make_state())
        assert plan.ok is True

    def test_plan_has_four_steps(self):
        plan = build_mining_plan(make_state())
        assert len(plan.steps) == 4

    def test_first_step_is_mine_until_cargo_full(self):
        plan = build_mining_plan(make_state())
        step = plan.steps[0]
        assert step.op == "mine_until"
        assert step.condition == "cargo_full"

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
        """Cargo that's not full should not block the plan."""
        plan = build_mining_plan(make_state(cargo_used=99, cargo_capacity=100))
        assert plan.ok is True
