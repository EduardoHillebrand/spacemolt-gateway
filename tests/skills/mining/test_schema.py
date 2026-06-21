"""Minimal type tests for mining/schema.py."""

from app.skills.mining.schema import MiningState, Step, Plan, MiningResult


class TestMiningState:
    def test_cargo_free(self):
        s = MiningState(
            has_mining_laser=True,
            cargo_used=30,
            cargo_capacity=100,
            at_minable_poi=True,
            home_base_poi_id="base-1",
        )
        assert s.cargo_free == 70

    def test_cargo_full_when_at_capacity(self):
        s = MiningState(
            has_mining_laser=True,
            cargo_used=100,
            cargo_capacity=100,
            at_minable_poi=True,
            home_base_poi_id="base-1",
        )
        assert s.cargo_full is True

    def test_cargo_not_full_when_space_remains(self):
        s = MiningState(
            has_mining_laser=True,
            cargo_used=99,
            cargo_capacity=100,
            at_minable_poi=True,
            home_base_poi_id="base-1",
        )
        assert s.cargo_full is False


class TestPlan:
    def test_failed_plan_is_not_ok(self):
        plan = Plan.failed("falta laser de mineracao")
        assert plan.ok is False
        assert plan.steps == []
        assert "laser" in plan.failure_reason

    def test_default_plan_is_ok(self):
        plan = Plan(steps=[Step(op="mine_until", condition="cargo_full")])
        assert plan.ok is True


class TestMiningResult:
    def test_failed_result(self):
        result = MiningResult.failed("nao ha laser")
        assert result.ok is False
        assert result.cycles == 0
        assert result.credits_earned == 0.0

    def test_successful_result(self):
        result = MiningResult(ok=True, cycles=5, ore_collected=50, credits_earned=1500.0, final_location="base-1")
        assert result.ok is True
        assert result.ore_collected == 50
