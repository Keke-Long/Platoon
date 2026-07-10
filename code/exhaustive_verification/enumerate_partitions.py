"""Contiguous platoon partition enumeration."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from itertools import product

from model import ApproachPartition, Partition


def enumerate_approach_partitions(n: int) -> Iterator[ApproachPartition]:
    """Yield all contiguous partitions of one FIFO queue as block sizes."""

    if n <= 0:
        raise ValueError("approach vehicle count must be positive")
    for cut_mask in range(1 << (n - 1)):
        blocks: list[int] = []
        block_size = 1
        for boundary in range(n - 1):
            if cut_mask & (1 << boundary):
                blocks.append(block_size)
                block_size = 1
            else:
                block_size += 1
        blocks.append(block_size)
        yield tuple(blocks)


def enumerate_partitions(counts: Sequence[int]) -> Iterator[Partition]:
    per_approach = [tuple(enumerate_approach_partitions(count)) for count in counts]
    for partition in product(*per_approach):
        yield tuple(partition)

