"""Rule-based and archived platoon partition methods."""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass
from statistics import median
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
    timing_repetitions: int = 1,
) -> PlatoonFormationResult:
    """Form NP, CHP, or PP platoons by direct linear scanning.

    This entry point intentionally does not call the archived partition
    optimization code and does not enumerate candidate partitions.
    """

    if timing_repetitions <= 0:
        raise ValueError("timing_repetitions must be positive")

    def build() -> tuple[Partition, int | None, int | None]:
        if method == "NP":
            return no_platooning_partition(instance.counts), None, 1
        if method == "CHP":
            if threshold is None:
                raise ValueError("CHP requires threshold")
            return critical_headway_platooning(instance, threshold), threshold, None
        if method == "PP":
            if threshold is None:
                raise ValueError("PP requires threshold")
            if max_platoon_size is None:
                raise ValueError("PP requires max_platoon_size")
            return proposed_platooning(instance, threshold, max_platoon_size), threshold, max_platoon_size
        raise ValueError(f"unknown rule-based method: {method}")

    timings_ns: list[int] = []
    partition: Partition | None = None
    resolved_threshold: int | None = None
    resolved_max_platoon_size: int | None = None
    for _ in range(timing_repetitions):
        start_ns = time.perf_counter_ns()
        partition, resolved_threshold, resolved_max_platoon_size = build()
        timings_ns.append(time.perf_counter_ns() - start_ns)
    assert partition is not None
    elapsed_ms = median(timings_ns) / 1_000_000.0
    return PlatoonFormationResult(
        method=method,
        partition=partition,
        formation_time_ms=elapsed_ms,
        threshold=resolved_threshold,
        max_platoon_size=resolved_max_platoon_size,
    )
