"""Exact model logic for platoon scheduling verification."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Iterable, Mapping, Sequence

Vehicle = tuple[int, int]
SequenceT = tuple[Vehicle, ...]
ReleaseTimes = dict[Vehicle, int]
ApproachPartition = tuple[int, ...]
Partition = tuple[ApproachPartition, ...]


@dataclass(frozen=True)
class Instance:
    """A small exact scheduling instance."""

    counts: tuple[int, ...]
    releases: tuple[tuple[int, ...], ...]
    hF: int
    hS: int

    def __post_init__(self) -> None:
        if self.hF <= 0 or self.hS <= self.hF:
            raise ValueError("headways must satisfy 0 < hF < hS")
        if len(self.counts) != len(self.releases):
            raise ValueError("counts and releases must have the same length")
        for count, rels in zip(self.counts, self.releases, strict=True):
            if count != len(rels):
                raise ValueError("release vector length must match vehicle count")
            if any(rels[i] > rels[i + 1] for i in range(len(rels) - 1)):
                raise ValueError("release times must be nondecreasing within each approach")

    @property
    def L(self) -> int:
        return len(self.counts)

    @property
    def N(self) -> int:
        return sum(self.counts)

    @property
    def release_map(self) -> ReleaseTimes:
        return {
            (approach + 1, index + 1): release
            for approach, rels in enumerate(self.releases)
            for index, release in enumerate(rels)
        }


@dataclass(frozen=True)
class Optimum:
    total_delay: int
    sequences: tuple[SequenceT, ...]

    @property
    def average_delay(self) -> Fraction:
        if not self.sequences:
            raise ValueError("cannot compute average delay without a sequence length")
        return Fraction(self.total_delay, len(self.sequences[0]))


def vehicles_for_counts(counts: Sequence[int]) -> tuple[Vehicle, ...]:
    return tuple(
        (approach + 1, index + 1)
        for approach, count in enumerate(counts)
        for index in range(count)
    )


def headway(prev: Vehicle, current: Vehicle, hF: int, hS: int) -> int:
    return hF if prev[0] == current[0] else hS


def completion_times(
    sequence: Sequence[Vehicle],
    releases: Mapping[Vehicle, int],
    hF: int,
    hS: int,
) -> dict[Vehicle, int]:
    if not sequence:
        return {}
    completions: dict[Vehicle, int] = {}
    first = sequence[0]
    completions[first] = releases[first]
    for prev, current in zip(sequence, sequence[1:], strict=False):
        completions[current] = max(
            releases[current],
            completions[prev] + headway(prev, current, hF, hS),
        )
    return completions


def total_delay(
    sequence: Sequence[Vehicle],
    releases: Mapping[Vehicle, int],
    hF: int,
    hS: int,
) -> int:
    completions = completion_times(sequence, releases, hF, hS)
    return sum(completions[vehicle] - releases[vehicle] for vehicle in sequence)


def optimum_for_sequences(
    sequences: Iterable[SequenceT],
    releases: Mapping[Vehicle, int],
    hF: int,
    hS: int,
    keep_all: bool = True,
) -> Optimum:
    best_delay: int | None = None
    best_sequences: list[SequenceT] = []
    for sequence in sequences:
        delay = total_delay(sequence, releases, hF, hS)
        if best_delay is None or delay < best_delay:
            best_delay = delay
            best_sequences = [sequence]
        elif keep_all and delay == best_delay:
            best_sequences.append(sequence)
    if best_delay is None:
        raise ValueError("at least one sequence is required")
    return Optimum(best_delay, tuple(best_sequences))


def internal_links(partition: Partition) -> tuple[tuple[Vehicle, Vehicle], ...]:
    links: list[tuple[Vehicle, Vehicle]] = []
    for approach_index, approach_partition in enumerate(partition, start=1):
        vehicle_index = 1
        for block_size in approach_partition:
            for offset in range(block_size - 1):
                links.append(
                    (
                        (approach_index, vehicle_index + offset),
                        (approach_index, vehicle_index + offset + 1),
                    )
                )
            vehicle_index += block_size
    return tuple(links)


def scaled_index_free_bound(instance: Instance, partition: Partition) -> int:
    """Return N times the archived index-free bound, exactly."""

    releases = instance.release_map
    scaled_bound = 0
    switch_saving = 2 * (instance.hS - instance.hF)
    for first, second in internal_links(partition):
        release_gap = releases[second] - releases[first]
        same_approach_slack = max(release_gap - instance.hF, 0)
        scaled_bound += max(instance.N * same_approach_slack - switch_saving, 0)
    return scaled_bound


def scaled_indexed_bound(instance: Instance, partition: Partition) -> int:
    """Return N times the FIFO-indexed bound, exactly."""

    releases = instance.release_map
    scaled_bound = 0
    switch_saving = 2 * (instance.hS - instance.hF)
    for first, second in internal_links(partition):
        release_gap = releases[second] - releases[first]
        same_approach_slack = max(release_gap - instance.hF, 0)
        predecessor_fifo_index = first[1]
        scaled_bound += max(
            (instance.N - predecessor_fifo_index) * same_approach_slack
            - switch_saving,
            0,
        )
    return scaled_bound


scaled_candidate_bound = scaled_index_free_bound


def partition_label(partition: Partition) -> list[list[int]]:
    return [list(blocks) for blocks in partition]


def sequence_label(sequence: Sequence[Vehicle]) -> list[str]:
    return [f"{vehicle[0]}:{vehicle[1]}" for vehicle in sequence]


def is_fifo_sequence(sequence: Sequence[Vehicle], counts: Sequence[int]) -> bool:
    expected = [1] * len(counts)
    seen = [0] * len(counts)
    for approach, index in sequence:
        if approach < 1 or approach > len(counts):
            return False
        if index != expected[approach - 1]:
            return False
        expected[approach - 1] += 1
        seen[approach - 1] += 1
    return tuple(seen) == tuple(counts)
