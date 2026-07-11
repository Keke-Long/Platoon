"""Plot practical tightness of the indexed bound from exact partition rows."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from statistics import quantiles

import matplotlib.pyplot as plt


@dataclass(frozen=True)
class PartitionRow:
    instance_id: int
    partition_index: int
    N: int
    dimension_budget: int
    partition: tuple[tuple[int, ...], ...]
    scaled_gap: int
    scaled_indexed_bound: int


@dataclass(frozen=True)
class SelectionRow:
    instance_id: int
    dimension_budget: int
    bound_partition_index: int
    oracle_partition_index: int
    bound_dimension: int
    oracle_dimension: int
    bound_scaled_gap: int
    oracle_scaled_gap: int
    bound_scaled_indexed_bound: int
    oracle_scaled_indexed_bound: int

    def to_csv_row(self, n: int) -> dict[str, object]:
        return {
            "instance_id": self.instance_id,
            "dimension_budget": self.dimension_budget,
            "bound_partition_index": self.bound_partition_index,
            "oracle_partition_index": self.oracle_partition_index,
            "bound_dimension": self.bound_dimension,
            "oracle_dimension": self.oracle_dimension,
            "bound_scaled_gap": self.bound_scaled_gap,
            "oracle_scaled_gap": self.oracle_scaled_gap,
            "bound_scaled_indexed_bound": self.bound_scaled_indexed_bound,
            "oracle_scaled_indexed_bound": self.oracle_scaled_indexed_bound,
            "bound_actual_gap": f"{self.bound_scaled_gap}/{n}",
            "oracle_actual_gap": f"{self.oracle_scaled_gap}/{n}",
            "selection_regret": f"{self.bound_scaled_gap - self.oracle_scaled_gap}/{n}",
        }


def parse_partition(value: str) -> tuple[tuple[int, ...], ...]:
    return tuple(tuple(blocks) for blocks in json.loads(value))


def read_rows(path: Path) -> list[PartitionRow]:
    rows: list[PartitionRow] = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for raw in reader:
            rows.append(
                PartitionRow(
                    instance_id=int(raw["instance_id"]),
                    partition_index=int(raw["partition_index"]),
                    N=int(raw["N"]),
                    dimension_budget=int(raw["dimension_budget"]),
                    partition=parse_partition(raw["partition"]),
                    scaled_gap=int(raw["scaled_gap"]),
                    scaled_indexed_bound=int(raw["scaled_indexed_bound"]),
                )
            )
    if not rows:
        raise ValueError("partition row file is empty")
    return rows


def partition_sort_key(row: PartitionRow) -> tuple[tuple[int, ...], ...]:
    return row.partition


def quartiles(values: list[float]) -> tuple[float, float]:
    if len(values) == 1:
        return values[0], values[0]
    q1, _, q3 = quantiles(values, n=4, method="inclusive")
    return q1, q3


def mean_fraction(values: list[Fraction]) -> Fraction:
    return sum(values, start=Fraction(0, 1)) / len(values)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--partition-rows", required=True, help="CSV emitted by verify_bound.py")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--figure-name", default="indexed_bound_tightness")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    rows = read_rows(Path(args.partition_rows))
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    grouped: dict[int, list[PartitionRow]] = defaultdict(list)
    for row in rows:
        grouped[row.instance_id].append(row)

    n_values = {row.N for row in rows}
    if len(n_values) != 1:
        raise ValueError("all rows must share the same N for a common-budget tightness plot")
    n = next(iter(n_values))

    common_budgets: set[int] | None = None
    violation_count = 0
    positive_equality_cases = 0
    total_rows = len(rows)
    for instance_rows in grouped.values():
        budgets = {row.dimension_budget for row in instance_rows}
        common_budgets = budgets if common_budgets is None else (common_budgets & budgets)
        for row in instance_rows:
            if row.scaled_gap > row.scaled_indexed_bound:
                violation_count += 1
            if row.scaled_gap == row.scaled_indexed_bound and row.scaled_gap > 0:
                positive_equality_cases += 1
    if not common_budgets:
        raise ValueError("no common budgets found across instances")

    selection_rows: list[SelectionRow] = []
    bound_curve: dict[int, list[Fraction]] = defaultdict(list)
    oracle_curve: dict[int, list[Fraction]] = defaultdict(list)
    regret_sum = 0

    for instance_id, instance_rows in grouped.items():
        for budget in sorted(common_budgets):
            feasible = [row for row in instance_rows if row.dimension_budget <= budget]
            if not feasible:
                raise ValueError(f"instance {instance_id} has no feasible partition for budget {budget}")
            bound_selected = min(
                feasible,
                key=lambda row: (
                    row.scaled_indexed_bound,
                    row.dimension_budget,
                    partition_sort_key(row),
                ),
            )
            oracle_selected = min(
                feasible,
                key=lambda row: (
                    row.scaled_gap,
                    row.dimension_budget,
                    partition_sort_key(row),
                ),
            )
            if oracle_selected.scaled_gap > bound_selected.scaled_gap:
                raise AssertionError("oracle selection has larger actual gap than bound-selected partition")
            if bound_selected.dimension_budget > budget or oracle_selected.dimension_budget > budget:
                raise AssertionError("selected partition violates the dimension budget")
            regret_sum += bound_selected.scaled_gap - oracle_selected.scaled_gap
            bound_curve[budget].append(Fraction(bound_selected.scaled_gap, n))
            oracle_curve[budget].append(Fraction(oracle_selected.scaled_gap, n))
            selection_rows.append(
                SelectionRow(
                    instance_id=instance_id,
                    dimension_budget=budget,
                    bound_partition_index=bound_selected.partition_index,
                    oracle_partition_index=oracle_selected.partition_index,
                    bound_dimension=bound_selected.dimension_budget,
                    oracle_dimension=oracle_selected.dimension_budget,
                    bound_scaled_gap=bound_selected.scaled_gap,
                    oracle_scaled_gap=oracle_selected.scaled_gap,
                    bound_scaled_indexed_bound=bound_selected.scaled_indexed_bound,
                    oracle_scaled_indexed_bound=oracle_selected.scaled_indexed_bound,
                )
            )

    budgets = sorted(common_budgets)
    bound_means = [float(mean_fraction(bound_curve[budget])) for budget in budgets]
    oracle_means = [float(mean_fraction(oracle_curve[budget])) for budget in budgets]
    bound_q1 = [quartiles([float(value) for value in bound_curve[budget]])[0] for budget in budgets]
    bound_q3 = [quartiles([float(value) for value in bound_curve[budget]])[1] for budget in budgets]
    oracle_q1 = [quartiles([float(value) for value in oracle_curve[budget]])[0] for budget in budgets]
    oracle_q3 = [quartiles([float(value) for value in oracle_curve[budget]])[1] for budget in budgets]

    plt.style.use("seaborn-v0_8-whitegrid")
    fig, ax = plt.subplots(figsize=(4.8, 3.3))
    bound_fill = "mediumaquamarine"
    bound_edge = "seagreen"
    oracle_edge = "#8b0000"
    oracle_fill = "#c76b54"
    ax.fill_between(budgets, bound_q1, bound_q3, color=bound_fill, alpha=0.25)
    ax.fill_between(budgets, oracle_q1, oracle_q3, color=oracle_fill, alpha=0.18)
    ax.plot(
        budgets,
        bound_means,
        color=bound_edge,
        linewidth=2.0,
        marker="o",
        markersize=5.5,
        markerfacecolor=bound_fill,
        markeredgecolor=bound_edge,
        label="Bound-selected",
    )
    ax.plot(
        budgets,
        oracle_means,
        color=oracle_edge,
        linewidth=2.0,
        linestyle="--",
        marker="s",
        markersize=5.2,
        markerfacecolor=oracle_fill,
        markeredgecolor=oracle_edge,
        label="Actual-gap oracle",
    )
    ax.set_xlabel(r"Dimension budget $\bar C$", fontsize=11)
    ax.set_ylabel(r"Actual optimality gap $G(\Pi)$", fontsize=11)
    ax.set_xticks(budgets)
    ax.tick_params(axis="both", labelsize=11)
    ax.legend(frameon=False, fontsize=11, loc="upper right")
    ax.grid(True, alpha=0.3)

    mean_regret = Fraction(regret_sum, len(selection_rows) * n)
    annotation = "\n".join(
        [
            f"Violation rate: {violation_count}/{total_rows}",
            f"Positive equality: {positive_equality_cases}",
            f"Mean regret: {float(mean_regret):.3f}",
        ]
    )
    ax.text(
        0.03,
        0.97,
        annotation,
        transform=ax.transAxes,
        va="top",
        ha="left",
        fontsize=11,
        bbox={"facecolor": "white", "edgecolor": "#cccccc", "alpha": 0.9, "boxstyle": "round,pad=0.3"},
    )
    fig.tight_layout()

    png_path = output_dir / f"{args.figure_name}.png"
    pdf_path = output_dir / f"{args.figure_name}.pdf"
    fig.savefig(png_path, dpi=300, bbox_inches="tight")
    fig.savefig(pdf_path, bbox_inches="tight")
    plt.close(fig)

    selection_csv = output_dir / f"{args.figure_name}_selections.csv"
    with selection_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(selection_rows[0].to_csv_row(n).keys()),
            lineterminator="\n",
        )
        writer.writeheader()
        for row in selection_rows:
            writer.writerow(row.to_csv_row(n))

    summary = {
        "partition_rows": str(Path(args.partition_rows)),
        "instance_count": len(grouped),
        "common_budgets": budgets,
        "violation_rate_fraction": f"{violation_count}/{total_rows}",
        "positive_equality_cases": positive_equality_cases,
        "selection_pair_count": len(selection_rows),
        "mean_selection_regret": f"{mean_regret.numerator}/{mean_regret.denominator}",
        "mean_selection_regret_decimal": float(mean_regret),
        "bound_mean_gap_by_budget": {
            str(budget): str(mean_fraction(bound_curve[budget])) for budget in budgets
        },
        "oracle_mean_gap_by_budget": {
            str(budget): str(mean_fraction(oracle_curve[budget])) for budget in budgets
        },
    }
    (output_dir / f"{args.figure_name}_summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
