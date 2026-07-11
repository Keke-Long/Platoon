"""Build cross-scenario scalability plots and summary tables."""

from __future__ import annotations

import argparse
import csv
import json
import os
import statistics
from pathlib import Path

FIGSIZE = (4.8, 3.2)
LABEL_FONTSIZE = 11
TICK_FONTSIZE = 10
LEGEND_FONTSIZE = 11
GRID_ALPHA = 0.24

METHOD_COLORS = {
    "proposed_bound_aware": "#7FAF9A",
    "fixed_size_closest_dimension": "#B7A07A",
    "threshold_closest_dimension": "#9C8FAE",
}

METHOD_EDGES = {
    "proposed_bound_aware": "#557C69",
    "fixed_size_closest_dimension": "#7D6B4A",
    "threshold_closest_dimension": "#6F6480",
}

METHOD_HATCHES = {
    "proposed_bound_aware": "///",
    "fixed_size_closest_dimension": "\\\\\\",
    "threshold_closest_dimension": "...",
}

VEHICLE_LINE = "#5B616B"
VEHICLE_MARKER_FACE = "#D9D4CC"

METHODS = (
    "proposed_bound_aware",
    "fixed_size_closest_dimension",
    "threshold_closest_dimension",
)

METHOD_LABELS = {
    "proposed_bound_aware": "Proposed",
    "fixed_size_closest_dimension": "Fixed size",
    "threshold_closest_dimension": "Threshold",
}


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def mean(values: list[float]) -> float | None:
    if not values:
        return None
    return statistics.fmean(values)


def summarize_scenario(name: str, root: Path) -> tuple[list[dict[str, object]], dict[str, object]]:
    rows = read_rows(root / "fair_dimension_comparison.csv")
    vehicle_row = read_rows(root / "vehicle_level_summary.csv")[0]
    scenario_rows: list[dict[str, object]] = []
    vehicle_c = int(rows[0]["vehicle_level_ordering_variables"])
    for method in METHODS:
        subset = [row for row in rows if row["method_family"] == method]
        time_limit_rows = [row for row in subset if row["status"] == "TIME_LIMIT"]
        scenario_rows.append(
            {
                "scenario": name,
                "N": int(subset[0]["N"]),
                "method_family": method,
                "method_label": METHOD_LABELS[method],
                "vehicle_level_ordering_variables": vehicle_c,
                "mean_ordering_variables": mean([float(row["ordering_variables"]) for row in subset]),
                "mean_dimension_reduction_fraction": mean([float(row["dimension_reduction_fraction"]) for row in subset]),
                "optimality_rate": mean([1.0 if row["status"] == "OPTIMAL" else 0.0 for row in subset]),
                "mean_end_to_end_seconds": mean([float(row["end_to_end_seconds"]) for row in subset]),
                "mean_nodes": mean([float(row["nodes"]) for row in subset]),
                "mean_mip_gap": mean([float(row["mip_gap"]) for row in subset if row["mip_gap"] not in ("", None)]),
                "mean_indexed_bound": mean([float(row["indexed_bound"]) for row in subset]),
                "mean_objective_average_delay": mean(
                    [float(row["objective_average_delay"]) for row in subset if row["objective_average_delay"] not in ("", None)]
                ),
                "time_limit_case_count": len(time_limit_rows),
                "time_limit_mean_objective_average_delay": mean(
                    [float(row["objective_average_delay"]) for row in time_limit_rows if row["objective_average_delay"] not in ("", None)]
                ),
                "time_limit_mean_mip_gap": mean(
                    [float(row["mip_gap"]) for row in time_limit_rows if row["mip_gap"] not in ("", None)]
                ),
                "optimal_count": sum(1 for row in subset if row["status"] == "OPTIMAL"),
                "time_limit_count": sum(1 for row in subset if row["status"] == "TIME_LIMIT"),
            }
        )
    vehicle_summary = {
        "scenario": name,
        "N": int(rows[0]["N"]),
        "vehicle_level_ordering_variables": vehicle_c,
        "vehicle_statuses": vehicle_row["statuses"],
        "vehicle_mean_wall_time_seconds": float(vehicle_row["mean_vehicle_level_wall_time_seconds"]),
        "vehicle_mean_nodes": float(vehicle_row["mean_vehicle_level_nodes"]),
        "vehicle_mean_mip_gap": float(vehicle_row["mean_vehicle_level_mip_gap"]),
        "vehicle_optimal_case_count": int(vehicle_row["optimal_case_count"]),
        "vehicle_case_count": int(vehicle_row["cases"]),
    }
    return scenario_rows, vehicle_summary


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def plot_grouped_bars(output_path: Path, data: list[dict[str, object]], field: str, ylabel: str) -> None:
    os.environ.setdefault("MPLCONFIGDIR", str(output_path.parent / ".mplconfig"))
    import matplotlib.pyplot as plt

    scenarios = sorted({str(row["scenario"]) for row in data}, key=lambda name: int(name[1:]))
    x = list(range(len(scenarios)))
    width = 0.22
    fig, ax = plt.subplots(figsize=FIGSIZE)
    for index, method in enumerate(METHODS):
        subset = [row for row in data if row["method_family"] == method]
        subset_by_scenario = {str(row["scenario"]): row for row in subset}
        ax.bar(
            [value + (index - 1) * width for value in x],
            [float(subset_by_scenario[scenario][field]) for scenario in scenarios],
            width=width,
            label=METHOD_LABELS[method],
            color=METHOD_COLORS[method],
            edgecolor=METHOD_EDGES[method],
            linewidth=0.9,
            hatch=METHOD_HATCHES[method],
        )
    ax.set_xticks(x)
    ax.set_xticklabels(scenarios, fontsize=TICK_FONTSIZE)
    ax.set_ylabel(ylabel, fontsize=LABEL_FONTSIZE)
    ax.tick_params(axis="y", labelsize=TICK_FONTSIZE)
    ax.grid(axis="y", linewidth=0.5, alpha=GRID_ALPHA)
    ax.legend(frameon=False, fontsize=LEGEND_FONTSIZE)
    fig.tight_layout()
    fig.savefig(output_path, dpi=300)
    plt.close(fig)


def plot_dimension_reduction(output_path: Path, data: list[dict[str, object]], vehicle_rows: list[dict[str, object]]) -> None:
    os.environ.setdefault("MPLCONFIGDIR", str(output_path.parent / ".mplconfig"))
    import matplotlib.pyplot as plt

    scenarios = sorted({str(row["scenario"]) for row in data}, key=lambda name: int(name[1:]))
    x = list(range(len(scenarios)))
    width = 0.22
    fig, ax = plt.subplots(figsize=FIGSIZE)
    for index, method in enumerate(METHODS):
        subset = [row for row in data if row["method_family"] == method]
        subset_by_scenario = {str(row["scenario"]): row for row in subset}
        ax.bar(
            [value + (index - 1) * width for value in x],
            [float(subset_by_scenario[scenario]["mean_ordering_variables"]) for scenario in scenarios],
            width=width,
            label=METHOD_LABELS[method],
            color=METHOD_COLORS[method],
            edgecolor=METHOD_EDGES[method],
            linewidth=0.9,
            hatch=METHOD_HATCHES[method],
        )
    vehicle_by_scenario = {str(row["scenario"]): row for row in vehicle_rows}
    ax.plot(
        x,
        [float(vehicle_by_scenario[scenario]["vehicle_level_ordering_variables"]) for scenario in scenarios],
        color=VEHICLE_LINE,
        marker="o",
        markerfacecolor=VEHICLE_MARKER_FACE,
        markeredgecolor=VEHICLE_LINE,
        markersize=5.5,
        linewidth=1.8,
        label="Vehicle level",
    )
    ax.set_xticks(x)
    ax.set_xticklabels(scenarios, fontsize=TICK_FONTSIZE)
    ax.set_ylabel("Mean ordering variables", fontsize=LABEL_FONTSIZE)
    ax.tick_params(axis="y", labelsize=TICK_FONTSIZE)
    ax.grid(axis="y", linewidth=0.5, alpha=GRID_ALPHA)
    ax.legend(frameon=False, ncol=2, fontsize=LEGEND_FONTSIZE)
    fig.tight_layout()
    fig.savefig(output_path, dpi=300)
    plt.close(fig)


def build_artifacts(output_dir: Path, scenario_dirs: dict[str, Path]) -> dict[str, object]:
    data: list[dict[str, object]] = []
    vehicle_rows: list[dict[str, object]] = []
    for scenario, root in scenario_dirs.items():
        scenario_rows, vehicle_summary = summarize_scenario(scenario, root)
        data.extend(scenario_rows)
        vehicle_rows.append(vehicle_summary)

    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "fair_method_comparison.csv", data)
    write_csv(output_dir / "vehicle_level_scalability_summary.csv", vehicle_rows)
    write_csv(
        output_dir / "time_limit_incumbent_summary.csv",
        [
            {
                "scenario": row["scenario"],
                "method_label": row["method_label"],
                "time_limit_case_count": row["time_limit_case_count"],
                "time_limit_mean_objective_average_delay": row["time_limit_mean_objective_average_delay"],
                "time_limit_mean_mip_gap": row["time_limit_mean_mip_gap"],
            }
            for row in data
        ],
    )

    plot_dimension_reduction(output_dir / "dimension_reduction_by_scale.png", data, vehicle_rows)
    plot_grouped_bars(output_dir / "optimality_rate_by_scale.png", data, "optimality_rate", "Optimality rate")
    plot_grouped_bars(output_dir / "mip_gap_by_scale.png", data, "mean_mip_gap", "Mean MIP gap")
    plot_grouped_bars(output_dir / "runtime_by_scale.png", data, "mean_end_to_end_seconds", "Mean end-to-end seconds")
    plot_grouped_bars(output_dir / "nodes_by_scale.png", data, "mean_nodes", "Mean branch-and-bound nodes")

    payload = {
        "scenario_count": len(scenario_dirs),
        "row_count": len(data),
        "vehicle_row_count": len(vehicle_rows),
        "scenarios": sorted(scenario_dirs),
    }
    (output_dir / "artifact_manifest.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n20-dir", type=Path, required=True)
    parser.add_argument("--n30-dir", type=Path, required=True)
    parser.add_argument("--n40-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    payload = build_artifacts(
        args.output_dir,
        {
            "N20": args.n20_dir,
            "N30": args.n30_dir,
            "N40": args.n40_dir,
        },
    )
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
