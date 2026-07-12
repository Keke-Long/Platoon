"""Downstream platoon scheduling MILP solved with Gurobi."""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

VERIFY_DIR = Path(__file__).resolve().parents[1] / "exhaustive_verification"
if str(VERIFY_DIR) not in sys.path:
    sys.path.insert(0, str(VERIFY_DIR))

from model import Instance, Partition, Vehicle, partition_label  # noqa: E402
from metrics import ordering_variables, platoon_counts  # noqa: E402


@dataclass(frozen=True)
class PlatoonUnit:
    approach: int
    index: int
    vehicles: tuple[Vehicle, ...]

    @property
    def size(self) -> int:
        return len(self.vehicles)


@dataclass(frozen=True)
class ScheduleResult:
    status: str
    objective_total_delay: float | None
    objective_average_delay: float | None
    best_bound: float | None
    mip_gap: float | None
    runtime_seconds: float
    model_construction_seconds: float
    end_to_end_seconds: float
    node_count: float
    time_to_first_feasible: float | None
    sol_count: int
    ordering_variables: int
    total_platoons: int
    platoons_by_approach: tuple[int, ...]
    partition: Partition
    incumbent_trajectory: tuple[dict[str, float], ...] = ()

    def to_json(self) -> dict[str, object]:
        return {
            "status": self.status,
            "objective_total_delay": self.objective_total_delay,
            "objective_average_delay": self.objective_average_delay,
            "best_bound": self.best_bound,
            "mip_gap": self.mip_gap,
            "runtime_seconds": self.runtime_seconds,
            "model_construction_seconds": self.model_construction_seconds,
            "end_to_end_seconds": self.end_to_end_seconds,
            "node_count": self.node_count,
            "time_to_first_feasible": self.time_to_first_feasible,
            "sol_count": self.sol_count,
            "ordering_variables": self.ordering_variables,
            "total_platoons": self.total_platoons,
            "platoons_by_approach": list(self.platoons_by_approach),
            "partition": partition_label(self.partition),
            "incumbent_trajectory": list(self.incumbent_trajectory),
        }


def _import_gurobi():
    try:
        import gurobipy as gp
        from gurobipy import GRB
    except ModuleNotFoundError as exc:
        raise RuntimeError("gurobipy is not installed in this environment") from exc
    return gp, GRB


def units_from_partition(partition: Partition) -> tuple[PlatoonUnit, ...]:
    units: list[PlatoonUnit] = []
    for approach, blocks in enumerate(partition, start=1):
        next_vehicle = 1
        for platoon_index, block_size in enumerate(blocks, start=1):
            vehicles = tuple(
                (approach, vehicle_index)
                for vehicle_index in range(next_vehicle, next_vehicle + block_size)
            )
            units.append(PlatoonUnit(approach, platoon_index, vehicles))
            next_vehicle += block_size
    return tuple(units)


def singleton_partition(counts: tuple[int, ...]) -> Partition:
    return tuple(tuple(1 for _ in range(count)) for count in counts)


def _status_name(GRB: Any, status: int) -> str:
    names = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.INTERRUPTED: "INTERRUPTED",
        GRB.SUBOPTIMAL: "SUBOPTIMAL",
        GRB.NUMERIC: "NUMERIC",
    }
    return names.get(status, str(status))


def solve_downstream_schedule(
    instance: Instance,
    partition: Partition,
    time_limit: float | None = None,
    mip_gap: float | None = None,
    threads: int | None = None,
    collect_trajectory: bool = False,
) -> ScheduleResult:
    """Solve the platoon-constrained scheduling MILP.

    Each vehicle has a passing-time variable. Vehicles inside a platoon are
    constrained to be consecutive in the unit ordering, but their internal
    headways may exceed hF when release times require waiting.
    """

    total_start = time.perf_counter()
    gp, GRB = _import_gurobi()
    env = gp.Env(empty=True)
    env.setParam("OutputFlag", 0)
    env.start()
    model = gp.Model("downstream_platoon_schedule", env=env)
    if time_limit is not None:
        model.Params.TimeLimit = time_limit
    if mip_gap is not None:
        model.Params.MIPGap = mip_gap
    if threads is not None:
        model.Params.Threads = threads

    releases = instance.release_map
    units = units_from_partition(partition)
    passing_time = {
        vehicle: model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"C_{vehicle[0]}_{vehicle[1]}")
        for unit in units
        for vehicle in unit.vehicles
    }
    max_release = max(releases.values()) if releases else 0
    big_m = max_release + instance.N * instance.hS + instance.N * instance.hF + 1

    for unit in units:
        for vehicle in unit.vehicles:
            model.addConstr(
                passing_time[vehicle] >= releases[vehicle],
                name=f"release_{vehicle[0]}_{vehicle[1]}",
            )
        for previous, current in zip(unit.vehicles, unit.vehicles[1:], strict=False):
            model.addConstr(
                passing_time[current] >= passing_time[previous] + instance.hF,
                name=f"internal_{previous[0]}_{previous[1]}",
            )

    units_by_approach: dict[int, list[PlatoonUnit]] = {}
    for unit in units:
        units_by_approach.setdefault(unit.approach, []).append(unit)
    for approach_units in units_by_approach.values():
        for previous, current in zip(approach_units, approach_units[1:], strict=False):
            model.addConstr(
                passing_time[current.vehicles[0]] >= passing_time[previous.vehicles[-1]] + instance.hF,
                name=f"fifo_{previous.approach}_{previous.index}",
            )

    for left_index, left in enumerate(units):
        for right in units[left_index + 1:]:
            if left.approach == right.approach:
                continue
            y = model.addVar(vtype=GRB.BINARY, name=f"prec_{left.approach}_{left.index}_{right.approach}_{right.index}")
            model.addConstr(
                passing_time[right.vehicles[0]]
                >= passing_time[left.vehicles[-1]] + instance.hS - big_m * (1 - y),
                name=f"sep_lr_{left.approach}_{left.index}_{right.approach}_{right.index}",
            )
            model.addConstr(
                passing_time[left.vehicles[0]]
                >= passing_time[right.vehicles[-1]] + instance.hS - big_m * y,
                name=f"sep_rl_{left.approach}_{left.index}_{right.approach}_{right.index}",
            )

    total_delay_expr = 0
    for unit in units:
        for vehicle in unit.vehicles:
            total_delay_expr += passing_time[vehicle] - releases[vehicle]
    model.setObjective(total_delay_expr, GRB.MINIMIZE)
    model.update()
    construction_seconds = time.perf_counter() - total_start

    first_feasible_time: list[float | None] = [None]
    incumbent_trajectory: list[dict[str, float]] = []

    def callback(model_cb, where):
        if where == GRB.Callback.MIPSOL:
            runtime = float(model_cb.cbGet(GRB.Callback.RUNTIME))
            objective = float(model_cb.cbGet(GRB.Callback.MIPSOL_OBJ))
            best_bound = float(model_cb.cbGet(GRB.Callback.MIPSOL_OBJBND))
            if first_feasible_time[0] is None:
                first_feasible_time[0] = runtime
            if collect_trajectory:
                gap = None
                if abs(objective) > 1e-12:
                    gap = abs(objective - best_bound) / abs(objective)
                incumbent_trajectory.append(
                    {
                        "time_s": runtime,
                        "incumbent_total_delay": objective,
                        "incumbent_average_delay": objective / instance.N,
                        "best_bound_total_delay": best_bound,
                        "best_bound_average_delay": best_bound / instance.N,
                        "mip_gap": gap if gap is not None else 0.0,
                    }
                )

    try:
        model.optimize(callback)
    except gp.GurobiError as exc:
        end_to_end_seconds = time.perf_counter() - total_start
        return ScheduleResult(
            status=f"GUROBI_ERROR_{exc.errno}",
            objective_total_delay=None,
            objective_average_delay=None,
            best_bound=None,
            mip_gap=None,
            runtime_seconds=float(getattr(model, "Runtime", 0.0)),
            model_construction_seconds=construction_seconds,
            end_to_end_seconds=end_to_end_seconds,
            node_count=float(getattr(model, "NodeCount", 0.0)),
            time_to_first_feasible=first_feasible_time[0],
            sol_count=0,
            ordering_variables=ordering_variables(partition),
            total_platoons=sum(platoon_counts(partition)),
            platoons_by_approach=platoon_counts(partition),
            partition=partition,
            incumbent_trajectory=tuple(incumbent_trajectory),
        )
    end_to_end_seconds = time.perf_counter() - total_start
    sol_count = int(model.SolCount)
    objective = float(model.ObjVal) if sol_count else None
    best_bound = float(model.ObjBound) if sol_count or model.Status == GRB.TIME_LIMIT else None
    try:
        gap = float(model.MIPGap) if sol_count else None
    except AttributeError:
        gap = 0.0 if sol_count else None
    return ScheduleResult(
        status=_status_name(GRB, model.Status),
        objective_total_delay=objective,
        objective_average_delay=objective / instance.N if objective is not None else None,
        best_bound=best_bound,
        mip_gap=gap,
        runtime_seconds=float(model.Runtime),
        model_construction_seconds=construction_seconds,
        end_to_end_seconds=end_to_end_seconds,
        node_count=float(model.NodeCount),
        time_to_first_feasible=first_feasible_time[0],
        sol_count=sol_count,
        ordering_variables=ordering_variables(partition),
        total_platoons=sum(platoon_counts(partition)),
        platoons_by_approach=platoon_counts(partition),
        partition=partition,
        incumbent_trajectory=tuple(incumbent_trajectory),
    )
