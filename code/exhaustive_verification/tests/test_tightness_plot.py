from __future__ import annotations

import csv
import json
import tempfile
from pathlib import Path

from plot_bound_tightness import main as plot_bound_tightness_main
from verify_bound import SearchConfig, search


def test_verify_bound_can_save_partition_rows_for_fixed_counts() -> None:
    config = SearchConfig(
        L_values=(3,),
        max_n=2,
        max_total_vehicles=3,
        max_release=1,
        hF=1,
        hS_values=(2,),
        keep_all_optima=False,
        stop_on_counterexample=True,
        check_repair=True,
        exact_counts=(2, 1),
        save_partition_rows=True,
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        stats, counterexample, local_violation = search(config, output_dir)
        assert counterexample is None
        assert local_violation is None
        assert stats.partitions > 0
        row_path = output_dir / "indexed_partition_rows.csv"
        assert row_path.exists()
        with row_path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        assert rows
        assert set(
            [
                "instance_id",
                "dimension_budget",
                "partition",
                "scaled_gap",
                "scaled_indexed_bound",
                "actual_gap",
                "indexed_bound",
            ]
        ).issubset(rows[0].keys())


def test_plot_bound_tightness_produces_summary_and_selection_rows() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        partition_rows = tmp / "partition_rows.csv"
        with partition_rows.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "instance_id",
                    "partition_index",
                    "L",
                    "N",
                    "counts",
                    "releases",
                    "hF",
                    "hS",
                    "dimension_budget",
                    "partition",
                    "scaled_gap",
                    "scaled_indexed_bound",
                    "scaled_index_free_bound",
                    "actual_gap",
                    "indexed_bound",
                    "index_free_bound",
                ],
                lineterminator="\n",
            )
            writer.writeheader()
            rows = [
                {
                    "instance_id": 1,
                    "partition_index": 0,
                    "L": 2,
                    "N": 3,
                    "counts": "[2,1]",
                    "releases": "[[0,1],[0]]",
                    "hF": 1,
                    "hS": 2,
                    "dimension_budget": 1,
                    "partition": "[[2],[1]]",
                    "scaled_gap": 1,
                    "scaled_indexed_bound": 2,
                    "scaled_index_free_bound": 2,
                    "actual_gap": "1/3",
                    "indexed_bound": "2/3",
                    "index_free_bound": "2/3",
                },
                {
                    "instance_id": 1,
                    "partition_index": 1,
                    "L": 2,
                    "N": 3,
                    "counts": "[2,1]",
                    "releases": "[[0,1],[0]]",
                    "hF": 1,
                    "hS": 2,
                    "dimension_budget": 2,
                    "partition": "[[1,1],[1]]",
                    "scaled_gap": 0,
                    "scaled_indexed_bound": 0,
                    "scaled_index_free_bound": 0,
                    "actual_gap": "0/3",
                    "indexed_bound": "0/3",
                    "index_free_bound": "0/3",
                },
                {
                    "instance_id": 2,
                    "partition_index": 0,
                    "L": 2,
                    "N": 3,
                    "counts": "[2,1]",
                    "releases": "[[0,2],[0]]",
                    "hF": 1,
                    "hS": 2,
                    "dimension_budget": 1,
                    "partition": "[[2],[1]]",
                    "scaled_gap": 2,
                    "scaled_indexed_bound": 2,
                    "scaled_index_free_bound": 2,
                    "actual_gap": "2/3",
                    "indexed_bound": "2/3",
                    "index_free_bound": "2/3",
                },
                {
                    "instance_id": 2,
                    "partition_index": 1,
                    "L": 2,
                    "N": 3,
                    "counts": "[2,1]",
                    "releases": "[[0,2],[0]]",
                    "hF": 1,
                    "hS": 2,
                    "dimension_budget": 2,
                    "partition": "[[1,1],[1]]",
                    "scaled_gap": 0,
                    "scaled_indexed_bound": 1,
                    "scaled_index_free_bound": 1,
                    "actual_gap": "0/3",
                    "indexed_bound": "1/3",
                    "index_free_bound": "1/3",
                },
            ]
            for row in rows:
                writer.writerow(row)
        output_dir = tmp / "out"
        import sys

        argv = sys.argv
        try:
            sys.argv = [
                "plot_bound_tightness.py",
                "--partition-rows",
                str(partition_rows),
                "--output-dir",
                str(output_dir),
                "--figure-name",
                "tightness_test",
            ]
            assert plot_bound_tightness_main() == 0
        finally:
            sys.argv = argv

        summary = json.loads((output_dir / "tightness_test_summary.json").read_text(encoding="utf-8"))
        assert summary["violation_rate_fraction"] == "0/4"
        assert summary["positive_equality_cases"] == 1
        assert summary["common_budgets"] == [1, 2]
        selection_rows = list(csv.DictReader((output_dir / "tightness_test_selections.csv").open(encoding="utf-8")))
        assert len(selection_rows) == 4
