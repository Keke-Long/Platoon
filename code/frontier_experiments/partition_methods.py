"""Baseline and bound-aware platoon partition methods."""

from __future__ import annotations

import sys
from pathlib import Path

VERIFY_DIR = Path(__file__).resolve().parents[1] / "exhaustive_verification"
if str(VERIFY_DIR) not in sys.path:
    sys.path.insert(0, str(VERIFY_DIR))

from model import Instance, Partition  # noqa: E402
from partition_selection import solve_loss_budget, solve_size_budget  # noqa: E402
from scheduling_milp import singleton_partition  # noqa: E402


def fixed_size_partition(counts: tuple[int, ...], platoon_size: int) -> Partition:
    if platoon_size <= 0:
        raise ValueError("platoon_size must be positive")
    partition: list[tuple[int, ...]] = []
    for count in counts:
        blocks: list[int] = []
        remaining = count
        while remaining > 0:
            block = min(platoon_size, remaining)
            blocks.append(block)
            remaining -= block
        partition.append(tuple(blocks))
    return tuple(partition)


def release_gap_threshold_partition(
    instance: Instance,
    threshold: int,
    max_platoon_size: int | None = None,
) -> Partition:
    partition: list[tuple[int, ...]] = []
    for releases in instance.releases:
        blocks: list[int] = []
        block_size = 1
        for left, right in zip(releases, releases[1:], strict=False):
            can_join = right - left <= threshold
            if max_platoon_size is not None and block_size >= max_platoon_size:
                can_join = False
            if can_join:
                block_size += 1
            else:
                blocks.append(block_size)
                block_size = 1
        blocks.append(block_size)
        partition.append(tuple(blocks))
    return tuple(partition)


def bound_aware_loss_budget_partition(
    instance: Instance,
    scaled_loss_budget: int,
    max_platoon_size: int | None,
    solver: str = "gurobi",
) -> Partition:
    result = solve_loss_budget(
        instance,
        scaled_loss_budget,
        max_platoon_size=max_platoon_size,
        solver=solver,  # type: ignore[arg-type]
    )
    if result.partition is None:
        return singleton_partition(instance.counts)
    return result.partition


def bound_aware_size_budget_partition(
    instance: Instance,
    ordering_budget: int,
    max_platoon_size: int | None,
    solver: str = "gurobi",
) -> Partition:
    result = solve_size_budget(
        instance,
        ordering_budget,
        max_platoon_size=max_platoon_size,
        solver=solver,  # type: ignore[arg-type]
    )
    if result.partition is None:
        return singleton_partition(instance.counts)
    return result.partition

