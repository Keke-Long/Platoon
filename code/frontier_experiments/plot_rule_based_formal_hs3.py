"""Generate formal hS=3 rule-based experiment figures."""

from __future__ import annotations

import argparse
import csv
import math
import os
from pathlib import Path


DELTA_COLORS = {
    2: "#1f77b4",
    4: "#d62728",
    6: "#2ca02c",
    8: "#9467bd",
}
PMAX_MARKERS = {
    2: "o",
    4: "s",
    6: "^",
    8: "D",
}
METHOD_COLORS = {
    "NP": "#222222",
    "CHP": "#ff7f0e",
    "PP": "#1f77b4",
}


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def fvalue(row: dict[str, str], field: str) -> float | None:
    value = row.get(field)
    if value in (None, "", "NA"):
        return None
    return float(value)


def ivalue(row: dict[str, str], field: str) -> int | None:
    value = fvalue(row, field)
    return int(value) if value is not None else None


def mean(values: list[float]) -> float:
    return sum(values) / len(values)


def stderr(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mu = mean(values)
    variance = sum((value - mu) ** 2 for value in values) / (len(values) - 1)
    return math.sqrt(variance / len(values))


def grouped(rows: list[dict[str, str]], keys: tuple[str, ...]) -> dict[tuple[object, ...], list[dict[str, str]]]:
    result: dict[tuple[object, ...], list[dict[str, str]]] = {}
    for row in rows:
        key: list[object] = []
        skip = False
        for field in keys:
            value = row.get(field)
            if value in (None, ""):
                skip = True
                break
            if field in {"N", "threshold", "delta", "max_platoon_size", "Pmax", "replication"}:
                key.append(int(float(value)))
            elif field == "arrival_rate":
                key.append(float(value))
            else:
                key.append(value)
        if not skip:
            result.setdefault(tuple(key), []).append(row)
    return result


def save_both(fig, output_dir: Path, stem: str) -> None:
    fig.tight_layout()
    fig.savefig(output_dir / f"{stem}.pdf")
    fig.savefig(output_dir / f"{stem}.png", dpi=300)


def plot_bound_validation(bound_rows: list[dict[str, str]], output_dir: Path) -> None:
    import matplotlib.pyplot as plt

    rows = [row for row in bound_rows if row.get("bound_check_available") == "True"]
    if not rows:
        return
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    for (delta, pmax), group in sorted(grouped(rows, ("delta", "Pmax")).items()):
        xs = [fvalue(row, "actual_optimality_gap") for row in group]
        ys = [fvalue(row, "rule_level_upper_bound") for row in group]
        xs = [value for value in xs if value is not None]
        ys = [value for value in ys if value is not None]
        if not xs or not ys:
            continue
        ax.scatter(
            xs,
            ys,
            s=32,
            alpha=0.74,
            color=DELTA_COLORS.get(int(delta), "#555555"),
            marker=PMAX_MARKERS.get(int(pmax), "o"),
            label=f"delta={delta}, Pmax={pmax}",
        )
    max_axis = max(
        max(float(row["actual_optimality_gap"]) for row in rows),
        max(float(row["rule_level_upper_bound"]) for row in rows),
    )
    ax.plot([0, max_axis], [0, max_axis], color="#666666", linewidth=1.0, linestyle="--")
    coverage = len({row["instance_id"] for row in rows})
    ax.text(0.02, 0.98, f"Coverage: {coverage} instances, {len(rows)} rows", transform=ax.transAxes, va="top")
    ax.set_xlabel("Actual G")
    ax.set_ylabel("Rule-level upper bound Ghat")
    ax.grid(True, linewidth=0.5, alpha=0.25)
    ax.legend(frameon=False, fontsize=8, ncols=2)
    save_both(fig, output_dir, "bound_validation_actual_vs_upper")
    plt.close(fig)


def plot_tradeoff(bound_rows: list[dict[str, str]], output_dir: Path) -> None:
    import matplotlib.pyplot as plt

    rows = [row for row in bound_rows if row.get("bound_check_available") == "True"]
    if not rows:
        return
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    for (delta, pmax), group in sorted(grouped(rows, ("delta", "Pmax")).items()):
        times = [fvalue(row, "solve_time_s") for row in group]
        gaps = [fvalue(row, "actual_optimality_gap") for row in group]
        pairs = [(x, y) for x, y in zip(times, gaps, strict=True) if x is not None and y is not None]
        if not pairs:
            continue
        xs = [pair[0] for pair in pairs]
        ys = [pair[1] for pair in pairs]
        ax.errorbar(
            [mean(xs)],
            [mean(ys)],
            xerr=[stderr(xs)],
            yerr=[stderr(ys)],
            fmt=PMAX_MARKERS.get(int(pmax), "o"),
            color=DELTA_COLORS.get(int(delta), "#555555"),
            markersize=6,
            capsize=3,
            label=f"delta={delta}, Pmax={pmax}",
        )
    ax.set_xlabel("Downstream solve time (s)")
    ax.set_ylabel("Actual G")
    ax.grid(True, linewidth=0.5, alpha=0.25)
    ax.legend(frameon=False, fontsize=8, ncols=2)
    save_both(fig, output_dir, "experimental_tradeoff_solve_time_gap")
    plt.close(fig)


def method_delay(rows: list[dict[str, str]], method: str, delta: int | None, rate: float | None, pmax: int | None = None) -> list[float]:
    values: list[float] = []
    for row in rows:
        if row.get("method") != method:
            continue
        if delta is not None and ivalue(row, "delta") != delta:
            continue
        if rate is not None and fvalue(row, "arrival_rate") != rate:
            continue
        if pmax is not None and ivalue(row, "Pmax") != pmax:
            continue
        value = fvalue(row, "objective")
        if value is not None:
            values.append(value)
    return values


def plot_delay_density(rows: list[dict[str, str]], output_dir: Path) -> None:
    import matplotlib.pyplot as plt

    deltas = sorted({ivalue(row, "delta") for row in rows if row.get("delta") not in (None, "") and row.get("method") != "NP"})
    deltas = [value for value in deltas if value is not None]
    rates = sorted({fvalue(row, "arrival_rate") for row in rows})
    rates = [value for value in rates if value is not None]
    pmax_values = sorted({ivalue(row, "Pmax") for row in rows if row.get("method") == "PP"})
    pmax_values = [value for value in pmax_values if value is not None]
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.8))
    ax = axes[0]
    np_values = method_delay(rows, "NP", None, None)
    if np_values:
        ax.plot(deltas, [mean(np_values)] * len(deltas), color=METHOD_COLORS["NP"], marker="x", label="NP")
    chp_y = [mean(method_delay(rows, "CHP", delta, None)) for delta in deltas]
    ax.plot(deltas, chp_y, color=METHOD_COLORS["CHP"], marker="v", label="CHP")
    for pmax in pmax_values:
        y = [mean(method_delay(rows, "PP", delta, None, pmax)) for delta in deltas]
        ax.plot(deltas, y, color="#666666", marker=PMAX_MARKERS.get(pmax, "o"), label=f"PP Pmax={pmax}")
    ax.set_xlabel("Delta")
    ax.set_ylabel("Average delay or incumbent")
    ax.grid(True, linewidth=0.5, alpha=0.25)
    ax.legend(frameon=False, fontsize=8)

    ax = axes[1]
    for method, marker in (("NP", "x"), ("CHP", "v")):
        y = [mean(method_delay(rows, method, None, rate)) for rate in rates]
        ax.plot(rates, y, color=METHOD_COLORS[method], marker=marker, label=method)
    pp_y = [mean(method_delay(rows, "PP", None, rate)) for rate in rates]
    ax.plot(rates, pp_y, color=METHOD_COLORS["PP"], marker="o", label="PP")
    ax.set_xlabel("Arrival rate")
    ax.set_ylabel("Average delay or incumbent")
    ax.grid(True, linewidth=0.5, alpha=0.25)
    ax.legend(frameon=False, fontsize=8)
    save_both(fig, output_dir, "pp_delay_vs_threshold_density")
    plt.close(fig)


def metric_values(rows: list[dict[str, str]], metric: str, method: str, delta: int | None, rate: float | None) -> list[float]:
    values: list[float] = []
    for row in rows:
        if row.get("method") != method:
            continue
        if delta is not None and ivalue(row, "delta") != delta:
            continue
        if rate is not None and fvalue(row, "arrival_rate") != rate:
            continue
        value = fvalue(row, metric)
        if value is not None:
            values.append(value)
    return values


def plot_time_platoons(rows: list[dict[str, str]], output_dir: Path) -> None:
    import matplotlib.pyplot as plt

    deltas = sorted({ivalue(row, "delta") for row in rows if row.get("delta") not in (None, "") and row.get("method") != "NP"})
    deltas = [value for value in deltas if value is not None]
    rates = sorted({fvalue(row, "arrival_rate") for row in rows})
    rates = [value for value in rates if value is not None]
    fig, axes = plt.subplots(2, 2, figsize=(9.2, 6.8))
    panels = [
        (axes[0][0], "solve_time_s", deltas, "Delta", "Solve time (s)", "delta"),
        (axes[0][1], "solve_time_s", rates, "Arrival rate", "Solve time (s)", "rate"),
        (axes[1][0], "number_of_platoons", deltas, "Delta", "Number of platoons", "delta"),
        (axes[1][1], "number_of_platoons", rates, "Arrival rate", "Number of platoons", "rate"),
    ]
    for ax, metric, xs, xlabel, ylabel, mode in panels:
        for method, marker in (("NP", "x"), ("CHP", "v"), ("PP", "o")):
            y: list[float] = []
            for x in xs:
                values = metric_values(rows, metric, method, int(x) if mode == "delta" and method != "NP" else None, float(x) if mode == "rate" else None)
                y.append(mean(values) if values else float("nan"))
            ax.plot(xs, y, marker=marker, color=METHOD_COLORS[method], label=method)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.grid(True, linewidth=0.5, alpha=0.25)
    axes[0][0].legend(frameon=False, fontsize=8)
    save_both(fig, output_dir, "pp_time_and_platoon_count")
    plt.close(fig)


def plot_trajectories(trajectory_rows: list[dict[str, str]], output_dir: Path) -> None:
    import matplotlib.pyplot as plt

    if not trajectory_rows:
        return
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    groups: dict[tuple[str, str, str, str], list[dict[str, str]]] = {}
    for row in trajectory_rows:
        key = (
            row.get("method") or "NA",
            row.get("delta") or "NA",
            row.get("Pmax") or "NA",
            row.get("run_role") or "NA",
        )
        groups.setdefault(key, []).append(row)
    for key, group in sorted(groups.items()):
        method = key[0]
        label = method
        if method == "PP":
            label = f"PP delta={key[1]}, Pmax={key[2]}"
        elif method == "CHP":
            label = f"CHP delta={key[1]}"
        xs = [fvalue(row, "time_s") for row in group]
        ys = [fvalue(row, "incumbent_average_delay") for row in group]
        pairs = sorted((x, y) for x, y in zip(xs, ys, strict=True) if x is not None and y is not None)
        if pairs:
            ax.step([pair[0] for pair in pairs], [pair[1] for pair in pairs], where="post", label=label)
    ax.set_xlabel("Gurobi runtime (s)")
    ax.set_ylabel("Incumbent average delay")
    ax.grid(True, linewidth=0.5, alpha=0.25)
    ax.legend(frameon=False, fontsize=8)
    save_both(fig, output_dir, "gurobi_solution_quality_over_time")
    plt.close(fig)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bound-dir", type=Path, default=Path("../../results/rule_based_experiments/formal_bound_hS3"))
    parser.add_argument("--comparison-dir", type=Path, default=Path("../../results/rule_based_experiments/formal_pp_hS3"))
    parser.add_argument("--output-dir", type=Path, default=Path("../../results/rule_based_experiments/formal_figures_hS3"))
    return parser


def main() -> int:
    args = build_parser().parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(args.output_dir / ".mplconfig"))
    import matplotlib.pyplot as plt

    plt.rcParams.update(
        {
            "font.size": 10,
            "axes.labelsize": 10,
            "axes.titlesize": 11,
            "legend.fontsize": 8,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )
    bound_rows = read_rows(args.bound_dir / "formal_bound_rows.csv")
    comparison_rows = read_rows(args.comparison_dir / "formal_comparison_rows.csv")
    trajectory_rows = read_rows(args.comparison_dir / "gurobi_incumbent_trajectories.csv")
    plot_bound_validation(bound_rows, args.output_dir)
    plot_tradeoff(bound_rows, args.output_dir)
    plot_delay_density(comparison_rows, args.output_dir)
    plot_time_platoons(comparison_rows, args.output_dir)
    plot_trajectories(trajectory_rows, args.output_dir)
    print(args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
