from __future__ import annotations

import sys
from pathlib import Path

VERIFY_DIR = Path(__file__).resolve().parents[2] / "exhaustive_verification"
if str(VERIFY_DIR) not in sys.path:
    sys.path.insert(0, str(VERIFY_DIR))

from model import Instance  # noqa: E402
from partition_selection import solve_loss_budget_enum, solve_size_budget_enum


def test_loss_budget_selects_smallest_dimension_partition() -> None:
    instance = Instance(counts=(1, 2), releases=((1,), (0, 3)), hF=1, hS=2)
    zero_budget = solve_loss_budget_enum(instance, scaled_loss_budget=0)
    assert zero_budget.partition == ((1,), (1, 1))
    assert zero_budget.ordering_variables == 2

    positive_budget = solve_loss_budget_enum(instance, scaled_loss_budget=2)
    assert positive_budget.partition == ((1,), (2,))
    assert positive_budget.ordering_variables == 1


def test_size_budget_selects_lowest_bound_partition() -> None:
    instance = Instance(counts=(1, 2), releases=((1,), (0, 3)), hF=1, hS=2)
    tight_dimension = solve_size_budget_enum(instance, ordering_budget=1)
    assert tight_dimension.partition == ((1,), (2,))
    assert tight_dimension.scaled_indexed_bound == 2

    loose_dimension = solve_size_budget_enum(instance, ordering_budget=2)
    assert loose_dimension.partition == ((1,), (1, 1))
    assert loose_dimension.scaled_indexed_bound == 0


def test_max_platoon_size_constraint() -> None:
    instance = Instance(counts=(3, 3), releases=((0, 1, 3), (0, 1, 3)), hF=1, hS=2)
    result = solve_loss_budget_enum(instance, scaled_loss_budget=100, max_platoon_size=2)
    assert result.partition is not None
    assert all(block <= 2 for blocks in result.partition for block in blocks)

