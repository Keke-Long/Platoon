from __future__ import annotations

from fractions import Fraction

from metrics import (
    cut_bits_from_partition,
    ordering_variables,
    partition_from_cut_bits,
    partition_metrics,
    respects_max_platoon_size,
    vehicle_level_ordering_variables,
)

import sys
from pathlib import Path

VERIFY_DIR = Path(__file__).resolve().parents[2] / "exhaustive_verification"
if str(VERIFY_DIR) not in sys.path:
    sys.path.insert(0, str(VERIFY_DIR))

from model import Instance  # noqa: E402


def test_cut_bits_round_trip() -> None:
    partition = ((2, 1), (1, 3), (1,))
    cuts = cut_bits_from_partition(partition)
    assert cuts == ((0, 1), (1, 0, 0), ())
    assert partition_from_cut_bits(cuts) == partition


def test_ordering_variable_count() -> None:
    assert vehicle_level_ordering_variables((3, 2, 1)) == 11
    assert ordering_variables(((2, 1), (2,), (1,))) == 5


def test_partition_metrics_uses_indexed_bound() -> None:
    instance = Instance(counts=(1, 2), releases=((1,), (0, 3)), hF=1, hS=2)
    partition = ((1,), (2,))
    metrics = partition_metrics(instance, partition)
    assert metrics.scaled_indexed_bound == 2
    assert metrics.indexed_bound == Fraction(2, 3)
    assert metrics.ordering_variables == 1
    assert metrics.vehicle_level_ordering_variables == 2
    assert metrics.dimension_reduction_fraction == Fraction(1, 2)


def test_max_platoon_size_filter() -> None:
    assert respects_max_platoon_size(((2, 1),), 2)
    assert not respects_max_platoon_size(((3,),), 2)

