from __future__ import annotations

import sys
from pathlib import Path

VERIFY_DIR = Path(__file__).resolve().parents[2] / "exhaustive_verification"
if str(VERIFY_DIR) not in sys.path:
    sys.path.insert(0, str(VERIFY_DIR))

from model import Instance  # noqa: E402
from partition_methods import fixed_size_partition, release_gap_threshold_partition


def test_fixed_size_partition() -> None:
    assert fixed_size_partition((5, 3), 2) == ((2, 2, 1), (2, 1))


def test_release_gap_threshold_partition() -> None:
    instance = Instance(counts=(4,), releases=((0, 1, 4, 5),), hF=1, hS=2)
    assert release_gap_threshold_partition(instance, threshold=1) == ((2, 2),)
    assert release_gap_threshold_partition(instance, threshold=10, max_platoon_size=3) == ((3, 1),)

