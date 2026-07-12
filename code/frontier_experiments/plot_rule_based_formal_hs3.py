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
    from matplotlib.lines import Line2D

    rows = [row for row in bound_rows if row.get("bound_check_available") == "True"]
    if not rows:
        return
    fig = plt.figure(figsize=(7.2, 5.2))
    ax = fig.add_subplot(111, projection="3d")
    for (n_value, rate), group in sorted(grouped(rows, ("N", "arrival_rate")).items()):
        actual_points: list[tuple[float, float, float]] = []
        upper_points: list[tuple[float, float, float]] = []
        for row in group:
            delta = fvalue(row, "delta")
            pmax = fvalue(row, "Pmax")
            actual = fvalue(row, "actual_optimality_gap")
            upper = fvalue(row, "rule_level_upper_bound")
            if delta is None or pmax is None or actual is None or upper is None:
                continue
            actual_points.append((delta, pmax, actual))
            upper_points.append((delta, pmax, upper))
        if not actual_points:
            continue
        ax.scatter(
            [point[0] for point in actual_points],
            [point[1] for point in actual_points],
            [point[2] for point in actual_points],
            s=22,
            alpha=0.60,
            color=N_COLORS.get(int(n_value), "#555555"),
            marker=RATE_MARKERS.get(round(float(rate), 1), "o"),
            depthshade=False,
        )
        ax.scatter(
            [point[0] for point in upper_points],
            [point[1] for point in upper_points],
            [point[2] for point in upper_points],
            s=46,
            alpha=0.92,
            facecolors="none",
            edgecolors=N_COLORS.get(int(n_value), "#555555"),
            marker=RATE_MARKERS.get(round(float(rate), 1), "o"),
            depthshade=False,
        )
    ax.set_xlabel(r"Platooning threshold $\delta$")
    ax.set_ylabel(r"Maximum platoon size $P_{\max}$")
    ax.set_zlabel(r"Actual $G$ and upper bound $\widehat G$")
    ax.set_xticks(unique_ints(rows, "delta"))
    ax.set_yticks(unique_ints(rows, "Pmax"))
    ax.view_init(elev=22, azim=-55)
    panel_label(ax, "(a)", is_3d=True)
    apply_axis_typography(ax)
    n_handles = [
        Line2D([0], [0], marker="o", color="none", markerfacecolor=color, markeredgecolor=color, label=f"N={n_value}")
        for n_value, color in sorted(N_COLORS.items())
        if any(ivalue(row, "N") == n_value for row in rows)
    ]
    rate_handles = [
        Line2D([0], [0], marker=marker, color="#555555", linestyle="None", label=rf"$\lambda$={rate:g}")
        for rate, marker in sorted(RATE_MARKERS.items())
        if any(fvalue(row, "arrival_rate") == rate for row in rows)
    ]
    quantity_handles = [
        Line2D([0], [0], marker="o", color="#555555", linestyle="None", markerfacecolor="#555555", label=r"Actual $G$"),
        Line2D([0], [0], marker="o", color="#555555", linestyle="None", markerfacecolor="none", label=r"Upper bound $\widehat G$"),
    ]
    fig.legend(
        handles=n_handles + rate_handles + quantity_handles,
        frameon=False,
        fontsize=9,
        ncols=1,
        loc="center left",
        bbox_to_anchor=(0.92, 0.5),
    )
    write_metadata(
        output_dir,
        "bound_validation_actual_vs_upper",
        {
            "figure_number": 6,
            "plot_type": "3D scatter",
            "axes": {"x": "delta", "y": "Pmax", "z": "actual G and rule-level Ghat"},
            "color": "N",
            "marker": "arrival_rate",
            "quantity_encoding": "Actual G uses filled markers; Ghat uses open markers.",
            "rows": "Only bound_check_available rows where NP and PP are proven optimal.",
            "n_values": unique_ints(rows, "N"),
            "available_only": "Current figure uses the bound-checkable subset of completed data; this subset currently contains N=20 because larger N rows need exact NP references.",
        },
    )
    save_figure(fig, output_dir, "bound_validation_actual_vs_upper", write_png=write_png)
    plt.close(fig)


def plot_tradeoff(bound_rows: list[dict[str, str]], output_dir: Path, *, write_png: bool = False) -> None:
    import matplotlib.pyplot as plt

    rows = [row for row in bound_rows if row.get("bound_check_available") == "True"]
    if not rows:
        return
    n_values = unique_ints(rows, "N")
    fig, axes = plt.subplots(1, len(n_values), figsize=(5.0 * len(n_values), 4.2), squeeze=False)
    for col_index, n_value in enumerate(n_values):
        ax = axes[0][col_index]
        panel_label(ax, f"({chr(ord('a') + col_index)}) N={n_value}")
        for (delta, pmax, rate), group in sorted(grouped(filter_rows(rows, n_value=n_value), ("delta", "Pmax", "arrival_rate")).items()):
            times = [value for value in (fvalue(row, "solve_time_s") for row in group) if value is not None]
            gaps = [value for value in (fvalue(row, "actual_optimality_gap") for row in group) if value is not None]
            if not times or not gaps:
                continue
            ax.errorbar(
                [mean(times)],
                [mean(gaps)],
                xerr=[stderr(times)],
                yerr=[stderr(gaps)],
                fmt=PMAX_MARKERS.get(int(pmax), "o"),
                color=DELTA_COLORS.get(int(delta), "#555555"),
                markersize=6,
                capsize=3,
                label=rf"$\delta$={delta}, $P_{{\max}}$={pmax}",
            )
        ax.set_xlabel("Downstream solve time (s)")
        ax.set_ylabel(r"Actual optimality gap $G$")
        ax.grid(True, linewidth=0.5, alpha=0.25)
        apply_axis_typography(ax)
    handles, labels = axes[0][-1].get_legend_handles_labels()
    dedup: dict[str, object] = {}
    for handle, label in zip(handles, labels, strict=False):
        dedup.setdefault(label, handle)
    fig.legend(dedup.values(), dedup.keys(), frameon=False, fontsize=9, ncols=1, loc="center left", bbox_to_anchor=(0.98, 0.5))
    write_metadata(
        output_dir,
        "experimental_tradeoff_solve_time_gap",
        {
            "figure_number": 7,
            "plot_type": "scatter with mean and standard-error bars",
            "axes": {"x": "solve_time_s", "y": "actual_optimality_gap"},
            "color": "delta",
            "marker": "Pmax",
            "aggregation": "Separate N panels. Points average checked rows over replications within each (N, arrival_rate, delta, Pmax) group. Error bars are standard errors.",
            "n_values": n_values,
        },
    )
    save_figure(fig, output_dir, "experimental_tradeoff_solve_time_gap", write_png=write_png)
    plt.close(fig)


def plot_delay_density(rows: list[dict[str, str]], output_dir: Path, *, write_png: bool = False) -> None:
    import matplotlib.pyplot as plt

    n_values = unique_ints(rows, "N")
    deltas = unique_ints([row for row in rows if row.get("method") != "NP"], "delta")
    rates = unique_floats(rows, "arrival_rate")
    pmax_values = unique_ints([row for row in rows if row.get("method") == "PP"], "Pmax")
    if not n_values or not deltas or not rates:
        return
    fig, axes = plt.subplots(len(n_values), 2, figsize=(10.4, max(3.2, 2.8 * len(n_values))), squeeze=False)
    for row_index, n_value in enumerate(n_values):
        ax = axes[row_index][0]
        panel_label(ax, f"({chr(ord('a') + 2 * row_index)}) N={n_value}")
        np_values = metric_values(rows, "objective", n_value=n_value, method="NP")
        np_mean, np_ci = mean_interval(np_values)
        if np_mean is not None:
            yerr = [np_ci] * len(deltas) if np_ci is not None else None
            ax.errorbar(deltas, [np_mean] * len(deltas), yerr=yerr, color=METHOD_COLORS["NP"], marker="x", label="NP", capsize=2)
        chp_y: list[float | None] = []
        chp_err: list[float] = []
        for delta in deltas:
            value, interval = mean_interval(metric_values(rows, "objective", n_value=n_value, method="CHP", delta=delta))
            chp_y.append(value)
            chp_err.append(interval or 0.0)
        ax.errorbar(deltas, chp_y, yerr=chp_err, color=METHOD_COLORS["CHP"], marker="v", label="CHP", capsize=2)
        for pmax in pmax_values:
            y: list[float | None] = []
            err: list[float] = []
            for delta in deltas:
                value, interval = mean_interval(metric_values(rows, "objective", n_value=n_value, method="PP", delta=delta, pmax=pmax))
                y.append(value)
                err.append(interval or 0.0)
            ax.errorbar(deltas, y, yerr=err, color="#666666", marker=PMAX_MARKERS.get(pmax, "o"), label=f"PP Pmax={pmax}", capsize=2)
        ax.set_xlabel(r"Platooning threshold $\delta$")
        ax.set_ylabel("Average vehicle delay")
        ax.grid(True, linewidth=0.5, alpha=0.25)
        apply_axis_typography(ax)

        ax = axes[row_index][1]
        panel_label(ax, f"({chr(ord('a') + 2 * row_index + 1)}) N={n_value}")
        np_y: list[float | None] = []
        np_err: list[float] = []
        for rate in rates:
            value, interval = mean_interval(metric_values(rows, "objective", n_value=n_value, method="NP", rate=rate))
            np_y.append(value)
            np_err.append(interval or 0.0)
        ax.errorbar(rates, np_y, yerr=np_err, color=METHOD_COLORS["NP"], marker="x", label="NP", capsize=2)
        for delta in deltas:
            chp_rate_y: list[float | None] = []
            chp_rate_err: list[float] = []
            for rate in rates:
                value, interval = mean_interval(metric_values(rows, "objective", n_value=n_value, method="CHP", delta=delta, rate=rate))
                chp_rate_y.append(value)
                chp_rate_err.append(interval or 0.0)
            ax.errorbar(rates, chp_rate_y, yerr=chp_rate_err, color=DELTA_COLORS.get(delta, "#555555"), linestyle="--", marker="v", label=f"CHP delta={delta}", capsize=2)
            for pmax in pmax_values:
                pp_rate_y: list[float | None] = []
                pp_rate_err: list[float] = []
                for rate in rates:
                    value, interval = mean_interval(metric_values(rows, "objective", n_value=n_value, method="PP", delta=delta, pmax=pmax, rate=rate))
                    pp_rate_y.append(value)
                    pp_rate_err.append(interval or 0.0)
                ax.errorbar(
                    rates,
                    pp_rate_y,
                    yerr=pp_rate_err,
                    color=DELTA_COLORS.get(delta, "#555555"),
                    marker=PMAX_MARKERS.get(pmax, "o"),
                    linewidth=1.0,
                    alpha=0.75,
                    label=f"PP d={delta}, P={pmax}",
                    capsize=2,
                )
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
    fig.legend(dedup.values(), dedup.keys(), frameon=False, fontsize=9, ncols=2, loc="lower center", bbox_to_anchor=(0.5, -0.02))
    write_metadata(
        output_dir,
        "pp_delay_vs_threshold_density",
        {
            "figure_number": 8,
            "plot_type": "line figure",
            "aggregation": "Panels are stratified by N. Delta panels average over arrival rates and replications within each N/method/delta/Pmax group. Arrival-rate panels average over replications within each N/method/delta/Pmax/rate group. PP is never averaged across Pmax.",
            "uncertainty": "Error bars show approximate 95% mean intervals when at least two replications contribute to a plotted mean. Means are not jittered.",
            "n_values": n_values,
            "pmax_values": pmax_values,
            "delta_colors": DELTA_COLORS,
            "pmax_markers": PMAX_MARKERS,
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
