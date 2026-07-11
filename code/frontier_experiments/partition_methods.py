"""Rule-based and archived platoon partition methods."""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

VERIFY_DIR = Path(__file__).resolve().parents[1] / "exhaustive_verification"
if str(VERIFY_DIR) not in sys.path:
    sys.path.insert(0, str(VERIFY_DIR))

from model import Instance, Partition  # noqa: E402

RuleMethod = Literal["NP", "CHP", "PP"]


@dataclass(frozen=True)
class PlatoonFormationResult:
    method: RuleMethod
    partition: Partition
    formation_time_ms: float
    threshold: int | None = None
    max_platoon_size: int | None = None


def no_platooning_partition(counts: tuple[int, ...]) -> Partition:
    return tuple(tuple(1 for _ in range(count)) for count in counts)


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
    if threshold < 0:
        raise ValueError("threshold must be nonnegative")
    if max_platoon_size is not None and max_platoon_size <= 0:
        raise ValueError("max_platoon_size must be positive")
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


def critical_headway_platooning(instance: Instance, threshold: int) -> Partition:
    return release_gap_threshold_partition(
        instance,
        threshold=threshold,
        max_platoon_size=None,
    )


def proposed_platooning(
    instance: Instance,
    threshold: int,
    max_platoon_size: int,
) -> Partition:
    return release_gap_threshold_partition(
        instance,
        threshold=threshold,
        max_platoon_size=max_platoon_size,
    )


def form_rule_based_platoons(
    instance: Instance,
    method: RuleMethod,
    threshold: int | None = None,
    max_platoon_size: int | None = None,
) -> PlatoonFormationResult:
    """Form NP, CHP, or PP platoons by direct linear scanning.

    This entry point intentionally does not call the archived partition
    optimization code and does not enumerate candidate partitions.
    """

    start = time.perf_counter()
    if method == "NP":
        partition = no_platooning_partition(instance.counts)
        resolved_threshold = None
        resolved_max_platoon_size = 1
    elif method == "CHP":
        if threshold is None:
            raise ValueError("CHP requires threshold")
        partition = critical_headway_platooning(instance, threshold)
        resolved_threshold = threshold
        resolved_max_platoon_size = None
    elif method == "PP":
        if threshold is None:
            raise ValueError("PP requires threshold")
        if max_platoon_size is None:
            raise ValueError("PP requires max_platoon_size")
        partition = proposed_platooning(instance, threshold, max_platoon_size)
        resolved_threshold = threshold
        resolved_max_platoon_size = max_platoon_size
    else:
        raise ValueError(f"unknown rule-based method: {method}")
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    return PlatoonFormationResult(
        method=method,
        partition=partition,
        formation_time_ms=elapsed_ms,
        threshold=resolved_threshold,
        max_platoon_size=resolved_max_platoon_size,
    )


def bound_aware_loss_budget_partition(
    instance: Instance,
    scaled_loss_budget: int,
    max_platoon_size: int | None,
    solver: str = "gurobi",
    time_limit: float | None = None,
) -> Partition:
    from partition_selection import solve_loss_budget  # noqa: PLC0415

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
    from partition_selection import solve_size_budget  # noqa: PLC0415

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
