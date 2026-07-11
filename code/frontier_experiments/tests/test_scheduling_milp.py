from __future__ import annotations

import sys
import unittest
from pathlib import Path

VERIFY_DIR = Path(__file__).resolve().parents[2] / "exhaustive_verification"
if str(VERIFY_DIR) not in sys.path:
    sys.path.insert(0, str(VERIFY_DIR))

from model import Instance  # noqa: E402
from scheduling_milp import solve_downstream_schedule, units_from_partition
from enumerate_partitions import enumerate_partitions  # noqa: E402
from enumerate_sequences import enumerate_platoon_sequences  # noqa: E402
from model import optimum_for_sequences  # noqa: E402


def require_gurobi_runtime() -> None:
    try:
        import gurobipy as gp
    except ModuleNotFoundError as exc:
        raise unittest.SkipTest("gurobipy is not installed") from exc
    try:
        env = gp.Env(empty=True)
        env.setParam("OutputFlag", 0)
        env.start()
        env.dispose()
    except gp.GurobiError as exc:
        raise unittest.SkipTest(f"Gurobi runtime unavailable: {exc}") from exc


def test_units_from_partition() -> None:
    units = units_from_partition(((2, 1), (1,)))
    assert [unit.vehicles for unit in units] == [((1, 1), (1, 2)), ((1, 3),), ((2, 1),)]


def test_downstream_schedule_tight_example() -> None:
    require_gurobi_runtime()
    instance = Instance(counts=(1, 2), releases=((1,), (0, 3)), hF=1, hS=2)
    vehicle = solve_downstream_schedule(instance, ((1,), (1, 1)), time_limit=5)
    platoon = solve_downstream_schedule(instance, ((1,), (2,)), time_limit=5)
    assert vehicle.status == "OPTIMAL"
    assert platoon.status == "OPTIMAL"
    assert round(vehicle.objective_total_delay or -1) == 2
    assert round(platoon.objective_total_delay or -1) == 4


def test_platoon_internal_release_slack_does_not_delay_early_vehicles() -> None:
    require_gurobi_runtime()
    instance = Instance(counts=(3,), releases=((0, 1, 3),), hF=1, hS=2)
    result = solve_downstream_schedule(instance, ((3,),), time_limit=5)
    assert result.status == "OPTIMAL"
    assert result.objective_total_delay is not None
    assert round(result.objective_total_delay) == 0


def test_downstream_milp_matches_exact_enumeration_on_small_instance() -> None:
    require_gurobi_runtime()
    instances = (
        Instance(counts=(2, 2), releases=((0, 3), (1, 2)), hF=1, hS=2),
        Instance(counts=(2, 2), releases=((0, 0), (0, 0)), hF=1, hS=2),
        Instance(counts=(2, 2), releases=((0, 1), (0, 1)), hF=1, hS=2),
        Instance(counts=(2, 2), releases=((0, 10), (2, 12)), hF=1, hS=2),
    )
    for instance in instances:
        for partition in enumerate_partitions(instance.counts):
            exact = optimum_for_sequences(
                enumerate_platoon_sequences(partition),
                instance.release_map,
                instance.hF,
                instance.hS,
                keep_all=False,
            )
            milp = solve_downstream_schedule(instance, partition, time_limit=5, threads=1)
            assert milp.status == "OPTIMAL"
            assert milp.objective_total_delay is not None
            assert round(milp.objective_total_delay) == exact.total_delay
