"""Exact partition metrics used by the formal hS=3 platooning pipeline."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from fractions import Fraction
from math import ceil
from pathlib import Path
from typing import Iterable

VERIFY_DIR = Path(__file__).resolve().parents[1] / "exhaustive_verification"
if str(VERIFY_DIR) not in sys.path:
    sys.path.insert(0, str(VERIFY_DIR))

from model import Instance, Partition, internal_links, scaled_indexed_bound  # noqa: E402


@dataclass(frozen=True)
class PartitionMetrics:
    partition: Partition
    platoons_by_approach: tuple[int, ...]
    total_platoons: int
    ordering_variables: int
    vehicle_level_ordering_variables: int
    scaled_indexed_bound: int
    dimension_reduction_fraction: Fraction

    @property
    def indexed_bound(self) -> Fraction:
        return Fraction(self.scaled_indexed_bound, sum_vehicles(self.partition))


def sum_vehicles(partition: Partition) -> int:
    return sum(sum(blocks) for blocks in partition)


def vehicle_level_ordering_variables(counts: tuple[int, ...]) -> int:
    return sum(
        counts[left] * counts[right]
        for left in range(len(counts))
        for right in range(left + 1, len(counts))
    )


def platoon_counts(partition: Partition) -> tuple[int, ...]:
    return tuple(len(blocks) for blocks in partition)


def ordering_variables_from_counts(counts: Iterable[int]) -> int:
    counts_tuple = tuple(counts)
    return sum(
        counts_tuple[left] * counts_tuple[right]
        for left in range(len(counts_tuple))
        for right in range(left + 1, len(counts_tuple))
    )


def ordering_variables(partition: Partition) -> int:
    return ordering_variables_from_counts(platoon_counts(partition))


def partition_metrics(instance: Instance, partition: Partition) -> PartitionMetrics:
    c0 = vehicle_level_ordering_variables(instance.counts)
    c_pi = ordering_variables(partition)
    reduction = Fraction(c0 - c_pi, c0) if c0 else Fraction(0, 1)
    return PartitionMetrics(
        partition=partition,
        platoons_by_approach=platoon_counts(partition),
        total_platoons=sum(platoon_counts(partition)),
        ordering_variables=c_pi,
        vehicle_level_ordering_variables=c0,
        scaled_indexed_bound=scaled_indexed_bound(instance, partition),
        dimension_reduction_fraction=reduction,
    )


def scaled_rule_level_bound(
    instance: Instance,
    threshold: int,
    max_platoon_size: int | None,
) -> int:
    """Return N times the rule-level bound for a threshold-and-size rule."""

    if threshold < 0:
        raise ValueError("threshold must be nonnegative")
    effective_max_size = instance.N if max_platoon_size is None else max_platoon_size
    if effective_max_size <= 0:
        raise ValueError("max_platoon_size must be positive")
    link_count_bound = instance.N - ceil(instance.N / effective_max_size)
    same_approach_slack = max(threshold - instance.hF, 0)
    per_link_scaled = max(
        (instance.N - 1) * same_approach_slack - 2 * (instance.hS - instance.hF),
        0,
    )
    return link_count_bound * per_link_scaled


def rule_level_bound(
    instance: Instance,
    threshold: int,
    max_platoon_size: int | None,
) -> Fraction:
    return Fraction(
        scaled_rule_level_bound(instance, threshold, max_platoon_size),
        instance.N,
    )


def partition_from_cut_bits(cuts_by_approach: tuple[tuple[int, ...], ...]) -> Partition:
    """Build a contiguous partition from boundary cut indicators.

    A cut bit is one when the boundary after that vehicle is cut. A zero bit
    means the two adjacent vehicles are joined into the same platoon.
    """

    partition: list[tuple[int, ...]] = []
    for cuts in cuts_by_approach:
        blocks: list[int] = []
        block_size = 1
        for cut in cuts:
            if cut:
                blocks.append(block_size)
                block_size = 1
            else:
                block_size += 1
        blocks.append(block_size)
        partition.append(tuple(blocks))
    return tuple(partition)


def cut_bits_from_partition(partition: Partition) -> tuple[tuple[int, ...], ...]:
    cuts_by_approach: list[tuple[int, ...]] = []
    for blocks in partition:
        cuts: list[int] = []
        for block_index, block_size in enumerate(blocks):
            cuts.extend([0] * (block_size - 1))
            if block_index != len(blocks) - 1:
                cuts.append(1)
        cuts_by_approach.append(tuple(cuts))
    return tuple(cuts_by_approach)


def respects_max_platoon_size(partition: Partition, max_platoon_size: int | None) -> bool:
    if max_platoon_size is None:
        return True
    if max_platoon_size <= 0:
        raise ValueError("max_platoon_size must be positive")
    return all(block_size <= max_platoon_size for blocks in partition for block_size in blocks)


def scaled_internal_link_weights(instance: Instance) -> dict[tuple[int, int], int]:
    """Return each link's exact contribution to N * B_idx if joined."""

    releases = instance.release_map
    switch_saving = 2 * (instance.hS - instance.hF)
    weights: dict[tuple[int, int], int] = {}
    singleton_partition: Partition = tuple((count,) for count in instance.counts)
    for first, second in internal_links(singleton_partition):
        release_gap = releases[second] - releases[first]
        same_approach_slack = max(release_gap - instance.hF, 0)
        weights[first] = max(
            (instance.N - first[1]) * same_approach_slack - switch_saving,
            0,
        )
    return weights


def fraction_label(value: Fraction) -> str:
    if value.denominator == 1:
        return str(value.numerator)
    return f"{value.numerator}/{value.denominator}"
