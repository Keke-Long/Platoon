from __future__ import annotations

from model import (
    Instance,
    completion_times,
    optimum_for_sequences,
    scaled_candidate_bound,
    scaled_index_free_bound,
    scaled_indexed_bound,
    total_delay,
)
from enumerate_sequences import enumerate_fifo_sequences, enumerate_platoon_sequences


def test_completion_recursion_uses_actual_predecessor_passing_time() -> None:
    releases = {(1, 1): 0, (2, 1): 0, (1, 2): 1}
    sequence = ((1, 1), (2, 1), (1, 2))
    completions = completion_times(sequence, releases, hF=1, hS=3)
    assert completions == {(1, 1): 0, (2, 1): 3, (1, 2): 6}
    assert total_delay(sequence, releases, hF=1, hS=3) == 8


def test_scaled_candidate_bound_uses_exact_integer_form() -> None:
    instance = Instance(counts=(2, 1), releases=((0, 4), (0,)), hF=1, hS=3)
    partition = ((2,), (1,))
    assert scaled_candidate_bound(instance, partition) == 5
    assert scaled_index_free_bound(instance, partition) == 5
    assert scaled_indexed_bound(instance, partition) == 2


def test_tight_indexed_equality_example() -> None:
    instance = Instance(counts=(1, 2), releases=((1,), (0, 3)), hF=1, hS=2)
    releases = instance.release_map
    unrestricted = optimum_for_sequences(
        enumerate_fifo_sequences(instance.counts),
        releases,
        instance.hF,
        instance.hS,
    )
    partition = ((1,), (2,))
    platoon = optimum_for_sequences(
        enumerate_platoon_sequences(partition),
        releases,
        instance.hF,
        instance.hS,
    )
    scaled_gap = platoon.total_delay - unrestricted.total_delay
    assert unrestricted.total_delay == 2
    assert platoon.total_delay == 4
    assert scaled_gap == 2
    assert scaled_indexed_bound(instance, partition) == 2
    assert scaled_index_free_bound(instance, partition) == 4


def test_indexed_bound_uses_approach_fifo_indices_not_global_positions() -> None:
    instance = Instance(
        counts=(3, 3),
        releases=((0, 4, 8), (0, 5, 9)),
        hF=1,
        hS=2,
    )
    partition = ((3,), (3,))
    assert scaled_indexed_bound(instance, partition) == 51
    assert scaled_index_free_bound(instance, partition) == 70


def test_all_singleton_partition_has_zero_gap() -> None:
    instance = Instance(counts=(2, 2), releases=((0, 3), (1, 2)), hF=1, hS=3)
    releases = instance.release_map
    unrestricted = optimum_for_sequences(
        enumerate_fifo_sequences(instance.counts),
        releases,
        instance.hF,
        instance.hS,
    )
    singleton_partition = ((1, 1), (1, 1))
    platoon = optimum_for_sequences(
        enumerate_platoon_sequences(singleton_partition),
        releases,
        instance.hF,
        instance.hS,
    )
    assert platoon.total_delay == unrestricted.total_delay
    assert scaled_candidate_bound(instance, singleton_partition) == 0
    assert scaled_indexed_bound(instance, singleton_partition) == 0


def test_one_vehicle_per_approach_has_zero_gap() -> None:
    instance = Instance(counts=(1, 1, 1), releases=((0,), (0,), (0,)), hF=1, hS=3)
    releases = instance.release_map
    unrestricted = optimum_for_sequences(
        enumerate_fifo_sequences(instance.counts),
        releases,
        instance.hF,
        instance.hS,
    )
    partition = ((1,), (1,), (1,))
    platoon = optimum_for_sequences(
        enumerate_platoon_sequences(partition),
        releases,
        instance.hF,
        instance.hS,
    )
    assert platoon.total_delay == unrestricted.total_delay
    assert scaled_candidate_bound(instance, partition) == 0
    assert scaled_indexed_bound(instance, partition) == 0


def test_internal_gaps_no_greater_than_hf_zero_bound_sample() -> None:
    instance = Instance(counts=(2, 2), releases=((0, 1), (0, 1)), hF=1, hS=3)
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
    assert scaled_candidate_bound(instance, partition) == 0
    assert scaled_indexed_bound(instance, partition) == 0
    assert platoon.total_delay == unrestricted.total_delay


def test_identical_release_times_case() -> None:
    instance = Instance(counts=(3, 2), releases=((0, 0, 0), (0, 0)), hF=1, hS=4)
    releases = instance.release_map
    unrestricted = optimum_for_sequences(
        enumerate_fifo_sequences(instance.counts),
        releases,
        instance.hF,
        instance.hS,
    )
    partition = ((3,), (2,))
    platoon = optimum_for_sequences(
        enumerate_platoon_sequences(partition),
        releases,
        instance.hF,
        instance.hS,
    )
    assert platoon.total_delay >= unrestricted.total_delay
    assert scaled_candidate_bound(instance, partition) == 0
    assert scaled_indexed_bound(instance, partition) == 0
    assert platoon.total_delay == unrestricted.total_delay


def test_large_release_time_slack_case() -> None:
    instance = Instance(counts=(2, 2), releases=((0, 20), (5, 25)), hF=1, hS=3)
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
    assert scaled_gap >= 0
    assert scaled_gap <= scaled_candidate_bound(instance, partition)
    assert scaled_gap <= scaled_indexed_bound(instance, partition)
    assert scaled_indexed_bound(instance, partition) <= scaled_index_free_bound(instance, partition)


def test_no_release_time_slack_case() -> None:
    instance = Instance(counts=(3, 3), releases=((0, 1, 2), (0, 1, 2)), hF=1, hS=4)
    releases = instance.release_map
    unrestricted = optimum_for_sequences(
        enumerate_fifo_sequences(instance.counts),
        releases,
        instance.hF,
        instance.hS,
    )
    partition = ((3,), (3,))
    platoon = optimum_for_sequences(
        enumerate_platoon_sequences(partition),
        releases,
        instance.hF,
        instance.hS,
    )
    scaled_gap = platoon.total_delay - unrestricted.total_delay
    assert scaled_candidate_bound(instance, partition) == 0
    assert scaled_indexed_bound(instance, partition) == 0
    assert scaled_gap == 0


def test_highly_unbalanced_approach_counts_case() -> None:
    instance = Instance(counts=(1, 5), releases=((2,), (0, 1, 3, 4, 8)), hF=1, hS=3)
    releases = instance.release_map
    unrestricted = optimum_for_sequences(
        enumerate_fifo_sequences(instance.counts),
        releases,
        instance.hF,
        instance.hS,
    )
    partition = ((1,), (2, 3))
    platoon = optimum_for_sequences(
        enumerate_platoon_sequences(partition),
        releases,
        instance.hF,
        instance.hS,
    )
    scaled_gap = platoon.total_delay - unrestricted.total_delay
    assert scaled_gap >= 0
    assert scaled_gap <= scaled_candidate_bound(instance, partition)
    assert scaled_gap <= scaled_indexed_bound(instance, partition)
    assert scaled_indexed_bound(instance, partition) <= scaled_index_free_bound(instance, partition)


def test_known_d_below_hs_counterexample_has_positive_gap_but_satisfies_candidate_bound() -> None:
    instance = Instance(
        counts=(2, 10),
        releases=((0, 2), tuple(range(3, 13))),
        hF=1,
        hS=3,
    )
    releases = instance.release_map
    unrestricted = optimum_for_sequences(
        enumerate_fifo_sequences(instance.counts),
        releases,
        instance.hF,
        instance.hS,
    )
    partition = ((2,), (1, 1, 1, 1, 1, 1, 1, 1, 1, 1))
    platoon = optimum_for_sequences(
        enumerate_platoon_sequences(partition),
        releases,
        instance.hF,
        instance.hS,
    )
    scaled_gap = platoon.total_delay - unrestricted.total_delay
    assert unrestricted.total_delay == 13
    assert platoon.total_delay == 20
    assert scaled_gap == 7
    assert scaled_candidate_bound(instance, partition) == 8
    assert scaled_indexed_bound(instance, partition) == 7
    assert scaled_gap > 0
