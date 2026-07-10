from __future__ import annotations

from enumerate_partitions import enumerate_approach_partitions, enumerate_partitions
from enumerate_sequences import (
    enumerate_fifo_sequences,
    enumerate_platoon_sequences,
    is_platoon_sequence,
)
from model import is_fifo_sequence


def test_fifo_sequence_enumeration_preserves_order_and_count() -> None:
    sequences = tuple(enumerate_fifo_sequences((2, 1)))
    assert len(sequences) == 3
    assert all(is_fifo_sequence(sequence, (2, 1)) for sequence in sequences)
    assert sequences == (
        ((1, 1), (1, 2), (2, 1)),
        ((1, 1), (2, 1), (1, 2)),
        ((2, 1), (1, 1), (1, 2)),
    )


def test_approach_partition_enumeration_uses_contiguous_block_sizes() -> None:
    assert tuple(enumerate_approach_partitions(3)) == (
        (3,),
        (1, 2),
        (2, 1),
        (1, 1, 1),
    )


def test_full_partition_count_is_product_of_binary_cut_choices() -> None:
    partitions = tuple(enumerate_partitions((3, 2)))
    assert len(partitions) == 4 * 2


def test_platoon_sequence_enumeration_keeps_blocks_contiguous() -> None:
    partition = ((2,), (1, 1))
    sequences = tuple(enumerate_platoon_sequences(partition))
    assert len(sequences) == 3
    assert all(is_platoon_sequence(sequence, partition) for sequence in sequences)
    assert ((1, 1), (2, 1), (1, 2), (2, 2)) not in sequences

