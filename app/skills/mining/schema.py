"""Types for the mining skill.

No logic here — just data shapes.

Mapping to SpaceMolt get_status fields:
  MiningState.has_mining_laser      <- modules[] contains type "mining_laser"
  MiningState.cargo_used            <- cargo.used
  MiningState.cargo_capacity        <- cargo.capacity
  MiningState.at_minable_poi        <- location.poi.minable == true
  MiningState.home_base_poi_id      <- location.base_poi_id (last docked base)
  MiningState.fuel_current          <- ship.fuel_current / Fuel: X/Y
  MiningState.fuel_capacity         <- ship.fuel_capacity / Fuel: X/Y
  MiningState.fuel_per_jump_estimate <- conservative cost of one travel
  MiningState.other_minable_poi_ids  <- system.pois where minable=true
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Input: what we read from the game before building the plan
# ---------------------------------------------------------------------------

@dataclass
class MiningState:
    """Snapshot of game state relevant to mining."""

    has_mining_laser: bool
    """True if a mining laser module is installed and functional."""

    cargo_used: int
    """Current cargo units occupied."""

    cargo_capacity: int
    """Maximum cargo capacity in units."""

    at_minable_poi: bool
    """True if the ship is at a POI where mining is possible."""

    home_base_poi_id: str
    """POI id of the base to return to for selling (last docked station)."""

    # --- Resilience fields (0006) ---

    fuel_current: int = 0
    """Current fuel units. 0 = unknown (fuel check skipped)."""

    fuel_capacity: int = 100
    """Maximum fuel capacity."""

    fuel_per_jump_estimate: int = 0
    """Conservative fuel cost per travel/jump. 0 = disable fuel checks."""

    other_minable_poi_ids: list[str] = field(default_factory=list)
    """POI ids of other minable locations in the same system (for relocation)."""

    @property
    def cargo_free(self) -> int:
        return self.cargo_capacity - self.cargo_used

    @property
    def cargo_full(self) -> bool:
        return self.cargo_used >= self.cargo_capacity


# ---------------------------------------------------------------------------
# Plan: the sequence of steps decided by the planner
# ---------------------------------------------------------------------------

@dataclass
class Step:
    """One step in the mining plan."""

    op: str
    """Operation name.

    One of:
      mine_until_depleted_or_full  -- mine loop with depletion/relocation/survey
      survey_system                -- scan for hidden deposits
      travel                       -- move to a POI
      dock                         -- dock at current station
      sell_all_ore                 -- sell all tracked cargo items
    """

    target: str | None = None
    """POI id for the travel op; None for other ops."""

    condition: str | None = None
    """Legacy field kept for backward compatibility."""


@dataclass
class Plan:
    """A list of steps to execute, or an empty plan with a failure reason."""

    steps: list[Step] = field(default_factory=list)
    ok: bool = True
    failure_reason: str | None = None

    @classmethod
    def failed(cls, reason: str) -> "Plan":
        """Create a plan that was rejected at the precondition check."""
        return cls(steps=[], ok=False, failure_reason=reason)


# ---------------------------------------------------------------------------
# Result: what the executor reports after running the plan
# ---------------------------------------------------------------------------

@dataclass
class MiningResult:
    """Outcome of a completed (or aborted) mining run."""

    ok: bool
    """False if a precondition failed or the run was aborted."""

    cycles: int = 0
    """Number of mine() calls that extracted ore > 0."""

    ore_collected: int = 0
    """Total cargo units collected during this run."""

    credits_earned: float = 0.0
    """Credits received from selling the ore."""

    final_location: str = ""
    """POI id where the ship ended up."""

    failure_reason: str | None = None
    """Human-readable explanation when ok=False."""

    # --- Resilience fields (0006) ---

    relocations: int = 0
    """Number of times the ship moved to a different POI due to depletion."""

    surveys: int = 0
    """Number of survey_system calls made to look for hidden deposits."""

    stop_reason: str = "cargo_full"
    """Why the mining loop ended: 'cargo_full' | 'system_depleted' | 'low_fuel'."""

    @classmethod
    def failed(cls, reason: str) -> "MiningResult":
        return cls(ok=False, failure_reason=reason)
