from __future__ import annotations

from random_verify import RandomConfig, RandomStats
from verify_bound import SearchConfig, SearchStats


def test_deterministic_stats_split_positive_and_zero_equality_cases() -> None:
    stats = SearchStats()
    stats.record_case(scaled_gap=0, scaled_indexed=0, scaled_index_free=0)
    stats.record_case(scaled_gap=2, scaled_indexed=2, scaled_index_free=4)
    assert stats.zero_equality_cases == 1
    assert stats.positive_equality_cases == 1
    config = SearchConfig(
        L_values=(2,),
        max_n=2,
        max_total_vehicles=4,
        max_release=3,
        hF=1,
        hS_values=(2,),
        keep_all_optima=True,
        stop_on_counterexample=True,
        check_repair=True,
    )
    assert stats.to_json(config=config)["total_equality_cases"] == 2


def test_random_stats_split_positive_and_zero_equality_cases() -> None:
    stats = RandomStats()
    stats.record_case(scaled_gap=0, scaled_indexed=0, scaled_index_free=0)
    stats.record_case(scaled_gap=3, scaled_indexed=3, scaled_index_free=5)
    assert stats.zero_equality_cases == 1
    assert stats.positive_equality_cases == 1
    config = RandomConfig(
        seed=1,
        samples=1,
        L_values=(2,),
        max_n=2,
        max_total_vehicles=4,
        max_release=3,
        hF=1,
        hS_values=(2,),
        partitions_per_instance=1,
        check_repair=True,
    )
    assert stats.to_json(config=config)["total_equality_cases"] == 2
