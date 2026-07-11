from __future__ import annotations

import sys
from pathlib import Path

VERIFY_DIR = Path(__file__).resolve().parents[2] / "exhaustive_verification"
if str(VERIFY_DIR) not in sys.path:
    sys.path.insert(0, str(VERIFY_DIR))

from model import Instance  # noqa: E402
from metrics import ordering_variables  # noqa: E402
from partition_methods import fixed_size_partition, release_gap_threshold_partition  # noqa: E402
from scalability_suite import choose_largest_feasible_dimension  # noqa: E402


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
