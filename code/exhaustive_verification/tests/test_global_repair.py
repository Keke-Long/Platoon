from __future__ import annotations

from enumerate_partitions import enumerate_partitions
from enumerate_sequences import enumerate_fifo_sequences, enumerate_platoon_sequences
from global_repair import repair_sequence_to_partition, validate_repair_result
from model import (
    Instance,
    optimum_for_sequences,
    scaled_index_free_bound,
    scaled_indexed_bound,
    total_delay,
)


def assert_repair_valid(instance: Instance, sequence, partition) -> None:
    result = repair_sequence_to_partition(instance, sequence, partition)
    validate_repair_result(instance, sequence, partition, result)


def test_global_repair_handles_empty_prefix_and_single_vehicle_block() -> None:
    instance = Instance(counts=(2, 1), releases=((0, 3), (1,)), hF=1, hS=2)
    sequence = ((1, 1), (2, 1), (1, 2))
    partition = ((2,), (1,))
    result = repair_sequence_to_partition(instance, sequence, partition)
    validate_repair_result(instance, sequence, partition, result)
    assert result.records[0].predecessor_position == 0
    assert result.records[0].block_length == 1
    assert result.records[0].suffix_length == 0


def test_global_repair_all_singleton_partition_has_no_records() -> None:
    instance = Instance(counts=(2, 2), releases=((0, 2), (1, 3)), hF=1, hS=3)
    sequence = ((1, 1), (2, 1), (1, 2), (2, 2))
    partition = ((1, 1), (1, 1))
    result = repair_sequence_to_partition(instance, sequence, partition)
    validate_repair_result(instance, sequence, partition, result)
    assert result.records == ()
    assert result.final_sequence == sequence


def test_global_repair_one_approach_sequence_is_already_platoon_feasible() -> None:
    instance = Instance(counts=(4,), releases=((0, 1, 4, 5),), hF=1, hS=3)
    sequence = ((1, 1), (1, 2), (1, 3), (1, 4))
    partition = ((4,),)
    result = repair_sequence_to_partition(instance, sequence, partition)
    validate_repair_result(instance, sequence, partition, result)
    assert result.records == ()


def test_global_repair_three_vehicle_platoon_and_multiple_approaches() -> None:
    instance = Instance(counts=(3, 3), releases=((0, 2, 5), (0, 3, 6)), hF=1, hS=3)
    sequence = ((1, 1), (2, 1), (1, 2), (2, 2), (1, 3), (2, 3))
    partition = ((3,), (3,))
    result = repair_sequence_to_partition(instance, sequence, partition)
    validate_repair_result(instance, sequence, partition, result)
    assert 1 < len(result.records) <= 4
    assert result.final_sequence in tuple(enumerate_platoon_sequences(partition))
    assert all(record.local_delay_change <= record.local_bound for record in result.records)
    assert all(record.m_e <= record.indexed_affected_count_bound for record in result.records)


def test_indexed_zero_loss_threshold_equality_and_above_threshold() -> None:
    equality = Instance(counts=(1, 2), releases=((1,), (0, 2)), hF=1, hS=2)
    above = Instance(counts=(1, 2), releases=((1,), (0, 3)), hF=1, hS=2)
    partition = ((1,), (2,))
    assert scaled_indexed_bound(equality, partition) == 0
    assert scaled_indexed_bound(above, partition) == 2


def test_hf_not_one_instance() -> None:
    instance = Instance(counts=(2, 2), releases=((0, 5), (1, 7)), hF=2, hS=5)
    releases = instance.release_map
    unrestricted = optimum_for_sequences(
        enumerate_fifo_sequences(instance.counts),
        releases,
        instance.hF,
        instance.hS,
    )
    partition = ((2,), (2,))
    platoon = optimum_for_sequences(
        enumerate_platoon_sequences(partition),
        releases,
        instance.hF,
        instance.hS,
    )
    scaled_gap = platoon.total_delay - unrestricted.total_delay
    assert 0 <= scaled_gap <= scaled_indexed_bound(instance, partition)
    assert scaled_indexed_bound(instance, partition) <= scaled_index_free_bound(instance, partition)


def test_bound_dominance_on_small_enumerated_domain() -> None:
    for releases_a in ((0, 0), (0, 1), (0, 2)):
        for releases_b in ((0, 0), (0, 1), (0, 2)):
            instance = Instance(counts=(2, 2), releases=(releases_a, releases_b), hF=1, hS=3)
            releases = instance.release_map
            unrestricted = optimum_for_sequences(
                enumerate_fifo_sequences(instance.counts),
                releases,
                instance.hF,
                instance.hS,
            )
            for partition in enumerate_partitions(instance.counts):
                platoon = optimum_for_sequences(
                    enumerate_platoon_sequences(partition),
                    releases,
                    instance.hF,
                    instance.hS,
                )
                scaled_gap = platoon.total_delay - unrestricted.total_delay
                scaled_indexed = scaled_indexed_bound(instance, partition)
                scaled_index_free = scaled_index_free_bound(instance, partition)
                assert 0 <= scaled_gap
                assert scaled_gap <= scaled_indexed
                assert scaled_indexed <= scaled_index_free
                assert_repair_valid(instance, unrestricted.sequences[0], partition)
