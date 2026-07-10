"""Independent checks for the candidate local repair inequality."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from model import Instance, SequenceT, Vehicle, sequence_label, total_delay


@dataclass(frozen=True)
class LocalRepairViolation:
    instance: Instance
    sequence: SequenceT
    repaired_sequence: SequenceT
    first: Vehicle
    second: Vehicle
    block_length: int
    suffix_length: int
    lhs: int
    rhs: int

    def to_json(self) -> dict[str, object]:
        return {
            "L": self.instance.L,
            "N": self.instance.N,
            "counts": list(self.instance.counts),
            "hF": self.instance.hF,
            "hS": self.instance.hS,
            "releases": [list(row) for row in self.instance.releases],
            "sequence": sequence_label(self.sequence),
            "repaired_sequence": sequence_label(self.repaired_sequence),
            "first": f"{self.first[0]}:{self.first[1]}",
            "second": f"{self.second[0]}:{self.second[1]}",
            "block_length": self.block_length,
            "suffix_length": self.suffix_length,
            "lhs": self.lhs,
            "rhs": self.rhs,
        }


def local_repairs_for_sequence(sequence: SequenceT) -> Iterable[tuple[int, int, SequenceT]]:
    """Yield repairable same-approach FIFO successor pairs in a sequence."""

    positions = {vehicle: idx for idx, vehicle in enumerate(sequence)}
    for first in sequence:
        second = (first[0], first[1] + 1)
        if second not in positions:
            continue
        first_pos = positions[first]
        second_pos = positions[second]
        if second_pos <= first_pos + 1:
            continue
        repaired = (
            sequence[: first_pos + 1]
            + (second,)
            + sequence[first_pos + 1 : second_pos]
            + sequence[second_pos + 1 :]
        )
        yield first_pos, second_pos, repaired


def check_local_repair_sequence(
    instance: Instance,
    sequence: SequenceT,
) -> list[LocalRepairViolation]:
    releases = instance.release_map
    original_delay = total_delay(sequence, releases, instance.hF, instance.hS)
    violations: list[LocalRepairViolation] = []
    for first_pos, second_pos, repaired in local_repairs_for_sequence(sequence):
        repaired_delay = total_delay(repaired, releases, instance.hF, instance.hS)
        first = sequence[first_pos]
        second = sequence[second_pos]
        release_gap = releases[second] - releases[first]
        block_length = second_pos - first_pos - 1
        suffix_length = len(sequence) - second_pos - 1
        m_value = block_length + suffix_length + 1
        rhs = m_value * max(release_gap - instance.hF, 0) - 2 * (instance.hS - instance.hF)
        lhs = repaired_delay - original_delay
        if lhs > rhs:
            violations.append(
                LocalRepairViolation(
                    instance=instance,
                    sequence=sequence,
                    repaired_sequence=repaired,
                    first=first,
                    second=second,
                    block_length=block_length,
                    suffix_length=suffix_length,
                    lhs=lhs,
                    rhs=rhs,
                )
            )
    return violations
