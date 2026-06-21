"""Types for the mining skill.

No logic here — just data shapes.

Mapping to SpaceMolt get_status fields:
  MiningState.has_mining_laser  <- modules[] contains type "mining_laser"
  MiningState.cargo_used        <- cargo.used
  MiningState.cargo_capacity    <- cargo.capacity
  MiningState.at_minable_poi    <- location.poi.minable == true
  MiningState.home_base_poi_id  <- location.base_poi_id (last docked base)
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
    """Operation name. One of: mine_until, travel, dock, sell_all_ore."""

    target: str | None = None
    """POI id for the travel op; None for other ops."""

    condition: str | None = None
    """Loop condition for mine_until. Always 'cargo_full'."""


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
    """Number of mine() calls that succeeded."""

    ore_collected: int = 0
    """Total cargo units collected during this run."""

    credits_earned: float = 0.0
    """Credits received from selling the ore."""

    final_location: str = ""
    """POI id where the ship ended up."""

    failure_reason: str | None = None
    """Human-readable explanation when ok=False."""

    @classmethod
    def failed(cls, reason: str) -> "MiningResult":
        return cls(ok=False, failure_reason=reason)
