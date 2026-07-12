"""Generate formal hS=3 rule-based experiment figures.

The source of truth for Chapter 5 figure forms is
CHAPTER5_FIGURE_SPEC.md. Do not change axes, plot types, encodings, or
aggregation rules without explicit project-lead approval.
"""

from __future__ import annotations

import argparse
import csv
import json
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
N_COLORS = {
    20: "#1f77b4",
    40: "#d62728",
    60: "#2ca02c",
    80: "#9467bd",
}
RATE_MARKERS = {
    0.4: "o",
    0.7: "^",
    1.0: "s",
}
RATE_COLORS = {
    0.4: "#1f77b4",
    0.7: "#00a6a6",
    1.0: "#2ecc71",
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


def median(values: list[float]) -> float:
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return 0.5 * (ordered[middle - 1] + ordered[middle])


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


def unique_ints(rows: list[dict[str, str]], field: str) -> list[int]:
    return sorted({value for value in (ivalue(row, field) for row in rows) if value is not None})


def unique_floats(rows: list[dict[str, str]], field: str) -> list[float]:
    return sorted({value for value in (fvalue(row, field) for row in rows) if value is not None})


def finite_mean(values: list[float]) -> float | None:
    return mean(values) if values else None


def filter_rows(
    rows: list[dict[str, str]],
    *,
    n_value: int | None = None,
    method: str | None = None,
    delta: int | None = None,
    pmax: int | None = None,
    rate: float | None = None,
) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for row in rows:
        if n_value is not None and ivalue(row, "N") != n_value:
            continue
        if method is not None and row.get("method") != method:
            continue
        if delta is not None and ivalue(row, "delta") != delta:
            continue
        if pmax is not None and ivalue(row, "Pmax") != pmax:
            continue
        if rate is not None and fvalue(row, "arrival_rate") != rate:
            continue
        result.append(row)
    return result


def metric_mean(
    rows: list[dict[str, str]],
    metric: str,
    *,
    n_value: int | None = None,
    method: str | None = None,
    delta: int | None = None,
    pmax: int | None = None,
    rate: float | None = None,
) -> float | None:
    values = [
        value
        for value in (
            fvalue(row, metric)
            for row in filter_rows(
                rows,
                n_value=n_value,
                method=method,
                delta=delta,
                pmax=pmax,
                rate=rate,
            )
        )
        if value is not None
    ]
    return finite_mean(values)


def metric_values(
    rows: list[dict[str, str]],
    metric: str,
    *,
    n_value: int | None = None,
    method: str | None = None,
    delta: int | None = None,
    pmax: int | None = None,
    rate: float | None = None,
) -> list[float]:
    return [
        value
        for value in (
            fvalue(row, metric)
            for row in filter_rows(
                rows,
                n_value=n_value,
                method=method,
                delta=delta,
                pmax=pmax,
                rate=rate,
            )
        )
        if value is not None
    ]


def mean_interval(values: list[float]) -> tuple[float | None, float | None]:
    if not values:
        return None, None
    return mean(values), 1.96 * stderr(values) if len(values) >= 2 else None


def pp_metric_groups(
    rows: list[dict[str, str]],
    metric: str,
    *,
    x_field: str,
) -> dict[tuple[int, int, int, float | int], list[float]]:
    """Group PP metric values by N, delta, Pmax, and the plotted x variable."""

    if x_field not in {"delta", "arrival_rate"}:
        raise ValueError("x_field must be delta or arrival_rate")
    groups: dict[tuple[int, int, int, float | int], list[float]] = {}
    for row in rows:
        if row.get("method") != "PP":
            continue
        n_value = ivalue(row, "N")
        delta = ivalue(row, "delta")
        pmax = ivalue(row, "Pmax")
        metric_value = fvalue(row, metric)
        if n_value is None or delta is None or pmax is None or metric_value is None:
            continue
        x_value = ivalue(row, "delta") if x_field == "delta" else fvalue(row, "arrival_rate")
        if x_value is None:
            continue
        groups.setdefault((n_value, delta, pmax, x_value), []).append(metric_value)
    return groups


def select_representative_instance(
    trajectory_rows: list[dict[str, str]],
    comparison_rows: list[dict[str, str]] | None = None,
    representative_delta: int = 4,
    representative_pmax: int = 4,
) -> str | None:
    comparison_rows = comparison_rows or []
    comparison_by_instance = {
        (row.get("instance_id") or "", row.get("method") or "", row.get("delta") or "", row.get("Pmax") or ""): row
        for row in comparison_rows
    }
    by_instance: dict[str, set[str]] = {}
    point_counts: dict[tuple[str, str], int] = {}
    n_by_instance: dict[str, int] = {}
    for row in trajectory_rows:
        instance_id = row.get("instance_id")
        if not instance_id:
            continue
        n_value = ivalue(row, "N")
        if n_value is not None:
            n_by_instance[instance_id] = n_value
        method = row.get("method")
        if method == "NP":
            role = "NP"
        elif method == "CHP" and ivalue(row, "delta") == representative_delta:
            role = "CHP"
        elif (
            method == "PP"
            and ivalue(row, "delta") == representative_delta
            and ivalue(row, "Pmax") == representative_pmax
        ):
            role = "PP"
        else:
            continue
        by_instance.setdefault(instance_id, set()).add(role)
        point_counts[(instance_id, role)] = point_counts.get((instance_id, role), 0) + 1
    complete = sorted(instance_id for instance_id, roles in by_instance.items() if roles == {"NP", "CHP", "PP"})
    qualified: list[str] = []
    for instance_id in complete:
        if n_by_instance.get(instance_id, 0) < 40:
            continue
        np_row = comparison_by_instance.get((instance_id, "NP", "", ""))
        np_reaches_limit = False
        if np_row is not None:
            status = np_row.get("status")
            solve_time = fvalue(np_row, "solve_time_s")
            time_limit = fvalue(np_row, "time_limit_s")
            np_reaches_limit = status == "TIME_LIMIT" or (
                solve_time is not None and time_limit is not None and solve_time >= 0.95 * time_limit
            )
        np_has_updates = point_counts.get((instance_id, "NP"), 0) >= 2
        pp_has_callbacks = point_counts.get((instance_id, "PP"), 0) >= 2
        if (np_has_updates or np_reaches_limit) and pp_has_callbacks:
            qualified.append(instance_id)
    if qualified:
        return qualified[0]
    return complete[0] if complete else None


def save_figure(fig, output_dir: Path, stem: str, *, write_png: bool = False) -> None:
    fig.tight_layout()
    fig.savefig(output_dir / f"{stem}.pdf", bbox_inches="tight")
    if write_png:
        fig.savefig(output_dir / f"{stem}.png", dpi=300, bbox_inches="tight")


def apply_axis_typography(ax) -> None:
    ax.xaxis.label.set_size(11)
    ax.yaxis.label.set_size(11)
    if hasattr(ax, "zaxis"):
        ax.zaxis.label.set_size(11)
    ax.tick_params(axis="both", labelsize=10)
    if hasattr(ax, "zaxis"):
        ax.tick_params(axis="z", labelsize=10)


def panel_label(ax, label: str, *, is_3d: bool = False) -> None:
    if is_3d:
        ax.text2D(0.02, 0.96, label, transform=ax.transAxes, fontsize=10)
    else:
        ax.text(0.02, 0.96, label, transform=ax.transAxes, fontsize=10, va="top")


def write_metadata(output_dir: Path, stem: str, metadata: dict[str, object]) -> None:
    (output_dir / f"{stem}_metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def plot_bound_validation(bound_rows: list[dict[str, str]], output_dir: Path, *, write_png: bool = False) -> None:
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch

    rows = [row for row in bound_rows if fvalue(row, "rule_level_upper_bound") is not None]
    checked_rows = [row for row in rows if row.get("bound_check_available") == "True"]
    if not rows:
        return
    fig = plt.figure(figsize=(7.2, 5.2))
    ax = fig.add_subplot(111, projection="3d")
    all_deltas = unique_ints(rows, "delta")
    all_pmax_values = unique_ints(rows, "Pmax")
    z_lookup: dict[tuple[int, int], float] = {}
    for (delta, pmax), group in sorted(grouped(rows, ("delta", "Pmax")).items()):
        values = [value for value in (fvalue(row, "rule_level_upper_bound") for row in group) if value is not None]
        if values:
            z_lookup[(int(delta), int(pmax))] = mean(values)
    if all_deltas and all_pmax_values:
        x_grid, y_grid = np.meshgrid(all_deltas, all_pmax_values)
        z_grid = np.array([[z_lookup.get((int(x), int(y)), np.nan) for x in all_deltas] for y in all_pmax_values])
        ax.plot_surface(
            x_grid,
            y_grid,
            z_grid,
            color="#ff6b5f",
            alpha=0.34,
            linewidth=0.5,
            edgecolor="#c44e52",
            antialiased=True,
        )
    for rate, group in sorted(grouped(checked_rows, ("arrival_rate",)).items()):
        points: list[tuple[float, float, float]] = []
        for row in group:
            delta = fvalue(row, "delta")
            pmax = fvalue(row, "Pmax")
            actual = fvalue(row, "actual_optimality_gap")
            if delta is None or pmax is None or actual is None:
                continue
            points.append((delta, pmax, actual))
        if not points:
            continue
        ax.scatter(
            [point[0] for point in points],
            [point[1] for point in points],
            [point[2] for point in points],
            s=16,
            alpha=0.74,
            color=RATE_COLORS.get(round(float(rate[0]), 1), "#555555"),
            marker="o",
            depthshade=False,
        )
    panel_label(ax, "(a)", is_3d=True)
    ax.set_xlabel(r"$\delta$ (s)")
    ax.set_ylabel(r"$P_{\max}$")
    ax.set_zlabel(r"$G$ and $\widehat G$ (s)")
    ax.set_xticks(all_deltas)
    ax.set_yticks(all_pmax_values)
    ax.view_init(elev=22, azim=-58)
    apply_axis_typography(ax)
    rate_handles = [
        Line2D([0], [0], marker="o", color="none", markerfacecolor=color, markeredgecolor=color, linestyle="None", label=rf"$\lambda$={rate:g}")
        for rate, color in sorted(RATE_COLORS.items())
        if any(fvalue(row, "arrival_rate") == rate for row in rows)
    ]
    quantity_handles = [
        Patch(facecolor="#ff6b5f", edgecolor="#c44e52", alpha=0.34, label=r"Upper bound $\widehat G$"),
        Line2D([0], [0], marker="o", color="none", markerfacecolor="#555555", markeredgecolor="#555555", linestyle="None", label=r"Actual $G$"),
    ]
    fig.legend(
        handles=quantity_handles + rate_handles,
        frameon=False,
        fontsize=9,
        ncols=1,
        loc="center left",
        bbox_to_anchor=(0.98, 0.5),
    )
    write_metadata(
        output_dir,
        "bound_validation_actual_vs_upper",
        {
            "figure_number": 6,
            "plot_type": "3D surface plus scatter",
            "axes": {"x": "delta", "y": "Pmax", "z": "actual G and rule-level Ghat"},
            "color": "arrival_rate for actual G points",
            "surface": "Rule-level Ghat is shown as one semi-transparent surface aggregated by delta and Pmax across completed rows; N is not visually encoded.",
            "quantity_encoding": "Actual G uses filled scatter points; Ghat uses a semi-transparent surface.",
            "rows": "Ghat surface uses completed formal bound rows. Actual G points use only bound_check_available rows where NP and PP are proven optimal.",
            "n_values": unique_ints(rows, "N"),
            "available_only": "Current figure uses the bound-checkable subset of completed data; this subset currently contains N=20 because larger N rows need exact NP references.",
        },
    )
    save_figure(fig, output_dir, "bound_validation_actual_vs_upper", write_png=write_png)
    plt.close(fig)


def plot_tradeoff(bound_rows: list[dict[str, str]], output_dir: Path, *, write_png: bool = False) -> None:
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    rows = [row for row in bound_rows if row.get("bound_check_available") == "True"]
    if not rows:
        return
    n_values = unique_ints(rows, "N")
    delta_values = unique_ints(rows, "delta")
    pmax_values = unique_ints(rows, "Pmax")
    delta_cmap = plt.get_cmap("gist_earth")
    delta_tradeoff_colors = {
        delta: delta_cmap(0.86 - 0.68 * index / max(1, len(delta_values) - 1))
        for index, delta in enumerate(delta_values)
    }
    fig, axes = plt.subplots(1, len(n_values), figsize=(4.0 * len(n_values), 2.94), squeeze=False)
    for col_index, n_value in enumerate(n_values):
        ax = axes[0][col_index]
        ax.set_title(f"({chr(ord('a') + col_index)}) N={n_value}", loc="left", pad=5, fontsize=10)
        for (delta, pmax), group in sorted(grouped(filter_rows(rows, n_value=n_value), ("delta", "Pmax")).items()):
            points: list[tuple[float, float]] = []
            for row in group:
                solve_time = fvalue(row, "solve_time_s")
                gap = fvalue(row, "actual_optimality_gap")
                if solve_time is None or gap is None:
                    continue
                points.append((solve_time, gap))
            if not points:
                continue
            ax.scatter(
                [point[0] for point in points],
                [point[1] for point in points],
                marker=PMAX_MARKERS.get(int(pmax), "o"),
                color=delta_tradeoff_colors.get(int(delta), "#555555"),
                s=22,
                alpha=0.72,
                linewidths=0.3,
                edgecolors="white",
            )
        ax.set_xlabel("Downstream solve time (s)")
        ax.set_ylabel(r"Actual optimality gap $G$")
        ax.grid(True, linewidth=0.5, alpha=0.25)
        apply_axis_typography(ax)
    delta_handles = [
        Line2D([0], [0], marker="o", color="none", markerfacecolor=delta_tradeoff_colors[delta], markeredgecolor=delta_tradeoff_colors[delta], linestyle="None", label=rf"$\delta$={delta}")
        for delta in delta_values
    ]
    pmax_handles = [
        Line2D([0], [0], marker=PMAX_MARKERS.get(pmax, "o"), color="#555555", markerfacecolor="#555555", linestyle="None", label=rf"$P_{{\max}}$={pmax}")
        for pmax in pmax_values
    ]
    legend_ax = axes[0][-1]
    delta_legend = legend_ax.legend(handles=delta_handles, title=r"$\delta$ label", frameon=False, fontsize=8, title_fontsize=8, loc="upper left", bbox_to_anchor=(0.52, 0.96))
    legend_ax.add_artist(delta_legend)
    legend_ax.legend(handles=pmax_handles, title=r"$P_{\max}$ label", frameon=False, fontsize=8, title_fontsize=8, loc="upper left", bbox_to_anchor=(0.72, 0.96))
    write_metadata(
        output_dir,
        "experimental_tradeoff_solve_time_gap",
        {
            "figure_number": 7,
            "plot_type": "case-level scatter",
            "axes": {"x": "solve_time_s", "y": "actual_optimality_gap"},
            "color": "delta, sampled from the gist_earth colormap in reversed order",
            "marker": "Pmax",
            "aggregation": "None. Each plotted point is one bound-checkable case row with exact actual G.",
            "n_values": n_values,
        },
    )
    save_figure(fig, output_dir, "experimental_tradeoff_solve_time_gap", write_png=write_png)
    plt.close(fig)


def plot_delay_density(rows: list[dict[str, str]], output_dir: Path, *, write_png: bool = False) -> None:
    import matplotlib.pyplot as plt

    checked_rows = [row for row in rows if row.get("method") == "PP" and row.get("delay_order_check_available") == "True"]
    n_values = unique_ints(checked_rows, "N")
    deltas = unique_ints(checked_rows, "delta")
    rates = unique_floats(checked_rows, "arrival_rate")
    if not n_values or not deltas or not rates:
        return

    def checked_delay_values(method: str, *, n_value: int, delta: int | None = None, rate: float | None = None) -> list[float]:
        field = {
            "NP": "np_optimal_objective",
            "CHP": "matching_chp_objective",
            "PP": "pp_optimal_objective",
        }[method]
        values: list[float] = []
        for row in checked_rows:
            if ivalue(row, "N") != n_value:
                continue
            if delta is not None and ivalue(row, "delta") != delta:
                continue
            if rate is not None and fvalue(row, "arrival_rate") != rate:
                continue
            value = fvalue(row, field)
            if value is not None:
                values.append(value)
        return values

    def checked_delay_mean(method: str, *, n_value: int, delta: int | None = None, rate: float | None = None) -> float | None:
        return finite_mean(checked_delay_values(method, n_value=n_value, delta=delta, rate=rate))

    def percentile(values: list[float], fraction: float) -> float | None:
        if not values:
            return None
        ordered = sorted(values)
        position = fraction * (len(ordered) - 1)
        lower_index = math.floor(position)
        upper_index = math.ceil(position)
        if lower_index == upper_index:
            return ordered[lower_index]
        lower_weight = upper_index - position
        upper_weight = position - lower_index
        return lower_weight * ordered[lower_index] + upper_weight * ordered[upper_index]

    def plot_method_mean_with_range(ax, xs: list[float | int], ys: list[float | None], ranges: list[list[float]], method: str, marker: str) -> None:
        lower = [percentile(values, 0.25) for values in ranges]
        upper = [percentile(values, 0.75) for values in ranges]
        if all(value is not None for value in lower + upper):
            ax.fill_between(xs, lower, upper, color=METHOD_COLORS[method], alpha=0.06, linewidth=0)
        ax.plot(xs, ys, color=METHOD_COLORS[method], marker=marker, linewidth=1.4, label=method)

    fig, axes = plt.subplots(len(n_values), 2, figsize=(6.24, max(3.2, 2.8 * len(n_values))), squeeze=False)
    for row_index, n_value in enumerate(n_values):
        ax = axes[row_index][0]
        ax.set_title(f"({chr(ord('a') + 2 * row_index)}) N={n_value}", loc="center", pad=8, fontsize=10)
        np_ranges = [checked_delay_values("NP", n_value=n_value, delta=delta) for delta in deltas]
        np_y = [finite_mean(values) for values in np_ranges]
        chp_y = [checked_delay_mean("CHP", n_value=n_value, delta=delta) for delta in deltas]
        pp_y = [checked_delay_mean("PP", n_value=n_value, delta=delta) for delta in deltas]
        chp_ranges = [checked_delay_values("CHP", n_value=n_value, delta=delta) for delta in deltas]
        pp_ranges = [checked_delay_values("PP", n_value=n_value, delta=delta) for delta in deltas]
        plot_method_mean_with_range(ax, deltas, np_y, np_ranges, "NP", "x")
        plot_method_mean_with_range(ax, deltas, chp_y, chp_ranges, "CHP", "v")
        plot_method_mean_with_range(ax, deltas, pp_y, pp_ranges, "PP", "o")
        ax.set_xlabel(r"Platooning threshold $\delta$")
        ax.set_ylabel("Average vehicle delay")
        ax.grid(True, linewidth=0.5, alpha=0.25)
        apply_axis_typography(ax)

        ax = axes[row_index][1]
        ax.set_title(f"({chr(ord('a') + 2 * row_index + 1)}) N={n_value}", loc="center", pad=8, fontsize=10)
        np_rate_ranges = [checked_delay_values("NP", n_value=n_value, rate=rate) for rate in rates]
        np_y = [finite_mean(values) for values in np_rate_ranges]
        chp_rate_y = [checked_delay_mean("CHP", n_value=n_value, rate=rate) for rate in rates]
        pp_rate_y = [checked_delay_mean("PP", n_value=n_value, rate=rate) for rate in rates]
        chp_rate_ranges = [checked_delay_values("CHP", n_value=n_value, rate=rate) for rate in rates]
        pp_rate_ranges = [checked_delay_values("PP", n_value=n_value, rate=rate) for rate in rates]
        plot_method_mean_with_range(ax, rates, np_y, np_rate_ranges, "NP", "x")
        plot_method_mean_with_range(ax, rates, chp_rate_y, chp_rate_ranges, "CHP", "v")
        plot_method_mean_with_range(ax, rates, pp_rate_y, pp_rate_ranges, "PP", "o")
        ax.set_xlabel(r"Arrival rate $\lambda$")
        ax.set_ylabel("Average vehicle delay")
        ax.grid(True, linewidth=0.5, alpha=0.25)
        apply_axis_typography(ax)
    handles: list[object] = []
    labels: list[str] = []
    for legend_ax in (axes[0][0], axes[0][1]):
        new_handles, new_labels = legend_ax.get_legend_handles_labels()
        handles.extend(new_handles)
        labels.extend(new_labels)
    dedup: dict[str, object] = {}
    for handle, label in zip(handles, labels, strict=False):
        dedup.setdefault(label, handle)
    fig.legend(dedup.values(), dedup.keys(), frameon=False, fontsize=11, ncols=3, loc="upper center", bbox_to_anchor=(0.5, 1.06))
    write_metadata(
        output_dir,
        "pp_delay_vs_threshold_density",
        {
            "figure_number": 8,
            "plot_type": "method-level mean line figure",
            "aggregation": "Uses delay-order-checkable PP rows. Delta panels show one paired mean per method and delta; PP is averaged over Pmax, arrival rates, and replications at each delta. Arrival-rate panels show one paired mean per method and arrival rate; PP is averaged over delta, Pmax, and replications at each rate.",
            "uncertainty": "Light shaded bands show the interquartile range behind each method-level mean.",
            "n_values": n_values,
            "method_colors": METHOD_COLORS,
        },
    )
    save_figure(fig, output_dir, "pp_delay_vs_threshold_density", write_png=write_png)
    plt.close(fig)


def plot_time_platoons(rows: list[dict[str, str]], output_dir: Path, *, write_png: bool = False) -> None:
    import matplotlib.pyplot as plt

    n_values = unique_ints(rows, "N")
    deltas = unique_ints([row for row in rows if row.get("method") != "NP"], "delta")
    rates = unique_floats(rows, "arrival_rate")
    pmax_values = unique_ints([row for row in rows if row.get("method") == "PP"], "Pmax")
    if not n_values or not deltas or not rates:
        return
    fig, axes = plt.subplots(len(n_values), 4, figsize=(15.2, max(3.0, 2.8 * len(n_values))), squeeze=False)
    panel_specs = [
        ("solve_time_s", "delta", r"Platooning threshold $\delta$", "Solution time (s)"),
        ("solve_time_s", "arrival_rate", r"Arrival rate $\lambda$", "Solution time (s)"),
        ("number_of_platoons", "delta", r"Platooning threshold $\delta$", "Number of scheduling units"),
        ("number_of_platoons", "arrival_rate", r"Arrival rate $\lambda$", "Number of scheduling units"),
    ]
    for row_index, n_value in enumerate(n_values):
        for col_index, (metric, x_field, xlabel, ylabel) in enumerate(panel_specs):
            ax = axes[row_index][col_index]
            panel_label(ax, f"({chr(ord('a') + 4 * row_index + col_index)}) N={n_value}")
            xs = deltas if x_field == "delta" else rates
            if x_field == "delta":
                np_value = metric_mean(rows, metric, n_value=n_value, method="NP")
                if np_value is not None:
                    ax.plot(xs, [np_value] * len(xs), color=METHOD_COLORS["NP"], marker="x", label="NP")
                chp_y = [metric_mean(rows, metric, n_value=n_value, method="CHP", delta=delta) for delta in deltas]
                ax.plot(xs, chp_y, color=METHOD_COLORS["CHP"], marker="v", label="CHP")
                for delta in deltas:
                    for pmax in pmax_values:
                        value = metric_mean(rows, metric, n_value=n_value, method="PP", delta=delta, pmax=pmax)
                        if value is not None:
                            ax.scatter(
                                [delta],
                                [value],
                                color=DELTA_COLORS.get(delta, "#555555"),
                                marker=PMAX_MARKERS.get(pmax, "o"),
                                s=32,
                                label=f"PP d={delta}, P={pmax}",
                            )
            else:
                np_y = [metric_mean(rows, metric, n_value=n_value, method="NP", rate=rate) for rate in rates]
                ax.plot(xs, np_y, color=METHOD_COLORS["NP"], marker="x", label="NP")
                for delta in deltas:
                    chp_y = [
                        metric_mean(rows, metric, n_value=n_value, method="CHP", delta=delta, rate=rate)
                        for rate in rates
                    ]
                    ax.plot(xs, chp_y, color=DELTA_COLORS.get(delta, "#555555"), linestyle="--", marker="v", label=f"CHP d={delta}")
                    for pmax in pmax_values:
                        pp_y = [
                            metric_mean(rows, metric, n_value=n_value, method="PP", delta=delta, pmax=pmax, rate=rate)
                            for rate in rates
                        ]
                        ax.plot(
                            xs,
                            pp_y,
                            color=DELTA_COLORS.get(delta, "#555555"),
                            marker=PMAX_MARKERS.get(pmax, "o"),
                            linewidth=1.0,
                            alpha=0.75,
                            label=f"PP d={delta}, P={pmax}",
                        )
            ax.set_xlabel(xlabel)
            ax.set_ylabel(ylabel)
            if metric == "solve_time_s":
                ax.set_yscale("log")
            ax.grid(True, linewidth=0.5, alpha=0.25)
            apply_axis_typography(ax)
    handles: list[object] = []
    labels: list[str] = []
    for legend_ax in (axes[0][1], axes[0][3]):
        new_handles, new_labels = legend_ax.get_legend_handles_labels()
        handles.extend(new_handles)
        labels.extend(new_labels)
    dedup: dict[str, object] = {}
    for handle, label in zip(handles, labels, strict=False):
        dedup.setdefault(label, handle)
    fig.legend(dedup.values(), dedup.keys(), frameon=False, fontsize=9, ncols=3, loc="lower center", bbox_to_anchor=(0.5, -0.02))
    write_metadata(
        output_dir,
        "pp_time_and_scheduling_units",
        {
            "figure_number": 9,
            "plot_type": "line figure",
            "aggregation": "Panels are stratified by N. Delta panels average over arrival rates and replications within each N/method/delta/Pmax group. Arrival-rate panels average over replications within each N/method/delta/Pmax/rate group. PP is never averaged across Pmax.",
            "scheduling_units": "NP equals number of vehicles; CHP and PP equal number of platoons.",
            "n_values": n_values,
            "pmax_values": pmax_values,
            "delta_colors": DELTA_COLORS,
            "pmax_markers": PMAX_MARKERS,
        },
    )
    save_figure(fig, output_dir, "pp_time_and_scheduling_units", write_png=write_png)
    plt.close(fig)


def plot_trajectories(
    trajectory_rows: list[dict[str, str]],
    comparison_rows: list[dict[str, str]],
    output_dir: Path,
    representative_delta: int = 4,
    representative_pmax: int = 4,
    write_png: bool = False,
) -> None:
    import matplotlib.pyplot as plt

    if not trajectory_rows:
        return
    selected_instance = select_representative_instance(
        trajectory_rows,
        comparison_rows=comparison_rows,
        representative_delta=representative_delta,
        representative_pmax=representative_pmax,
    )
    if selected_instance is None:
        write_metadata(
            output_dir,
            "gurobi_solution_quality_over_time",
            {
                "selected_instance_id": None,
                "reason": "No instance contains NP, CHP, and representative PP trajectory rows.",
            },
        )
        return
    rows = [row for row in trajectory_rows if row.get("instance_id") == selected_instance]
    selected_n = max((ivalue(row, "N") or 0 for row in rows), default=0)
    max_n_present = max((ivalue(row, "N") or 0 for row in trajectory_rows), default=0)
    available_pp_deltas = sorted(
        {
            ivalue(row, "delta")
            for row in rows
            if row.get("method") == "PP" and ivalue(row, "Pmax") == representative_pmax and ivalue(row, "delta") is not None
        }
    )
    missing_multiple_pp_deltas = len(available_pp_deltas) < 2
    provisional = selected_n < 40 or max_n_present < 40 or missing_multiple_pp_deltas
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    groups: dict[tuple[str, str, str, str], list[dict[str, str]]] = {}
    for row in rows:
        if row.get("method") == "CHP":
            continue
        if row.get("method") == "PP" and ivalue(row, "Pmax") != representative_pmax:
            continue
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
            label = rf"PP $\delta$={key[1]}, $P_{{\max}}$={key[2]}"
        xs = [fvalue(row, "time_s") for row in group]
        ys = [fvalue(row, "incumbent_average_delay") for row in group]
        pairs = sorted((x, y) for x, y in zip(xs, ys, strict=True) if x is not None and y is not None)
        if pairs:
            ax.step([pair[0] for pair in pairs], [pair[1] for pair in pairs], where="post", label=label)
    panel_label(ax, "(a)")
    ax.set_xlabel("Gurobi wall-clock solution time (s)")
    ax.set_ylabel("Best incumbent average vehicle delay")
    ax.grid(True, linewidth=0.5, alpha=0.25)
    apply_axis_typography(ax)
    ax.legend(frameon=False, fontsize=9, loc="center left", bbox_to_anchor=(1.02, 0.5))
    write_metadata(
        output_dir,
        "gurobi_solution_quality_over_time",
        {
            "figure_number": 10,
            "plot_type": "line plot from real Gurobi callback trajectories",
            "axes": {"x": "Gurobi wall-clock solution time", "y": "best incumbent average vehicle delay"},
            "aggregation": "One selected instance only. Series are NP and available PP trajectories at fixed representative Pmax.",
            "status": "partial_current_data" if provisional else "representative_selected_after_N40_search",
            "selection_policy": "Prefer N>=40 instances where NP has multiple incumbent updates or reaches the time limit, PP has at least two callback points, and rows share the same instance. Fall back to the first complete trajectory instance if no better instance exists.",
            "selected_instance_id": selected_instance,
            "selected_N": selected_n,
            "representative_delta": representative_delta,
            "representative_pmax": representative_pmax,
            "available_pp_deltas_for_selected_instance": available_pp_deltas,
            "missing_multiple_pp_delta_trajectories": missing_multiple_pp_deltas,
            "instance_ids_present": sorted({row.get("instance_id", "") for row in trajectory_rows if row.get("instance_id")}),
        },
    )
    save_figure(fig, output_dir, "gurobi_solution_quality_over_time", write_png=write_png)
    plt.close(fig)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bound-dir", type=Path, default=Path("../../results/rule_based_experiments/formal_bound_hS3"))
    parser.add_argument("--comparison-dir", type=Path, default=Path("../../results/rule_based_experiments/formal_pp_hS3"))
    parser.add_argument("--output-dir", type=Path, default=Path("../../results/rule_based_experiments/formal_figures_hS3"))
    parser.add_argument("--representative-threshold", type=int, default=4)
    parser.add_argument("--representative-max-platoon-size", type=int, default=4)
    parser.add_argument("--write-png", action="store_true", help="Also write PNG previews. Formal runs write PDFs only by default.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(args.output_dir / ".mplconfig"))
    import matplotlib.pyplot as plt

    plt.rcParams.update(
        {
            "font.size": 10,
            "axes.labelsize": 11,
            "legend.fontsize": 9,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )
    bound_rows = read_rows(args.bound_dir / "formal_bound_rows.csv")
    comparison_rows = read_rows(args.comparison_dir / "formal_comparison_rows.csv")
    trajectory_rows = read_rows(args.comparison_dir / "gurobi_incumbent_trajectories.csv")
    plot_bound_validation(bound_rows, args.output_dir, write_png=args.write_png)
    plot_tradeoff(bound_rows, args.output_dir, write_png=args.write_png)
    plot_delay_density(comparison_rows, args.output_dir, write_png=args.write_png)
    plot_time_platoons(comparison_rows, args.output_dir, write_png=args.write_png)
    plot_trajectories(
        trajectory_rows,
        comparison_rows,
        args.output_dir,
        representative_delta=args.representative_threshold,
        representative_pmax=args.representative_max_platoon_size,
        write_png=args.write_png,
    )
    print(args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
