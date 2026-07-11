"""Plot integrated frontier experiment outputs."""

from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path

FIGSIZE = (4.8, 3.2)
LABEL_FONTSIZE = 11
TICK_FONTSIZE = 10
LEGEND_FONTSIZE = 11
GRID_ALPHA = 0.24

METHOD_COLORS = ["#6B8F7C", "#9A6A5C", "#8C84A3", "#B79A73"]
METHOD_FILLS = ["#B7CDBE", "#D4B4A7", "#C9C1D9", "#D4C2A3"]


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def plot_suite(input_dir: Path) -> None:
    os.environ.setdefault("MPLCONFIGDIR", str(input_dir / ".mplconfig"))
    import matplotlib.pyplot as plt

    frontier = read_rows(input_dir / "dimension_loss_frontier.csv")
    summary = read_rows(input_dir / "summary.csv")
    comparison = read_rows(input_dir / "comparison_runtime.csv")

    fig, ax = plt.subplots(figsize=FIGSIZE)
    for budget_index, (budget_type, marker) in enumerate((("loss_budget", "o"), ("size_budget", "s"))):
        rows = [row for row in frontier if row["budget_type"] == budget_type]
        ax.scatter(
            [float(row["ordering_variables"]) for row in rows],
            [float(row["indexed_bound"]) for row in rows],
            marker=marker,
            alpha=0.8,
            s=28,
            color=METHOD_COLORS[budget_index],
            label=f"{budget_type}: bound",
        )
        ax.scatter(
            [float(row["ordering_variables"]) for row in rows],
            [float(row["actual_average_gap"]) for row in rows],
            marker=marker,
            alpha=0.5,
            s=28,
            color=METHOD_FILLS[budget_index],
            label=f"{budget_type}: actual gap",
        )
    ax.set_xlabel("Ordering variables C(Pi)", fontsize=LABEL_FONTSIZE)
    ax.set_ylabel("Average delay loss", fontsize=LABEL_FONTSIZE)
    ax.tick_params(axis="both", labelsize=TICK_FONTSIZE)
    ax.grid(True, linewidth=0.5, alpha=GRID_ALPHA)
    ax.legend(frameon=False, fontsize=LEGEND_FONTSIZE)
    fig.tight_layout()
    fig.savefig(input_dir / "dimension_loss_frontier.png", dpi=300)
    plt.close(fig)

    methods = sorted({row["method"] for row in summary})
    mean_c = []
    mean_gap = []
    mean_bound = []
    for method in methods:
        rows = [row for row in summary if row["method"] == method]
        mean_c.append(sum(float(row["mean_ordering_variables"]) for row in rows) / len(rows))
        mean_gap.append(sum(float(row["mean_actual_average_gap"]) for row in rows) / len(rows))
        mean_bound.append(sum(float(row["mean_indexed_bound"]) for row in rows) / len(rows))

    fig, ax = plt.subplots(figsize=FIGSIZE)
    ax.scatter(mean_c, mean_bound, label="Mean indexed bound", marker="o", s=46, color=METHOD_COLORS[0])
    ax.scatter(mean_c, mean_gap, label="Mean actual gap", marker="s", s=46, color=METHOD_COLORS[1])
    for method, x, y in zip(methods, mean_c, mean_bound, strict=True):
        ax.annotate(method.replace("_", "\n"), (x, y), fontsize=TICK_FONTSIZE, xytext=(3, 3), textcoords="offset points")
    ax.set_xlabel("Mean ordering variables C(Pi)", fontsize=LABEL_FONTSIZE)
    ax.set_ylabel("Average delay loss", fontsize=LABEL_FONTSIZE)
    ax.tick_params(axis="both", labelsize=TICK_FONTSIZE)
    ax.grid(True, linewidth=0.5, alpha=GRID_ALPHA)
    ax.legend(frameon=False, fontsize=LEGEND_FONTSIZE)
    fig.tight_layout()
    fig.savefig(input_dir / "method_comparison.png", dpi=300)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=FIGSIZE)
    for index, method in enumerate(methods):
        rows = [row for row in comparison if row["method"] == method]
        ax.scatter(
            [float(row["ordering_variables"]) for row in rows],
            [float(row["runtime_seconds"]) for row in rows],
            s=18,
            alpha=0.65,
            color=METHOD_COLORS[index % len(METHOD_COLORS)],
            label=method,
        )
    ax.set_xlabel("Ordering variables C(Pi)", fontsize=LABEL_FONTSIZE)
    ax.set_ylabel("Gurobi runtime (seconds)", fontsize=LABEL_FONTSIZE)
    ax.tick_params(axis="both", labelsize=TICK_FONTSIZE)
    ax.grid(True, linewidth=0.5, alpha=GRID_ALPHA)
    ax.legend(frameon=False, fontsize=LEGEND_FONTSIZE)
    fig.tight_layout()
    fig.savefig(input_dir / "runtime_vs_dimension.png", dpi=300)
    plt.close(fig)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_dir", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    plot_suite(args.input_dir)
    print(args.input_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
