from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("MPLCONFIGDIR", tempfile.mkdtemp(prefix="platoon-mpl-"))

from plot_rule_based_formal_hs3 import (  # noqa: E402
    metric_mean,
    plot_delay_density,
    plot_trajectories,
    pp_metric_groups,
    select_representative_instance,
)


def test_pp_metric_groups_do_not_mix_n_values() -> None:
    rows = [
        {"method": "PP", "N": "20", "delta": "4", "Pmax": "4", "arrival_rate": "0.7", "objective": "10"},
        {"method": "PP", "N": "40", "delta": "4", "Pmax": "4", "arrival_rate": "0.7", "objective": "30"},
    ]
    groups = pp_metric_groups(rows, "objective", x_field="arrival_rate")
    assert groups[(20, 4, 4, 0.7)] == [10.0]
    assert groups[(40, 4, 4, 0.7)] == [30.0]


def test_pp_metric_groups_do_not_mix_pmax_values() -> None:
    rows = [
        {"method": "PP", "N": "20", "delta": "4", "Pmax": "2", "arrival_rate": "0.7", "objective": "10"},
        {"method": "PP", "N": "20", "delta": "4", "Pmax": "8", "arrival_rate": "0.7", "objective": "30"},
    ]
    groups = pp_metric_groups(rows, "objective", x_field="arrival_rate")
    assert groups[(20, 4, 2, 0.7)] == [10.0]
    assert groups[(20, 4, 8, 0.7)] == [30.0]


def test_trajectory_selection_requires_one_complete_instance() -> None:
    rows = [
        {"instance_id": "a", "method": "NP", "delta": "", "Pmax": ""},
        {"instance_id": "a", "method": "CHP", "delta": "4", "Pmax": ""},
        {"instance_id": "b", "method": "NP", "delta": "", "Pmax": ""},
        {"instance_id": "b", "method": "CHP", "delta": "4", "Pmax": ""},
        {"instance_id": "b", "method": "PP", "delta": "4", "Pmax": "4"},
    ]
    assert select_representative_instance(rows) == "b"


def test_plot_trajectories_filters_to_selected_instance() -> None:
    rows = [
        {
            "instance_id": "a",
            "method": "NP",
            "delta": "",
            "Pmax": "",
            "run_role": "initial_30s",
            "time_s": "1",
            "incumbent_average_delay": "10",
        },
        {
            "instance_id": "a",
            "method": "CHP",
            "delta": "4",
            "Pmax": "",
            "run_role": "initial_30s",
            "time_s": "1",
            "incumbent_average_delay": "11",
        },
        {
            "instance_id": "b",
            "method": "NP",
            "delta": "",
            "Pmax": "",
            "run_role": "initial_30s",
            "time_s": "1",
            "incumbent_average_delay": "20",
        },
        {
            "instance_id": "b",
            "method": "CHP",
            "delta": "4",
            "Pmax": "",
            "run_role": "initial_30s",
            "time_s": "1",
            "incumbent_average_delay": "21",
        },
        {
            "instance_id": "b",
            "method": "PP",
            "delta": "4",
            "Pmax": "4",
            "run_role": "initial_30s",
            "time_s": "1",
            "incumbent_average_delay": "22",
        },
    ]
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        plot_trajectories(rows, output_dir)
        metadata = json.loads((output_dir / "gurobi_solution_quality_over_time_metadata.json").read_text())
        assert metadata["selected_instance_id"] == "b"
        assert (output_dir / "gurobi_solution_quality_over_time.png").exists()


def test_missing_data_behavior() -> None:
    assert metric_mean([], "objective", n_value=20, method="PP") is None
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        plot_delay_density([], output_dir)
        assert not (output_dir / "pp_delay_vs_threshold_density.png").exists()
