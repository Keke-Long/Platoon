from __future__ import annotations

from enumerate_sequences import enumerate_fifo_sequences
from local_repair import check_local_repair_sequence, local_repairs_for_sequence
from model import Instance


def test_local_repair_enumerates_nonadjacent_fifo_successors() -> None:
    sequence = ((1, 1), (2, 1), (2, 2), (1, 2))
    repairs = tuple(local_repairs_for_sequence(sequence))
    assert len(repairs) == 1
    assert repairs[0][2] == ((1, 1), (1, 2), (2, 1), (2, 2))


def test_local_repair_claim_on_small_identical_release_instance() -> None:
    instance = Instance(counts=(2, 2), releases=((0, 0), (0, 0)), hF=1, hS=3)
    violations = []
    for sequence in enumerate_fifo_sequences(instance.counts):
        violations.extend(check_local_repair_sequence(instance, sequence))
    assert violations == []

