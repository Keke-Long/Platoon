from __future__ import annotations

import sys
from pathlib import Path

VERIFY_DIR = Path(__file__).resolve().parents[2] / "exhaustive_verification"
if str(VERIFY_DIR) not in sys.path:
    sys.path.insert(0, str(VERIFY_DIR))

from model import Instance  # noqa: E402
from scheduling_milp import solve_downstream_schedule, units_from_partition


def test_units_from_partition() -> None:
    units = units_from_partition(((2, 1), (1,)))
    assert [unit.vehicles for unit in units] == [((1, 1), (1, 2)), ((1, 3),), ((2, 1),)]


def test_downstream_schedule_tight_example() -> None:
    instance = Instance(counts=(1, 2), releases=((1,), (0, 3)), hF=1, hS=2)
    vehicle = solve_downstream_schedule(instance, ((1,), (1, 1)), time_limit=5)
    platoon = solve_downstream_schedule(instance, ((1,), (2,)), time_limit=5)
    assert vehicle.status == "OPTIMAL"
    assert platoon.status == "OPTIMAL"
    assert round(vehicle.objective_total_delay or -1) == 2
    assert round(platoon.objective_total_delay or -1) == 4


def test_platoon_internal_release_slack_does_not_delay_early_vehicles() -> None:
    instance = Instance(counts=(3,), releases=((0, 1, 3),), hF=1, hS=2)
    result = solve_downstream_schedule(instance, ((3,),), time_limit=5)
    assert result.status == "OPTIMAL"
    assert result.objective_total_delay is not None
    assert round(result.objective_total_delay) == 0
