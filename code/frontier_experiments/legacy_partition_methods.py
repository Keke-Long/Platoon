"""Legacy optimization-based partition methods.

These functions are retained only for reproducing archived optimized-partition
experiments. They are not part of the active NP/CHP/PP rule-based pipeline.
"""

from __future__ import annotations

import sys
from pathlib import Path

VERIFY_DIR = Path(__file__).resolve().parents[1] / "exhaustive_verification"
if str(VERIFY_DIR) not in sys.path:
    sys.path.insert(0, str(VERIFY_DIR))

from model import Instance, Partition  # noqa: E402
from partition_methods import no_platooning_partition  # noqa: E402
from partition_selection import solve_loss_budget, solve_size_budget  # noqa: E402


def bound_aware_loss_budget_partition(
    instance: Instance,
    scaled_loss_budget: int,
    max_platoon_size: int | None,
    solver: str = "gurobi",
    time_limit: float | None = None,
) -> Partition:
    result = solve_loss_budget(
        instance,
        scaled_loss_budget,
        max_platoon_size=max_platoon_size,
        solver=solver,  # type: ignore[arg-type]
        time_limit=time_limit,
    )
    if result.partition is None:
        return no_platooning_partition(instance.counts)
    return result.partition


def bound_aware_size_budget_partition(
    instance: Instance,
    ordering_budget: int,
    max_platoon_size: int | None,
    solver: str = "gurobi",
    time_limit: float | None = None,
) -> Partition:
    result = solve_size_budget(
        instance,
        ordering_budget,
        max_platoon_size=max_platoon_size,
        solver=solver,  # type: ignore[arg-type]
        time_limit=time_limit,
    )
    if result.partition is None:
        return no_platooning_partition(instance.counts)
    return result.partition
