"""Partition-selection models for dimension-loss frontier experiments."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

VERIFY_DIR = Path(__file__).resolve().parents[1] / "exhaustive_verification"
if str(VERIFY_DIR) not in sys.path:
    sys.path.insert(0, str(VERIFY_DIR))

from enumerate_partitions import enumerate_partitions  # noqa: E402
from model import Instance, Partition, partition_label, scaled_indexed_bound  # noqa: E402
from metrics import (  # noqa: E402
    ordering_variables,
    partition_from_cut_bits,
    partition_metrics,
    respects_max_platoon_size,
    scaled_internal_link_weights,
    vehicle_level_ordering_variables,
)

ObjectiveMode = Literal["loss_budget", "size_budget"]
SolverName = Literal["gurobi", "enum", "auto"]


@dataclass(frozen=True)
class PartitionSelectionResult:
    mode: ObjectiveMode
    solver: str
    status: str
    partition: Partition | None
    scaled_loss_budget: int | None = None
    ordering_budget: int | None = None
    objective_value: int | None = None
    ordering_variables: int | None = None
    scaled_indexed_bound: int | None = None
    total_platoons: int | None = None
    platoons_by_approach: tuple[int, ...] | None = None

    def to_json(self) -> dict[str, object]:
        return {
            "mode": self.mode,
            "solver": self.solver,
            "status": self.status,
            "partition": partition_label(self.partition) if self.partition is not None else None,
            "scaled_loss_budget": self.scaled_loss_budget,
            "ordering_budget": self.ordering_budget,
            "objective_value": self.objective_value,
            "ordering_variables": self.ordering_variables,
            "scaled_indexed_bound": self.scaled_indexed_bound,
            "total_platoons": self.total_platoons,
            "platoons_by_approach": list(self.platoons_by_approach)
            if self.platoons_by_approach is not None
            else None,
        }


def _result_from_partition(
    mode: ObjectiveMode,
    solver: str,
    instance: Instance,
    partition: Partition,
    scaled_loss_budget: int | None = None,
    ordering_budget: int | None = None,
) -> PartitionSelectionResult:
    metrics = partition_metrics(instance, partition)
    objective = (
        metrics.ordering_variables
        if mode == "loss_budget"
        else metrics.scaled_indexed_bound
    )
    return PartitionSelectionResult(
        mode=mode,
        solver=solver,
        status="OPTIMAL",
        partition=partition,
        scaled_loss_budget=scaled_loss_budget,
        ordering_budget=ordering_budget,
        objective_value=objective,
        ordering_variables=metrics.ordering_variables,
        scaled_indexed_bound=metrics.scaled_indexed_bound,
        total_platoons=metrics.total_platoons,
        platoons_by_approach=metrics.platoons_by_approach,
    )


def solve_loss_budget_enum(
    instance: Instance,
    scaled_loss_budget: int,
    max_platoon_size: int | None = None,
) -> PartitionSelectionResult:
    best: Partition | None = None
    best_key: tuple[int, int, tuple[tuple[int, ...], ...]] | None = None
    for partition in enumerate_partitions(instance.counts):
        if not respects_max_platoon_size(partition, max_platoon_size):
            continue
        scaled_bound = scaled_indexed_bound(instance, partition)
        if scaled_bound > scaled_loss_budget:
            continue
        key = (ordering_variables(partition), scaled_bound, partition)
        if best_key is None or key < best_key:
            best_key = key
            best = partition
    if best is None:
        return PartitionSelectionResult(
            mode="loss_budget",
            solver="enum",
            status="INFEASIBLE",
            partition=None,
            scaled_loss_budget=scaled_loss_budget,
        )
    return _result_from_partition(
        "loss_budget",
        "enum",
        instance,
        best,
        scaled_loss_budget=scaled_loss_budget,
    )


def solve_size_budget_enum(
    instance: Instance,
    ordering_budget: int,
    max_platoon_size: int | None = None,
) -> PartitionSelectionResult:
    best: Partition | None = None
    best_key: tuple[int, int, tuple[tuple[int, ...], ...]] | None = None
    for partition in enumerate_partitions(instance.counts):
        if not respects_max_platoon_size(partition, max_platoon_size):
            continue
        c_pi = ordering_variables(partition)
        if c_pi > ordering_budget:
            continue
        scaled_bound = scaled_indexed_bound(instance, partition)
        key = (scaled_bound, c_pi, partition)
        if best_key is None or key < best_key:
            best_key = key
            best = partition
    if best is None:
        return PartitionSelectionResult(
            mode="size_budget",
            solver="enum",
            status="INFEASIBLE",
            partition=None,
            ordering_budget=ordering_budget,
        )
    return _result_from_partition(
        "size_budget",
        "enum",
        instance,
        best,
        ordering_budget=ordering_budget,
    )


def _import_gurobi():
    try:
        import gurobipy as gp
        from gurobipy import GRB
    except ModuleNotFoundError as exc:
        raise RuntimeError("gurobipy is not installed in this environment") from exc
    return gp, GRB


def _build_gurobi_model(
    instance: Instance,
    max_platoon_size: int | None,
    name: str,
):
    gp, GRB = _import_gurobi()
    model = gp.Model(name)
    cuts = {}
    for approach, count in enumerate(instance.counts, start=1):
        for boundary in range(1, count):
            cuts[(approach, boundary)] = model.addVar(
                vtype=GRB.BINARY,
                name=f"cut_{approach}_{boundary}",
            )

    if max_platoon_size is not None:
        if max_platoon_size <= 0:
            raise ValueError("max_platoon_size must be positive")
        for approach, count in enumerate(instance.counts, start=1):
            if max_platoon_size >= count:
                continue
            for start in range(1, count - max_platoon_size + 1):
                model.addConstr(
                    gp.quicksum(
                        cuts[(approach, boundary)]
                        for boundary in range(start, start + max_platoon_size)
                    )
                    >= 1,
                    name=f"max_platoon_{approach}_{start}",
                )

    weights = scaled_internal_link_weights(instance)
    scaled_bound_expr = gp.quicksum(
        weight * (1 - cuts[(approach, boundary)])
        for (approach, boundary), weight in weights.items()
    )

    dimension_expr = 0
    for left in range(1, instance.L + 1):
        for right in range(left + 1, instance.L + 1):
            dimension_expr += 1
            left_boundaries = range(1, instance.counts[left - 1])
            right_boundaries = range(1, instance.counts[right - 1])
            for boundary in left_boundaries:
                dimension_expr += cuts[(left, boundary)]
            for boundary in right_boundaries:
                dimension_expr += cuts[(right, boundary)]
            for left_boundary in left_boundaries:
                for right_boundary in right_boundaries:
                    product_var = model.addVar(
                        vtype=GRB.BINARY,
                        name=f"cutprod_{left}_{left_boundary}_{right}_{right_boundary}",
                    )
                    model.addConstr(product_var <= cuts[(left, left_boundary)])
                    model.addConstr(product_var <= cuts[(right, right_boundary)])
                    model.addConstr(
                        product_var >= cuts[(left, left_boundary)] + cuts[(right, right_boundary)] - 1
                    )
                    dimension_expr += product_var

    model.update()
    return gp, GRB, model, cuts, scaled_bound_expr, dimension_expr


def _partition_from_gurobi_solution(instance: Instance, cuts) -> Partition:
    cuts_by_approach: list[tuple[int, ...]] = []
    for approach, count in enumerate(instance.counts, start=1):
        cuts_by_approach.append(
            tuple(
                1 if cuts[(approach, boundary)].X >= 0.5 else 0
                for boundary in range(1, count)
            )
        )
    return partition_from_cut_bits(tuple(cuts_by_approach))


def solve_loss_budget_gurobi(
    instance: Instance,
    scaled_loss_budget: int,
    max_platoon_size: int | None = None,
    time_limit: float | None = None,
) -> PartitionSelectionResult:
    gp, GRB, model, cuts, scaled_bound_expr, dimension_expr = _build_gurobi_model(
        instance,
        max_platoon_size,
        "loss_budget_partition_selection",
    )
    model.addConstr(scaled_bound_expr <= scaled_loss_budget, name="loss_budget")
    max_scaled_bound = sum(scaled_internal_link_weights(instance).values())
    model.setObjective(
        dimension_expr * (max_scaled_bound + 1) + scaled_bound_expr,
        GRB.MINIMIZE,
    )
    if time_limit is not None:
        model.Params.TimeLimit = time_limit
    model.optimize()
    if model.Status != GRB.OPTIMAL:
        return PartitionSelectionResult(
            mode="loss_budget",
            solver="gurobi",
            status=str(model.Status),
            partition=None,
            scaled_loss_budget=scaled_loss_budget,
        )
    partition = _partition_from_gurobi_solution(instance, cuts)
    return _result_from_partition(
        "loss_budget",
        "gurobi",
        instance,
        partition,
        scaled_loss_budget=scaled_loss_budget,
    )


def solve_size_budget_gurobi(
    instance: Instance,
    ordering_budget: int,
    max_platoon_size: int | None = None,
    time_limit: float | None = None,
) -> PartitionSelectionResult:
    gp, GRB, model, cuts, scaled_bound_expr, dimension_expr = _build_gurobi_model(
        instance,
        max_platoon_size,
        "size_budget_partition_selection",
    )
    model.addConstr(dimension_expr <= ordering_budget, name="ordering_budget")
    c0 = vehicle_level_ordering_variables(instance.counts)
    model.setObjective(
        scaled_bound_expr * (c0 + 1) + dimension_expr,
        GRB.MINIMIZE,
    )
    if time_limit is not None:
        model.Params.TimeLimit = time_limit
    model.optimize()
    if model.Status != GRB.OPTIMAL:
        return PartitionSelectionResult(
            mode="size_budget",
            solver="gurobi",
            status=str(model.Status),
            partition=None,
            ordering_budget=ordering_budget,
        )
    partition = _partition_from_gurobi_solution(instance, cuts)
    return _result_from_partition(
        "size_budget",
        "gurobi",
        instance,
        partition,
        ordering_budget=ordering_budget,
    )


def solve_loss_budget(
    instance: Instance,
    scaled_loss_budget: int,
    max_platoon_size: int | None = None,
    solver: SolverName = "auto",
    time_limit: float | None = None,
) -> PartitionSelectionResult:
    if solver == "enum":
        return solve_loss_budget_enum(instance, scaled_loss_budget, max_platoon_size)
    if solver == "gurobi":
        return solve_loss_budget_gurobi(
            instance,
            scaled_loss_budget,
            max_platoon_size,
            time_limit,
        )
    try:
        return solve_loss_budget_gurobi(
            instance,
            scaled_loss_budget,
            max_platoon_size,
            time_limit,
        )
    except RuntimeError:
        return solve_loss_budget_enum(instance, scaled_loss_budget, max_platoon_size)


def solve_size_budget(
    instance: Instance,
    ordering_budget: int,
    max_platoon_size: int | None = None,
    solver: SolverName = "auto",
    time_limit: float | None = None,
) -> PartitionSelectionResult:
    if solver == "enum":
        return solve_size_budget_enum(instance, ordering_budget, max_platoon_size)
    if solver == "gurobi":
        return solve_size_budget_gurobi(
            instance,
            ordering_budget,
            max_platoon_size,
            time_limit,
        )
    try:
        return solve_size_budget_gurobi(
            instance,
            ordering_budget,
            max_platoon_size,
            time_limit,
        )
    except RuntimeError:
        return solve_size_budget_enum(instance, ordering_budget, max_platoon_size)

