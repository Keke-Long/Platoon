"""Build preliminary diagnostic plots for rule-based experiments."""

from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def fvalue(row: dict[str, str], field: str) -> float | None:
    value = row.get(field)
    if value in (None, ""):
        return None
    return float(value)


def plot_gap_by_threshold(theory_summary: Path, output_dir: Path) -> None:
    os.environ.setdefault("MPLCONFIGDIR", str(output_dir / ".mplconfig"))
    import matplotlib.pyplot as plt

    rows = read_rows(theory_summary)
    grouped: dict[int, dict[int, list[float]]] = {}
    for row in rows:
        gap = fvalue(row, "mean_actual_gap")
        if gap is None:
            continue
        threshold = int(float(row["threshold"]))
        pmax = int(float(row["max_platoon_size"]))
        grouped.setdefault(pmax, {}).setdefault(threshold, []).append(gap)
    fig, ax = plt.subplots(figsize=(5.2, 3.4))
    for pmax, by_threshold in sorted(grouped.items()):
        xs = sorted(by_threshold)
        ys = [sum(by_threshold[x]) / len(by_threshold[x]) for x in xs]
        ax.plot(xs, ys, marker="o", linewidth=1.7, label=f"Pmax={pmax}")
    ax.set_xlabel("Critical headway threshold delta")
    ax.set_ylabel("Mean actual optimality gap")
    ax.grid(True, linewidth=0.5, alpha=0.28)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(output_dir / "actual_gap_by_threshold_pmax.png", dpi=300)
    plt.close(fig)


def plot_tradeoff(theory_rows: Path, output_dir: Path) -> None:
    os.environ.setdefault("MPLCONFIGDIR", str(output_dir / ".mplconfig"))
    import matplotlib.pyplot as plt

    rows = read_rows(theory_rows)
    fig, ax = plt.subplots(figsize=(5.2, 3.4))
    markers = {2: "o", 3: "s", 4: "^", 5: "D"}
    for pmax in sorted({int(float(row["max_platoon_size"])) for row in rows}):
        subset = [
            row
            for row in rows
            if int(float(row["max_platoon_size"])) == pmax
            and row.get("actual_optimality_gap") not in (None, "")
        ]
        if not subset:
            continue
        ax.scatter(
            [float(row["ordering_variable_count"]) for row in subset],
            [float(row["actual_optimality_gap"]) for row in subset],
            s=20,
            alpha=0.55,
            marker=markers.get(pmax, "o"),
            label=f"Pmax={pmax}",
        )
    ax.set_xlabel("Ordering-variable count")
    ax.set_ylabel("Actual optimality gap")
    ax.grid(True, linewidth=0.5, alpha=0.28)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(output_dir / "gap_vs_ordering_variables_pp_grid.png", dpi=300)
    plt.close(fig)


def plot_comparison_runtime(comparison_summary: Path, output_dir: Path) -> None:
    if not comparison_summary.exists():
        return
    os.environ.setdefault("MPLCONFIGDIR", str(output_dir / ".mplconfig"))
    import matplotlib.pyplot as plt

    rows = read_rows(comparison_summary)
    methods = ["NP", "CHP", "PP"]
    n_values = sorted({int(float(row["N"])) for row in rows})
    width = 0.24
    x = list(range(len(n_values)))
    fig, ax = plt.subplots(figsize=(5.2, 3.4))
    for idx, method in enumerate(methods):
        values = []
        for n_value in n_values:
            subset = [
                row
                for row in rows
                if int(float(row["N"])) == n_value and row["method"] == method
            ]
            vals = [fvalue(row, "mean_solve_time_s") for row in subset]
            vals = [val for val in vals if val is not None]
            values.append(sum(vals) / len(vals) if vals else 0.0)
        ax.bar([pos + (idx - 1) * width for pos in x], values, width=width, label=method)
    ax.set_xticks(x)
    ax.set_xticklabels([str(value) for value in n_values])
    ax.set_xlabel("N")
    ax.set_ylabel("Mean solver time (s)")
    ax.grid(axis="y", linewidth=0.5, alpha=0.28)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(output_dir / "comparison_solver_time_by_N.png", dpi=300)
    plt.close(fig)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--theory-dir", type=Path, required=True)
    parser.add_argument("--comparison-dir", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    plot_gap_by_threshold(args.theory_dir / "formal_theory_summary.csv", args.output_dir)
    plot_tradeoff(args.theory_dir / "formal_theory_rows.csv", args.output_dir)
    if args.comparison_dir is not None:
        plot_comparison_runtime(args.comparison_dir / "formal_comparison_summary.csv", args.output_dir)
    print(args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
