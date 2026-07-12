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


def mean(values: list[float]) -> float:
    return sum(values) / len(values)


def quantile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("quantile requires at least one value")
    index = fraction * (len(ordered) - 1)
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    weight = index - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def group_actual_gaps_by_n_threshold_pmax(rows: list[dict[str, str]]) -> dict[int, dict[int, dict[int, list[float]]]]:
    grouped: dict[int, dict[int, dict[int, list[float]]]] = {}
    for row in rows:
        gap = fvalue(row, "actual_optimality_gap")
        if gap is None:
            continue
        n_value = int(float(row["N"]))
        threshold = int(float(row["threshold"]))
        pmax = int(float(row["max_platoon_size"]))
        grouped.setdefault(n_value, {}).setdefault(pmax, {}).setdefault(threshold, []).append(gap)
    return grouped


def plot_gap_by_threshold(theory_rows: Path, output_dir: Path) -> None:
    os.environ.setdefault("MPLCONFIGDIR", str(output_dir / ".mplconfig"))
    import matplotlib.pyplot as plt

    rows = read_rows(theory_rows)
    grouped = group_actual_gaps_by_n_threshold_pmax(rows)
    if not grouped:
        return
    for n_value, by_pmax in sorted(grouped.items()):
        fig, ax = plt.subplots(figsize=(5.2, 3.4))
        for pmax, by_threshold in sorted(by_pmax.items()):
            xs = sorted(by_threshold)
            ys = [mean(by_threshold[x]) for x in xs]
            q1 = [quantile(by_threshold[x], 0.25) for x in xs]
            q3 = [quantile(by_threshold[x], 0.75) for x in xs]
            ax.plot(xs, ys, marker="o", linewidth=1.7, label=f"Pmax={pmax}")
            ax.fill_between(xs, q1, q3, alpha=0.14)
            for x, y in zip(xs, ys, strict=True):
                ax.annotate(
                    str(len(by_threshold[x])),
                    (x, y),
                    xytext=(0, 5),
                    textcoords="offset points",
                    ha="center",
                    fontsize=7,
                )
        ax.set_xlabel("Critical headway threshold delta")
        ax.set_ylabel("Mean actual optimality gap")
        ax.set_title(f"N={n_value}; labels show actual-gap cases")
        ax.grid(True, linewidth=0.5, alpha=0.28)
        ax.legend(frameon=False)
        fig.tight_layout()
        fig.savefig(output_dir / f"actual_gap_by_threshold_pmax_N{n_value}.png", dpi=300)
        plt.close(fig)


def plot_tradeoff(theory_rows: Path, output_dir: Path) -> None:
    os.environ.setdefault("MPLCONFIGDIR", str(output_dir / ".mplconfig"))
    import matplotlib.pyplot as plt

    rows = read_rows(theory_rows)
    grouped: dict[tuple[int, int, int], list[dict[str, str]]] = {}
    for row in rows:
        if row.get("actual_optimality_gap") in (None, ""):
            continue
        key = (
            int(float(row["N"])),
            int(float(row["threshold"])),
            int(float(row["max_platoon_size"])),
        )
        grouped.setdefault(key, []).append(row)
    fig, ax = plt.subplots(figsize=(5.2, 3.4))
    markers = {2: "o", 3: "s", 4: "^", 5: "D"}
    for pmax in sorted({key[2] for key in grouped}):
        subset = {key: value for key, value in grouped.items() if key[2] == pmax}
        xs: list[float] = []
        ys: list[float] = []
        yerr_low: list[float] = []
        yerr_high: list[float] = []
        labels: list[str] = []
        for (n_value, threshold, _), group_rows in sorted(subset.items()):
            gaps = [float(row["actual_optimality_gap"]) for row in group_rows]
            reductions = [float(row["dimension_reduction_ratio"]) for row in group_rows]
            gap_mean = mean(gaps)
            q1 = quantile(gaps, 0.25)
            q3 = quantile(gaps, 0.75)
            xs.append(mean(reductions))
            ys.append(gap_mean)
            yerr_low.append(max(0.0, gap_mean - q1))
            yerr_high.append(max(0.0, q3 - gap_mean))
            labels.append(f"N{n_value},d{threshold}")
        ax.scatter(
            xs,
            ys,
            s=34,
            alpha=0.78,
            marker=markers.get(pmax, "o"),
            label=f"Pmax={pmax}",
        )
        ax.errorbar(xs, ys, yerr=[yerr_low, yerr_high], fmt="none", alpha=0.35, linewidth=0.8)
        for x, y, label in zip(xs, ys, labels, strict=True):
            ax.annotate(label, (x, y), xytext=(3, 3), textcoords="offset points", fontsize=6)
    ax.set_xlabel("Dimension reduction ratio")
    ax.set_ylabel("Mean actual optimality gap")
    ax.grid(True, linewidth=0.5, alpha=0.28)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(output_dir / "gap_vs_dimension_reduction_pp_grid.png", dpi=300)
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
    plot_gap_by_threshold(args.theory_dir / "formal_theory_rows.csv", args.output_dir)
    plot_tradeoff(args.theory_dir / "formal_theory_rows.csv", args.output_dir)
    if args.comparison_dir is not None:
        plot_comparison_runtime(args.comparison_dir / "formal_comparison_summary.csv", args.output_dir)
    print(args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
