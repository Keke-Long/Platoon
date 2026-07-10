"""FIFO vehicle and platoon sequence enumeration."""

from __future__ import annotations

from collections.abc import Iterator, Sequence

from model import ApproachPartition, Partition, SequenceT, Vehicle


def enumerate_fifo_sequences(counts: Sequence[int]) -> Iterator[SequenceT]:
    """Yield every FIFO-preserving interleaving of approach queues."""

    counts_tuple = tuple(counts)
    next_indices = [1] * len(counts_tuple)
    remaining = list(counts_tuple)
    prefix: list[Vehicle] = []

    def rec() -> Iterator[SequenceT]:
        if len(prefix) == sum(counts_tuple):
            yield tuple(prefix)
            return
        for approach in range(1, len(counts_tuple) + 1):
            idx = approach - 1
            if remaining[idx] == 0:
                continue
            vehicle = (approach, next_indices[idx])
            prefix.append(vehicle)
            next_indices[idx] += 1
            remaining[idx] -= 1
            yield from rec()
            remaining[idx] += 1
            next_indices[idx] -= 1
            prefix.pop()

    yield from rec()


def _approach_blocks(
    approach: int, approach_partition: ApproachPartition
) -> tuple[tuple[Vehicle, ...], ...]:
    blocks: list[tuple[Vehicle, ...]] = []
    next_vehicle = 1
    for block_size in approach_partition:
        block = tuple((approach, index) for index in range(next_vehicle, next_vehicle + block_size))
        blocks.append(block)
        next_vehicle += block_size
    return tuple(blocks)


def enumerate_platoon_sequences(partition: Partition) -> Iterator[SequenceT]:
    """Yield FIFO sequences in which each partition block is contiguous."""

    block_counts = tuple(len(approach_partition) for approach_partition in partition)
    approach_blocks = tuple(
        _approach_blocks(approach, approach_partition)
        for approach, approach_partition in enumerate(partition, start=1)
    )
    for unit_sequence in enumerate_fifo_sequences(block_counts):
        expanded: list[Vehicle] = []
        for approach, platoon_index in unit_sequence:
            expanded.extend(approach_blocks[approach - 1][platoon_index - 1])
        yield tuple(expanded)


def is_platoon_sequence(sequence: Sequence[Vehicle], partition: Partition) -> bool:
    """Check whether every partition block occupies consecutive positions."""

    position = {vehicle: idx for idx, vehicle in enumerate(sequence)}
    for approach, approach_partition in enumerate(partition, start=1):
        next_vehicle = 1
        for block_size in approach_partition:
            vehicles = [
                (approach, index)
                for index in range(next_vehicle, next_vehicle + block_size)
            ]
            positions = [position[vehicle] for vehicle in vehicles]
            if positions != list(range(positions[0], positions[0] + block_size)):
                return False
            next_vehicle += block_size
    return True

