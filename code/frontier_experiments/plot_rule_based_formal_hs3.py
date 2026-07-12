"""Generate formal hS=3 rule-based experiment figures."""

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


def save_both(fig, output_dir: Path, stem: str) -> None:
    fig.tight_layout()
    fig.savefig(output_dir / f"{stem}.pdf", bbox_inches="tight")
    fig.savefig(output_dir / f"{stem}.png", dpi=300, bbox_inches="tight")


def write_metadata(output_dir: Path, stem: str, metadata: dict[str, object]) -> None:
    (output_dir / f"{stem}_metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def plot_bound_validation(bound_rows: list[dict[str, str]], output_dir: Path) -> None:
    import matplotlib.pyplot as plt

    rows = [row for row in bound_rows if row.get("bound_check_available") == "True"]
    if not rows:
        return
    fig, axes = plt.subplots(1, 2, figsize=(11.4, 4.2))
    ax = axes[0]
    for (delta, pmax), group in sorted(grouped(rows, ("delta", "Pmax")).items()):
        pairs = [
            (actual, upper)
            for actual, upper in (
                (fvalue(row, "actual_optimality_gap"), fvalue(row, "rule_level_upper_bound")) for row in group
            )
            if actual is not None and upper is not None
        ]
        if not pairs:
            continue
        ax.scatter(
            [pair[0] for pair in pairs],
            [pair[1] for pair in pairs],
            s=32,
            alpha=0.74,
            color=DELTA_COLORS.get(int(delta), "#555555"),
            marker=PMAX_MARKERS.get(int(pmax), "o"),
            label=f"d={delta}, P={pmax}",
        )
    max_axis = max(
        max(float(row["actual_optimality_gap"]) for row in rows),
        max(float(row["rule_level_upper_bound"]) for row in rows),
    )
    ax.plot([0, max_axis], [0, max_axis], color="#666666", linewidth=1.0, linestyle="--")
    ax.text(0.02, 0.98, "Bound valid; conservative", transform=ax.transAxes, va="top")
    ax.set_title("(a) Actual G vs. Ghat")
    ax.set_xlabel("Actual G")
    ax.set_ylabel("Rule-level upper bound Ghat")
    ax.grid(True, linewidth=0.5, alpha=0.25)
    ax = axes[1]
    labels: list[str] = []
    centers: list[float] = []
    medians: list[float] = []
    lower_errors: list[float] = []
    upper_errors: list[float] = []
    colors: list[str] = []
    markers: list[str] = []
    for index, ((delta, pmax), group) in enumerate(sorted(grouped(rows, ("delta", "Pmax")).items())):
        ratios = []
        for row in group:
            actual = fvalue(row, "actual_optimality_gap")
            upper = fvalue(row, "rule_level_upper_bound")
            if actual is not None and upper is not None and upper > 0:
                ratios.append(actual / upper)
        if not ratios:
            continue
        q50 = median(ratios)
        q10 = sorted(ratios)[max(0, int(0.10 * (len(ratios) - 1)))]
        q90 = sorted(ratios)[min(len(ratios) - 1, int(0.90 * (len(ratios) - 1)))]
        centers.append(float(index))
        labels.append(f"{delta}/{pmax}")
        medians.append(q50)
        lower_errors.append(q50 - q10)
        upper_errors.append(q90 - q50)
        colors.append(DELTA_COLORS.get(int(delta), "#555555"))
        markers.append(PMAX_MARKERS.get(int(pmax), "o"))
    for x_value, y_value, lo, hi, color, marker in zip(centers, medians, lower_errors, upper_errors, colors, markers, strict=True):
        ax.errorbar(
            [x_value],
            [y_value],
            yerr=[[lo], [hi]],
            fmt=marker,
            color=color,
            markersize=6,
            capsize=3,
        )
    ax.axhline(1.0, color="#666666", linewidth=1.0, linestyle="--")
    ax.set_title("(b) Bound utilization G/Ghat")
    ax.set_ylabel("G/Ghat median with 10-90% interval")
    ax.set_xlabel("delta/Pmax")
    ax.set_xticks(centers)
    ax.set_xticklabels(labels, fontsize=7, rotation=90)
    ax.grid(True, axis="y", linewidth=0.5, alpha=0.25)
    handles, legend_labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, legend_labels, frameon=False, fontsize=7, ncols=1, loc="center left", bbox_to_anchor=(1.0, 0.5))
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
    ax.legend(frameon=False, fontsize=8, ncols=2, loc="center left", bbox_to_anchor=(1.02, 0.5))
    save_both(fig, output_dir, "experimental_tradeoff_solve_time_gap")
    plt.close(fig)


def plot_delay_density(rows: list[dict[str, str]], output_dir: Path) -> None:
    import matplotlib.pyplot as plt

    n_values = unique_ints(rows, "N")
    deltas = unique_ints([row for row in rows if row.get("method") != "NP"], "delta")
    rates = unique_floats(rows, "arrival_rate")
    pmax_values = unique_ints([row for row in rows if row.get("method") == "PP"], "Pmax")
    if not n_values or not deltas or not rates:
        return
    fig, axes = plt.subplots(len(n_values), 2, figsize=(10.4, max(3.2, 2.6 * len(n_values))), squeeze=False)
    for row_index, n_value in enumerate(n_values):
        ax = axes[row_index][0]
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
        ax.set_title(f"N={n_value}")
        ax.set_xlabel("Delta")
        ax.set_ylabel("Average delay or incumbent")
        ax.grid(True, linewidth=0.5, alpha=0.25)

        ax = axes[row_index][1]
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
        ax.set_title(f"N={n_value}")
        ax.set_xlabel("Arrival rate")
        ax.set_ylabel("Average delay or incumbent")
        ax.grid(True, linewidth=0.5, alpha=0.25)
    for legend_ax in (axes[0][0], axes[0][1]):
        handles, labels = legend_ax.get_legend_handles_labels()
        dedup: dict[str, object] = {}
        for handle, label in zip(handles, labels, strict=False):
            dedup.setdefault(label, handle)
        legend_ax.legend(dedup.values(), dedup.keys(), frameon=False, fontsize=6, ncols=1, loc="center left", bbox_to_anchor=(1.02, 0.5))
    write_metadata(
        output_dir,
        "pp_delay_vs_threshold_density",
        {
            "aggregation": "Panels are stratified by N. Delta panels average over arrival rates and replications within each N/method/delta/Pmax group. Arrival-rate panels average over replications within each N/method/delta/Pmax/rate group. PP is never averaged across Pmax.",
            "uncertainty": "Error bars show approximate 95% mean intervals when at least two replications contribute to a plotted mean. Means are not jittered.",
            "n_values": n_values,
            "pmax_values": pmax_values,
            "delta_colors": DELTA_COLORS,
            "pmax_markers": PMAX_MARKERS,
        },
    )
    save_both(fig, output_dir, "pp_delay_vs_threshold_density")
    plt.close(fig)


def plot_time_platoons(rows: list[dict[str, str]], output_dir: Path) -> None:
    import matplotlib.pyplot as plt

    n_values = unique_ints(rows, "N")
    deltas = unique_ints([row for row in rows if row.get("method") != "NP"], "delta")
    rates = unique_floats(rows, "arrival_rate")
    pmax_values = unique_ints([row for row in rows if row.get("method") == "PP"], "Pmax")
    if not n_values or not deltas or not rates:
        return
    fig, axes = plt.subplots(len(n_values), 4, figsize=(15.2, max(3.0, 2.7 * len(n_values))), squeeze=False)
    panel_specs = [
        ("solve_time_s", "delta", "Delta", "Solve time (s)"),
        ("solve_time_s", "arrival_rate", "Arrival rate", "Solve time (s)"),
        ("number_of_platoons", "delta", "Delta", "Number of platoons"),
        ("number_of_platoons", "arrival_rate", "Arrival rate", "Number of platoons"),
    ]
    for row_index, n_value in enumerate(n_values):
        for col_index, (metric, x_field, xlabel, ylabel) in enumerate(panel_specs):
            ax = axes[row_index][col_index]
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
            ax.set_title(f"N={n_value}")
            ax.set_xlabel(xlabel)
            ax.set_ylabel(ylabel)
            if metric == "solve_time_s":
                ax.set_yscale("log")
            ax.grid(True, linewidth=0.5, alpha=0.25)
    handles, labels = axes[0][1].get_legend_handles_labels()
    dedup: dict[str, object] = {}
    for handle, label in zip(handles, labels, strict=False):
        dedup.setdefault(label, handle)
    axes[0][1].legend(dedup.values(), dedup.keys(), frameon=False, fontsize=6, ncols=1, loc="center left", bbox_to_anchor=(1.02, 0.5))
    write_metadata(
        output_dir,
        "pp_time_and_platoon_count",
        {
            "aggregation": "Panels are stratified by N. Delta panels average over arrival rates and replications within each N/method/delta/Pmax group. Arrival-rate panels average over replications within each N/method/delta/Pmax/rate group. PP is never averaged across Pmax.",
            "n_values": n_values,
            "pmax_values": pmax_values,
            "delta_colors": DELTA_COLORS,
            "pmax_markers": PMAX_MARKERS,
        },
    )
    save_both(fig, output_dir, "pp_time_and_platoon_count")
    plt.close(fig)


def plot_trajectories(
    trajectory_rows: list[dict[str, str]],
    comparison_rows: list[dict[str, str]],
    output_dir: Path,
    representative_delta: int = 4,
    representative_pmax: int = 4,
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
    provisional = selected_n < 40 or max_n_present < 40
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    groups: dict[tuple[str, str, str, str], list[dict[str, str]]] = {}
    for row in rows:
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
    ax.set_title(f"{selected_instance} (provisional)" if provisional else selected_instance)
    ax.grid(True, linewidth=0.5, alpha=0.25)
    ax.legend(frameon=False, fontsize=8, loc="center left", bbox_to_anchor=(1.02, 0.5))
    write_metadata(
        output_dir,
        "gurobi_solution_quality_over_time",
        {
            "aggregation": "One selected instance only. Series are NP, CHP at representative delta, and PP at representative delta/Pmax from real callback rows.",
            "status": "provisional" if provisional else "representative_selected_after_N40_search",
            "selection_policy": "Prefer N>=40 instances where NP has multiple incumbent updates or reaches the time limit, PP has at least two callback points, and NP/CHP/PP rows share the same instance. Fall back to the first complete trajectory instance if no better instance exists.",
            "selected_instance_id": selected_instance,
            "selected_N": selected_n,
            "representative_delta": representative_delta,
            "representative_pmax": representative_pmax,
            "instance_ids_present": sorted({row.get("instance_id", "") for row in trajectory_rows if row.get("instance_id")}),
        },
    )
    save_both(fig, output_dir, "gurobi_solution_quality_over_time")
    plt.close(fig)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bound-dir", type=Path, default=Path("../../results/rule_based_experiments/formal_bound_hS3"))
    parser.add_argument("--comparison-dir", type=Path, default=Path("../../results/rule_based_experiments/formal_pp_hS3"))
    parser.add_argument("--output-dir", type=Path, default=Path("../../results/rule_based_experiments/formal_figures_hS3"))
    parser.add_argument("--representative-threshold", type=int, default=4)
    parser.add_argument("--representative-max-platoon-size", type=int, default=4)
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
    plot_trajectories(
        trajectory_rows,
        comparison_rows,
        args.output_dir,
        representative_delta=args.representative_threshold,
        representative_pmax=args.representative_max_platoon_size,
    )
    print(args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
