"""Global left-to-right platoon repair and invariant checks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from enumerate_sequences import is_platoon_sequence
from model import (
    Instance,
    Partition,
    SequenceT,
    Vehicle,
    internal_links,
    is_fifo_sequence,
    sequence_label,
    total_delay,
)


@dataclass(frozen=True)
class RepairRecord:
    internal_link: tuple[Vehicle, Vehicle]
    before_sequence: SequenceT
    after_sequence: SequenceT
    predecessor_position: int
    block_length: int
    suffix_length: int
    m_e: int
    fifo_index: int
    release_gap: int
    local_delay_change: int
    local_bound: int
    indexed_affected_count_bound: int

    @property
    def positive_local_bound(self) -> int:
        return max(self.local_bound, 0)

    def to_json(self) -> dict[str, object]:
        first, second = self.internal_link
        return {
            "internal_link": [f"{first[0]}:{first[1]}", f"{second[0]}:{second[1]}"],
            "before_sequence": sequence_label(self.before_sequence),
            "after_sequence": sequence_label(self.after_sequence),
            "predecessor_position": self.predecessor_position,
            "block_length": self.block_length,
            "suffix_length": self.suffix_length,
            "M_e": self.m_e,
            "i_e": self.fifo_index,
            "release_gap": self.release_gap,
            "local_delay_change": self.local_delay_change,
            "local_bound": self.local_bound,
            "positive_local_bound": self.positive_local_bound,
            "indexed_affected_count_bound": self.indexed_affected_count_bound,
        }


@dataclass(frozen=True)
class RepairResult:
    final_sequence: SequenceT
    records: tuple[RepairRecord, ...]

    def to_json(self) -> dict[str, object]:
        return {
            "final_sequence": sequence_label(self.final_sequence),
            "repair_count": len(self.records),
            "records": [record.to_json() for record in self.records],
        }


def platoon_internal_links(partition: Partition) -> tuple[tuple[Vehicle, Vehicle], ...]:
    """Return internal links in the global repair order."""

    return internal_links(partition)


def established_adjacencies(sequence: SequenceT, links: set[tuple[Vehicle, Vehicle]]) -> set[tuple[Vehicle, Vehicle]]:
    positions = {vehicle: index for index, vehicle in enumerate(sequence)}
    return {
        (first, second)
        for first, second in links
        if positions[second] == positions[first] + 1
    }


def repair_sequence_to_partition(
    instance: Instance,
    sequence: Sequence[Vehicle],
    partition: Partition,
) -> RepairResult:
    """Repair a FIFO sequence into the platoon-constrained set.

    Platoons are processed in partition order, and links inside each platoon
    are processed from left to right. Positions in repair records are zero-based.
    """

    current = tuple(sequence)
    if not is_fifo_sequence(current, instance.counts):
        raise ValueError("input sequence must be FIFO-feasible")

    releases = instance.release_map
    records: list[RepairRecord] = []
    for first, second in platoon_internal_links(partition):
        positions = {vehicle: index for index, vehicle in enumerate(current)}
        first_pos = positions[first]
        second_pos = positions[second]
        if second_pos == first_pos + 1:
            continue
        if second_pos < first_pos:
            raise ValueError("partition link violates FIFO order in current sequence")

        before = current
        block_length = second_pos - first_pos - 1
        suffix_length = len(before) - second_pos - 1
        after = (
            before[: first_pos + 1]
            + (second,)
            + before[first_pos + 1 : second_pos]
            + before[second_pos + 1 :]
        )
        release_gap = releases[second] - releases[first]
        m_e = block_length + suffix_length + 1
        local_bound = (
            m_e * max(release_gap - instance.hF, 0)
            - 2 * (instance.hS - instance.hF)
        )
        record = RepairRecord(
            internal_link=(first, second),
            before_sequence=before,
            after_sequence=after,
            predecessor_position=first_pos,
            block_length=block_length,
            suffix_length=suffix_length,
            m_e=m_e,
            fifo_index=first[1],
            release_gap=release_gap,
            local_delay_change=total_delay(after, releases, instance.hF, instance.hS)
            - total_delay(before, releases, instance.hF, instance.hS),
            local_bound=local_bound,
            indexed_affected_count_bound=instance.N - first[1],
        )
        records.append(record)
        current = after

    return RepairResult(final_sequence=current, records=tuple(records))


def validate_repair_result(
    instance: Instance,
    initial_sequence: Sequence[Vehicle],
    partition: Partition,
    result: RepairResult,
) -> None:
    """Raise AssertionError if a global repair invariant is violated."""

    initial = tuple(initial_sequence)
    assert is_fifo_sequence(initial, instance.counts)
    all_links = set(internal_links(partition))
    assert len(result.records) <= len(all_links)
    seen_links: set[tuple[Vehicle, Vehicle]] = set()
    established: set[tuple[Vehicle, Vehicle]] = set()
    current = initial
    records = iter(result.records)
    next_record = next(records, None)
    telescoping_sum = 0
    sequence_specific_bound = 0

    for link in platoon_internal_links(partition):
        before_established = established_adjacencies(current, established)
        assert before_established == established
        if next_record is not None and next_record.internal_link == link:
            record = next_record
            assert record.before_sequence == current
            assert record.internal_link not in seen_links
            seen_links.add(record.internal_link)
            assert is_fifo_sequence(record.after_sequence, instance.counts)
            assert record.block_length >= 1
            assert record.m_e == record.block_length + record.suffix_length + 1
            assert record.m_e <= record.indexed_affected_count_bound
            assert record.local_delay_change <= record.local_bound

            current = record.after_sequence
            telescoping_sum += record.local_delay_change
            sequence_specific_bound += record.positive_local_bound
            next_record = next(records, None)
        else:
            positions = {vehicle: index for index, vehicle in enumerate(current)}
            assert positions[link[1]] == positions[link[0]] + 1

        after_established = established_adjacencies(current, established)
        assert established.issubset(after_established)
        established.add(link)
        assert link in established_adjacencies(current, established)

    releases = instance.release_map
    assert next_record is None
    assert result.final_sequence == current
    assert is_platoon_sequence(result.final_sequence, partition)
    assert telescoping_sum == (
        total_delay(result.final_sequence, releases, instance.hF, instance.hS)
        - total_delay(initial, releases, instance.hF, instance.hS)
    )
    assert telescoping_sum <= sequence_specific_bound
