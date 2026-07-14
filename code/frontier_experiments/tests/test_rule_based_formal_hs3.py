from __future__ import annotations

import json
import tempfile
from pathlib import Path

from rule_based_formal_hs3 import (
    FormalHS3Config,
    canonical_average_delay,
    load_checkpoints,
    refresh_numerical_checks,
)


def test_optimal_delay_is_canonicalized_to_integer_total_delay() -> None:
    raw_pp_objective = 3.066636482640691
    row = {
        "N": 60,
        "method": "PP",
        "objective": raw_pp_objective,
        "np_optimal_objective": 3.066666666666667,
        "pp_optimal_objective": raw_pp_objective,
        "matching_chp_objective": 3.0666665845740755,
        "rule_level_upper_bound": 27.5,
    }

    refresh_numerical_checks([row])

    assert row["objective"] == raw_pp_objective
    assert row["np_optimal_objective"] == 184 / 60
    assert row["pp_optimal_objective"] == 184 / 60
    assert row["matching_chp_objective"] == 184 / 60
    assert row["actual_optimality_gap"] == 0.0
    assert row["bound_valid"] is True
    assert row["np_pp_chp_delay_order_holds"] is True


def test_canonical_average_delay_uses_vehicle_count_lattice() -> None:
    assert canonical_average_delay(2.3749992619071123, 40) == 95 / 40


def test_checkpoint_loading_filters_unrequested_scales() -> None:
    with tempfile.TemporaryDirectory() as temporary_dir:
        tmp_path = Path(temporary_dir)
        checkpoint_dir = tmp_path / "checkpoints"
        checkpoint_dir.mkdir()
        for n_value in (20, 60):
            payload = {
                "instance": {"N": n_value, "arrival_rate": 0.5, "replication": 0},
                "rows": [{"N": n_value}],
                "trajectory_rows": [{"N": n_value}],
            }
            (checkpoint_dir / f"N{n_value}.json").write_text(json.dumps(payload), encoding="utf-8")
        config = FormalHS3Config(
            seed=1,
            reps=10,
            n_values=(20,),
            approaches=4,
            arrival_rates=(0.5,),
            thresholds=(2,),
            max_platoon_sizes=(2,),
            hF=1,
            hS=3,
            time_limit=600.0,
            threads=1,
            formation_repetitions=1,
            bound_output_dir=str(tmp_path / "bound"),
            comparison_output_dir=str(tmp_path),
            write_trajectory=True,
            trajectory_output_dir=str(tmp_path),
            representative_threshold=2,
            representative_max_platoon_size=2,
        )

        rows, trajectories, completed = load_checkpoints(config)

        assert rows == [{"N": 20}]
        assert trajectories == [{"N": 20}]
        assert completed == {(20, 0.5, 0)}
