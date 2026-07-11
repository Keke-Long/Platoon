from __future__ import annotations

import sys
from pathlib import Path

VERIFY_DIR = Path(__file__).resolve().parents[2] / "exhaustive_verification"
if str(VERIFY_DIR) not in sys.path:
    sys.path.insert(0, str(VERIFY_DIR))

from model import Instance  # noqa: E402
from metrics import ordering_variables  # noqa: E402
from partition_methods import fixed_size_partition, release_gap_threshold_partition  # noqa: E402
from scalability_suite import choose_largest_feasible_dimension, summarize, summarize_vehicle_level  # noqa: E402


def test_baseline_selection_never_exceeds_budget_when_feasible() -> None:
    instance = Instance(counts=(5, 5, 5), releases=((0, 1, 2, 3, 4),) * 3, hF=1, hS=2)
    target_c = 12
    fixed_label, fixed_partition = choose_largest_feasible_dimension(
        [(f"fixed_{size}", fixed_size_partition(instance.counts, size)) for size in range(1, 5)],
        target_c,
    )
    threshold_label, threshold_partition = choose_largest_feasible_dimension(
        [
            (
                f"threshold_{threshold}",
                release_gap_threshold_partition(instance, threshold, max_platoon_size=4),
            )
            for threshold in (0, 1, 2, 10)
        ],
        target_c,
    )
    assert fixed_label
    assert threshold_label
    assert ordering_variables(fixed_partition) <= target_c
    assert ordering_variables(threshold_partition) <= target_c


def test_summary_marks_actual_gap_availability_explicitly() -> None:
    rows = [
        {
            "N": 20,
            "L": 4,
            "demand_pattern": "balanced",
            "arrival_mode": "poisson",
            "target_dimension_reduction": 0.5,
            "method_family": "proposed_bound_aware",
            "end_to_end_seconds": 1.0,
            "partition_time_seconds": 0.2,
            "model_construction_seconds": 0.3,
            "downstream_optimization_seconds": 0.5,
            "actual_average_gap": None,
            "indexed_bound": 1.25,
            "ordering_variables": 12,
            "nodes": 7,
            "status": "OPTIMAL",
            "actual_gap_le_indexed_bound": None,
        }
    ]
    row = summarize(rows)[0]
    assert row["actual_gap_case_count"] == 0
    assert row["all_actual_gaps_within_bound"] == "N/A"


def test_vehicle_level_summary_is_deduplicated_by_instance() -> None:
    base = {
        "scenario": "N20_L4_balanced_poisson_hS2",
        "replication": 0,
        "N": 20,
        "L": 4,
        "counts": [5, 5, 5, 5],
        "demand_pattern": "balanced",
        "arrival_mode": "poisson",
        "hF": 1,
        "hS": 2,
        "max_platoon_size": 4,
        "vehicle_level_ordering_variables": 79,
        "vehicle_level_average_delay": None,
        "vehicle_level_incumbent_average_delay": 12.5,
        "vehicle_level_status": "TIME_LIMIT",
        "vehicle_level_mip_gap": 0.15,
        "vehicle_level_nodes": 123,
        "vehicle_level_time_to_first_feasible": 0.8,
        "vehicle_level_model_construction_seconds": 0.1,
        "vehicle_level_downstream_optimization_seconds": 30.0,
        "vehicle_level_wall_time_seconds": 30.2,
    }
    rows = [
        dict(base, target_dimension_reduction=0.25, method_family="proposed_bound_aware"),
        dict(base, target_dimension_reduction=0.50, method_family="fixed_size_closest_dimension"),
    ]
    summary = summarize_vehicle_level(rows)
    assert len(summary) == 1
    assert summary[0]["cases"] == 1
    assert summary[0]["statuses"] == '{"TIME_LIMIT": 1}'
