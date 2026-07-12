"""Formal hS=3 rule-based platooning experiments.

This runner implements the frozen Chapter 5 NP/CHP/PP experiment grid without
calling archived partition optimization, oracle, or budget-selection code. It
checkpoints after every replication and rewrites aggregate outputs so
interrupted runs can resume without duplicating rows.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import sys
from dataclasses import asdict, dataclass
from fractions import Fraction
from pathlib import Path
from statistics import median
from typing import Any

VERIFY_DIR = Path(__file__).resolve().parents[1] / "exhaustive_verification"
if str(VERIFY_DIR) not in sys.path:
    sys.path.insert(0, str(VERIFY_DIR))

from metrics import (  # noqa: E402
    ordering_variables,
    rule_level_bound,
    scaled_rule_level_bound,
    vehicle_level_ordering_variables,
)
from model import Instance, partition_label, scaled_indexed_bound  # noqa: E402
from partition_methods import RuleMethod, form_rule_based_platoons  # noqa: E402
from scheduling_milp import ScheduleResult, solve_downstream_schedule  # noqa: E402


@dataclass(frozen=True)
class FormalHS3Config:
    seed: int
    reps: int
    n_values: tuple[int, ...]
    approaches: int
    arrival_rates: tuple[float, ...]
    thresholds: tuple[int, ...]
    max_platoon_sizes: tuple[int, ...]
    hF: int
    hS: int
    time_limit: float
    np_recovery_time_limit: float
    enable_np_recovery: bool
    threads: int
    formation_repetitions: int
    bound_output_dir: str
    comparison_output_dir: str
    recovery_output_dir: str
    write_trajectory: bool
    trajectory_output_dir: str
    representative_threshold: int
    representative_max_platoon_size: int


def parse_int_tuple(value: str) -> tuple[int, ...]:
    return tuple(int(part.strip()) for part in value.split(",") if part.strip())


def parse_float_tuple(value: str) -> tuple[float, ...]:
    return tuple(float(part.strip()) for part in value.split(",") if part.strip())


def balanced_counts(total_vehicles: int, approaches: int) -> tuple[int, ...]:
    base = total_vehicles // approaches
    remainder = total_vehicles % approaches
    return tuple(base + (1 if index < remainder else 0) for index in range(approaches))


def rate_label(rate: float) -> str:
    return f"{rate:g}".replace(".", "p")


def per_approach_arrival_rate(total_arrival_rate: float, approaches: int) -> float:
    return total_arrival_rate / approaches


def instance_id(n_value: int, total_arrival_rate: float, replication: int, seed: int) -> str:
    return f"N{n_value}_lambda{rate_label(total_arrival_rate)}_rep{replication:03d}_seed{seed}"


def instance_seed(config: FormalHS3Config, n_value: int, total_arrival_rate: float, replication: int) -> int:
    material = json.dumps(
        {
            "base_seed": config.seed,
            "N": n_value,
            "total_arrival_rate": total_arrival_rate,
            "replication": replication,
            "approaches": config.approaches,
            "hF": config.hF,
            "hS": config.hS,
        },
        sort_keys=True,
    ).encode("utf-8")
    return int.from_bytes(hashlib.sha256(material).digest()[:8], "big")


def generate_releases(
    counts: tuple[int, ...],
    approach_arrival_rate: float,
    rng: random.Random,
) -> tuple[tuple[int, ...], ...]:
    releases: list[tuple[int, ...]] = []
    for count in counts:
        current = rng.randint(0, 2)
        row: list[int] = []
        for _ in range(count):
            current += rng.expovariate(approach_arrival_rate)
            row.append(round(current))
        releases.append(tuple(row))
    return tuple(releases)


def build_instance(
    config: FormalHS3Config,
    n_value: int,
    total_arrival_rate: float,
    replication: int,
) -> tuple[Instance, int, str]:
    seed = instance_seed(config, n_value, total_arrival_rate, replication)
    rng = random.Random(seed)
    counts = balanced_counts(n_value, config.approaches)
    approach_arrival_rate = per_approach_arrival_rate(total_arrival_rate, config.approaches)
    instance = Instance(
        counts=counts,
        releases=generate_releases(counts, approach_arrival_rate, rng),
        hF=config.hF,
        hS=config.hS,
    )
    return instance, seed, instance_id(n_value, total_arrival_rate, replication, seed)


def numeric_values(rows: list[dict[str, Any]], field: str) -> list[float]:
    return [float(row[field]) for row in rows if row.get(field) not in (None, "")]


def mean_or_none(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def median_or_none(values: list[float]) -> float | None:
    return float(median(values)) if values else None


def row_key(row: dict[str, Any]) -> tuple[Any, ...]:
    def canonical(value: Any) -> str:
        if value in (None, "", "NA"):
            return "NA"
        return str(value)

    return (
        canonical(row.get("instance_id")),
        canonical(row.get("method")),
        canonical(row.get("threshold")),
        canonical(row.get("max_platoon_size")),
        canonical(row.get("run_role")),
    )


def schedule_fields(schedule: ScheduleResult) -> dict[str, Any]:
    return {
        "status": schedule.status,
        "objective": schedule.objective_average_delay,
        "objective_total_delay": schedule.objective_total_delay,
        "best_bound": schedule.best_bound,
        "terminal_mip_gap": schedule.mip_gap,
        "solve_time_s": schedule.runtime_seconds,
        "model_construction_time_s": schedule.model_construction_seconds,
        "end_to_end_time_s": schedule.end_to_end_seconds,
        "node_count": schedule.node_count,
        "time_to_first_feasible_s": schedule.time_to_first_feasible,
        "sol_count": schedule.sol_count,
    }


def solve_method_row(
    config: FormalHS3Config,
    instance: Instance,
    seed: int,
    instance_id_value: str,
    total_arrival_rate: float,
    replication: int,
    method: RuleMethod,
    threshold: int | None,
    max_platoon_size: int | None,
    run_role: str,
    time_limit: float,
    collect_trajectory: bool = False,
) -> tuple[dict[str, Any], ScheduleResult]:
    formation = form_rule_based_platoons(
        instance,
        method,
        threshold=threshold,
        max_platoon_size=max_platoon_size,
        timing_repetitions=config.formation_repetitions,
    )
    schedule = solve_downstream_schedule(
        instance,
        formation.partition,
        time_limit=time_limit,
        threads=config.threads,
        collect_trajectory=collect_trajectory,
    )
    partition_bound = Fraction(scaled_indexed_bound(instance, formation.partition), instance.N)
    if method == "NP":
        scaled_rule_bound = 0
        rule_bound = Fraction(0, 1)
    else:
        assert threshold is not None
        scaled_rule_bound = scaled_rule_level_bound(instance, threshold, max_platoon_size)
        rule_bound = rule_level_bound(instance, threshold, max_platoon_size)
    ordering_count = ordering_variables(formation.partition)
    vehicle_level_count = vehicle_level_ordering_variables(instance.counts)
    approach_arrival_rate = per_approach_arrival_rate(total_arrival_rate, instance.L)
    row: dict[str, Any] = {
        "instance_id": instance_id_value,
        "seed": seed,
        "replication": replication,
        "N": instance.N,
        "L": instance.L,
        "counts": list(instance.counts),
        "releases": [list(values) for values in instance.releases],
        "lambda": total_arrival_rate,
        "arrival_rate": total_arrival_rate,
        "total_arrival_rate": total_arrival_rate,
        "per_approach_arrival_rate": approach_arrival_rate,
        "h_F": instance.hF,
        "h_S": instance.hS,
        "method": method,
        "run_role": run_role,
        "threshold": threshold,
        "delta": threshold,
        "max_platoon_size": formation.max_platoon_size,
        "Pmax": formation.max_platoon_size,
        "partition": partition_label(formation.partition),
        "number_of_platoons": sum(len(blocks) for blocks in formation.partition),
        "ordering_variable_count": ordering_count,
        "vehicle_level_ordering_variable_count": vehicle_level_count,
        "dimension_reduction_ratio": (
            0.0 if vehicle_level_count == 0 else 1.0 - ordering_count / vehicle_level_count
        ),
        "formation_time_ms": formation.formation_time_ms,
        "formation_repetitions": config.formation_repetitions,
        "partition_specific_upper_bound": float(partition_bound),
        "scaled_partition_specific_upper_bound": scaled_indexed_bound(instance, formation.partition),
        "rule_level_upper_bound": float(rule_bound),
        "scaled_rule_level_upper_bound": scaled_rule_bound,
        "time_limit_s": time_limit,
        "threads": config.threads,
    }
    row.update(schedule_fields(schedule))
    row["end_to_end_time_s"] = row["end_to_end_time_s"] + formation.formation_time_ms / 1000.0
    return row, schedule


def run_replication(
    config: FormalHS3Config,
    n_value: int,
    total_arrival_rate: float,
    replication: int,
    collect_trajectory: bool,
) -> dict[str, Any]:
    instance, seed, instance_id_value = build_instance(config, n_value, total_arrival_rate, replication)
    approach_arrival_rate = per_approach_arrival_rate(total_arrival_rate, config.approaches)
    rows: list[dict[str, Any]] = []
    recovery_rows: list[dict[str, Any]] = []
    trajectory_rows: list[dict[str, Any]] = []

    np_row, np_schedule = solve_method_row(
        config,
        instance,
        seed,
        instance_id_value,
        total_arrival_rate,
        replication,
        "NP",
        None,
        None,
        "initial_30s",
        config.time_limit,
        collect_trajectory=collect_trajectory,
    )
    rows.append(np_row)

    np_optimal_objective = (
        np_schedule.objective_average_delay
        if np_schedule.status == "OPTIMAL"
        else None
    )
    np_optimal_source = "initial_30s" if np_optimal_objective is not None else None

    if config.enable_np_recovery and np_schedule.status != "OPTIMAL":
        recovery_row, recovery_schedule = solve_method_row(
            config,
            instance,
            seed,
            instance_id_value,
            total_arrival_rate,
            replication,
            "NP",
            None,
            None,
            "np_recovery_600s",
            config.np_recovery_time_limit,
            collect_trajectory=collect_trajectory,
        )
        recovery_rows.append(recovery_row)
        if recovery_schedule.status == "OPTIMAL":
            np_optimal_objective = recovery_schedule.objective_average_delay
            np_optimal_source = "np_recovery_600s"
        if collect_trajectory:
            trajectory_rows.extend(trajectory_points(recovery_row, recovery_schedule))

    if collect_trajectory:
        trajectory_rows.extend(trajectory_points(np_row, np_schedule))

    chp_by_threshold: dict[int, dict[str, Any]] = {}
    for threshold in config.thresholds:
        chp_row, chp_schedule = solve_method_row(
            config,
            instance,
            seed,
            instance_id_value,
            total_arrival_rate,
            replication,
            "CHP",
            threshold,
            None,
            "initial_30s",
            config.time_limit,
            collect_trajectory=(
                collect_trajectory and threshold == config.representative_threshold
            ),
        )
        chp_by_threshold[threshold] = chp_row
        rows.append(chp_row)
        if collect_trajectory and threshold == config.representative_threshold:
            trajectory_rows.extend(trajectory_points(chp_row, chp_schedule))

        for max_platoon_size in config.max_platoon_sizes:
            pp_row, pp_schedule = solve_method_row(
                config,
                instance,
                seed,
                instance_id_value,
                total_arrival_rate,
                replication,
                "PP",
                threshold,
                max_platoon_size,
                "initial_30s",
                config.time_limit,
                collect_trajectory=(
                    collect_trajectory
                    and threshold == config.representative_threshold
                    and max_platoon_size == config.representative_max_platoon_size
                ),
            )
            pp_objective = (
                pp_schedule.objective_average_delay
                if pp_schedule.status == "OPTIMAL"
                else None
            )
            chp_objective = (
                chp_schedule.objective_average_delay
                if chp_schedule.status == "OPTIMAL"
                else None
            )
            pp_row["np_30s_status"] = np_row["status"]
            pp_row["np_30s_objective"] = np_row["objective"]
            pp_row["np_30s_terminal_mip_gap"] = np_row["terminal_mip_gap"]
            pp_row["np_30s_solve_time_s"] = np_row["solve_time_s"]
            pp_row["np_recovery_status"] = recovery_rows[0]["status"] if recovery_rows else None
            pp_row["np_recovery_objective"] = recovery_rows[0]["objective"] if recovery_rows else None
            pp_row["np_optimal_objective"] = np_optimal_objective
            pp_row["np_optimal_source"] = np_optimal_source
            pp_row["matching_chp_objective"] = chp_objective
            pp_row["pp_optimal_objective"] = pp_objective
            pp_row["actual_optimality_gap"] = (
                pp_objective - np_optimal_objective
                if pp_objective is not None and np_optimal_objective is not None
                else None
            )
            pp_row["bound_check_available"] = pp_row["actual_optimality_gap"] is not None
            if pp_row["bound_check_available"]:
                pp_row["bound_slack"] = pp_row["rule_level_upper_bound"] - pp_row["actual_optimality_gap"]
                pp_row["bound_valid"] = pp_row["bound_slack"] >= -1e-7
            else:
                pp_row["bound_slack"] = None
                pp_row["bound_valid"] = None
            pp_row["delay_order_check_available"] = (
                np_optimal_objective is not None
                and chp_objective is not None
                and pp_objective is not None
            )
            pp_row["np_pp_chp_delay_order_holds"] = (
                np_optimal_objective <= pp_objective + 1e-7 <= chp_objective + 1e-7
                if pp_row["delay_order_check_available"]
                else None
            )
            rows.append(pp_row)
            if (
                collect_trajectory
                and threshold == config.representative_threshold
                and max_platoon_size == config.representative_max_platoon_size
            ):
                trajectory_rows.extend(trajectory_points(pp_row, pp_schedule))

    for row in rows:
        row["np_30s_status"] = np_row["status"]
        row["np_30s_objective"] = np_row["objective"]
        row["np_recovery_status"] = recovery_rows[0]["status"] if recovery_rows else None
        row["np_recovery_objective"] = recovery_rows[0]["objective"] if recovery_rows else None
        row["np_optimal_objective"] = np_optimal_objective
        row["np_optimal_source"] = np_optimal_source
        if row["method"] in ("NP", "CHP"):
            row["actual_optimality_gap"] = (
                row["objective"] - np_optimal_objective
                if row["status"] == "OPTIMAL" and row["objective"] is not None and np_optimal_objective is not None
                else None
            )
            row["bound_check_available"] = False
            row["bound_valid"] = None
            row["bound_slack"] = None
            row["delay_order_check_available"] = False
            row["np_pp_chp_delay_order_holds"] = None
        if row["method"] == "CHP":
            row["matching_chp_objective"] = row["objective"] if row["status"] == "OPTIMAL" else None
        if row["method"] == "NP":
            row["matching_chp_objective"] = None
            row["pp_optimal_objective"] = None

    return {
        "config": asdict(config),
        "instance": {
            "instance_id": instance_id_value,
            "seed": seed,
            "replication": replication,
            "N": n_value,
            "lambda": total_arrival_rate,
            "arrival_rate": total_arrival_rate,
            "total_arrival_rate": total_arrival_rate,
            "per_approach_arrival_rate": approach_arrival_rate,
            "counts": list(instance.counts),
            "releases": [list(values) for values in instance.releases],
        },
        "rows": rows,
        "recovery_rows": recovery_rows,
        "trajectory_rows": trajectory_rows,
    }


def trajectory_points(row: dict[str, Any], schedule: ScheduleResult) -> list[dict[str, Any]]:
    points: list[dict[str, Any]] = []
    for index, point in enumerate(schedule.incumbent_trajectory):
        points.append(
            {
                "instance_id": row["instance_id"],
                "N": row["N"],
                "lambda": row["lambda"],
                "arrival_rate": row["arrival_rate"],
                "total_arrival_rate": row["total_arrival_rate"],
                "per_approach_arrival_rate": row["per_approach_arrival_rate"],
                "replication": row["replication"],
                "method": row["method"],
                "threshold": row["threshold"],
                "delta": row["delta"],
                "max_platoon_size": row["max_platoon_size"],
                "Pmax": row["Pmax"],
                "run_role": row["run_role"],
                "point_index": index,
                **point,
            }
        )
    return points


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    key: json.dumps(value) if isinstance(value, (list, dict, tuple)) else value
                    for key, value in row.items()
                }
            )


def parse_csv_value(value: str) -> Any:
    if value == "":
        return None
    if value == "True":
        return True
    if value == "False":
        return False
    if value.startswith("[") or value.startswith("{"):
        return json.loads(value)
    return value


def read_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return [
            {key: parse_csv_value(value) for key, value in row.items()}
            for row in csv.DictReader(handle)
        ]


def summarize_comparison(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for row in rows:
        key = (
            int(row["N"]),
            float(row["arrival_rate"]),
            row["method"],
            row.get("threshold") if row.get("threshold") is not None else "NA",
            row.get("max_platoon_size") if row.get("max_platoon_size") is not None else "NA",
        )
        groups.setdefault(key, []).append(row)
    summary: list[dict[str, Any]] = []
    for (n_value, arrival_rate, method, threshold, pmax), group in sorted(groups.items()):
        delay_order_rows = [row for row in group if row.get("delay_order_check_available") is True]
        summary.append(
            {
                "N": n_value,
                "lambda": arrival_rate,
                "arrival_rate": arrival_rate,
                "total_arrival_rate": arrival_rate,
                "per_approach_arrival_rate": arrival_rate / float(group[0].get("L", 4)),
                "method": method,
                "threshold": threshold,
                "delta": threshold,
                "max_platoon_size": pmax,
                "Pmax": pmax,
                "case_count": len(group),
                "optimality_rate": sum(1 for row in group if row.get("status") == "OPTIMAL") / len(group),
                "mean_average_delay_or_incumbent": mean_or_none(numeric_values(group, "objective")),
                "median_average_delay_or_incumbent": median_or_none(numeric_values(group, "objective")),
                "mean_terminal_mip_gap": mean_or_none(numeric_values(group, "terminal_mip_gap")),
                "mean_solve_time_s": mean_or_none(numeric_values(group, "solve_time_s")),
                "mean_end_to_end_time_s": mean_or_none(numeric_values(group, "end_to_end_time_s")),
                "mean_model_construction_time_s": mean_or_none(numeric_values(group, "model_construction_time_s")),
                "mean_node_count": mean_or_none(numeric_values(group, "node_count")),
                "mean_number_of_platoons": mean_or_none(numeric_values(group, "number_of_platoons")),
                "mean_ordering_variable_count": mean_or_none(numeric_values(group, "ordering_variable_count")),
                "mean_dimension_reduction_ratio": mean_or_none(numeric_values(group, "dimension_reduction_ratio")),
                "delay_order_check_case_count": len(delay_order_rows),
                "delay_order_failure_count": sum(
                    1 for row in delay_order_rows if row.get("np_pp_chp_delay_order_holds") is not True
                ),
            }
        )
    return summary


def summarize_bound(rows: list[dict[str, Any]]) -> dict[str, Any]:
    pp_rows = [row for row in rows if row.get("method") == "PP"]
    checkable = [row for row in pp_rows if row.get("bound_check_available") is True]
    violations = [row for row in checkable if row.get("bound_valid") is not True]
    coverage: dict[str, int] = {}
    for row in checkable:
        key = f"N={row['N']},total_arrival_rate={row['arrival_rate']}"
        coverage[key] = coverage.get(key, 0) + 1
    return {
        "total_pp_rows": len(pp_rows),
        "bound_checkable_rows": len(checkable),
        "unique_checked_instances": len({row["instance_id"] for row in checkable}),
        "coverage_by_N_and_total_arrival_rate": coverage,
        "violation_count": len(violations),
        "mean_actual_gap": mean_or_none(numeric_values(checkable, "actual_optimality_gap")),
        "median_actual_gap": median_or_none(numeric_values(checkable, "actual_optimality_gap")),
        "mean_rule_level_upper_bound": mean_or_none(numeric_values(checkable, "rule_level_upper_bound")),
        "median_rule_level_upper_bound": median_or_none(numeric_values(checkable, "rule_level_upper_bound")),
        "mean_bound_slack": mean_or_none(numeric_values(checkable, "bound_slack")),
        "median_bound_slack": median_or_none(numeric_values(checkable, "bound_slack")),
        "minimum_bound_slack": min(numeric_values(checkable, "bound_slack")) if checkable else None,
    }


def aggregate_checks(config: FormalHS3Config, rows: list[dict[str, Any]]) -> dict[str, Any]:
    keys = [row_key(row) for row in rows]
    duplicate_keys = sorted({key for key in keys if keys.count(key) > 1})
    expected_instances = len(config.n_values) * len(config.arrival_rates) * config.reps
    expected_rows = expected_instances * (1 + len(config.thresholds) + len(config.thresholds) * len(config.max_platoon_sizes))
    pp_rows = [row for row in rows if row.get("method") == "PP"]
    return {
        "expected_instance_count": expected_instances,
        "observed_instance_count": len({row["instance_id"] for row in rows}),
        "expected_initial_row_count": expected_rows,
        "observed_initial_row_count": len(rows),
        "duplicate_row_key_count": len(duplicate_keys),
        "duplicate_row_keys": [list(key) for key in duplicate_keys[:20]],
        "expected_pp_rows": expected_instances * len(config.thresholds) * len(config.max_platoon_sizes),
        "observed_pp_rows": len(pp_rows),
        "bound_violation_count": sum(1 for row in pp_rows if row.get("bound_valid") is False),
        "delay_order_failure_count": sum(
            1 for row in pp_rows if row.get("np_pp_chp_delay_order_holds") is False
        ),
    }


def write_outputs(
    config: FormalHS3Config,
    rows: list[dict[str, Any]],
    recovery_rows: list[dict[str, Any]],
    trajectory_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    comparison_dir = Path(config.comparison_output_dir)
    bound_dir = Path(config.bound_output_dir)
    recovery_dir = Path(config.recovery_output_dir)
    trajectory_dir = Path(config.trajectory_output_dir)
    for directory in (comparison_dir, bound_dir, recovery_dir, trajectory_dir):
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "config_manifest.json").write_text(json.dumps(asdict(config), indent=2), encoding="utf-8")

    rows = sorted(rows, key=row_key)
    recovery_rows = sorted(recovery_rows, key=row_key)
    pp_rows = [row for row in rows if row.get("method") == "PP"]
    bound_summary = summarize_bound(rows)
    comparison_summary = summarize_comparison(rows)
    checks = aggregate_checks(config, rows)
    payload = {
        "config": asdict(config),
        "checks": checks,
        "bound_statistics": bound_summary,
        "comparison_summary_rows": len(comparison_summary),
        "recovery_row_count": len(recovery_rows),
        "trajectory_row_count": len(trajectory_rows),
    }

    write_csv(comparison_dir / "formal_comparison_rows.csv", rows)
    write_csv(comparison_dir / "formal_comparison_summary.csv", comparison_summary)
    (comparison_dir / "formal_comparison_summary.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    write_csv(bound_dir / "formal_bound_rows.csv", pp_rows)
    write_csv(bound_dir / "formal_bound_checkable_rows.csv", [row for row in pp_rows if row.get("bound_check_available") is True])
    (bound_dir / "formal_bound_summary.json").write_text(json.dumps(bound_summary | {"checks": checks}, indent=2), encoding="utf-8")

    write_csv(recovery_dir / "formal_np_recovery_rows.csv", recovery_rows)
    (recovery_dir / "formal_np_recovery_summary.json").write_text(
        json.dumps(
            {
                "recovery_row_count": len(recovery_rows),
                "optimal_recovery_count": sum(1 for row in recovery_rows if row.get("status") == "OPTIMAL"),
                "status_counts": status_counts(recovery_rows),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    if trajectory_rows:
        write_csv(trajectory_dir / "gurobi_incumbent_trajectories.csv", trajectory_rows)
    return payload


def status_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        status = str(row.get("status"))
        counts[status] = counts.get(status, 0) + 1
    return counts


def checkpoint_path(config: FormalHS3Config, n_value: int, arrival_rate: float, replication: int) -> Path:
    return Path(config.comparison_output_dir) / "checkpoints" / f"N{n_value}_lambda{rate_label(arrival_rate)}_rep{replication:03d}.json"


def completed_from_rows(rows: list[dict[str, Any]]) -> set[tuple[int, float, int]]:
    completed: set[tuple[int, float, int]] = set()
    for row in rows:
        if row.get("N") in (None, "") or row.get("arrival_rate") in (None, "") or row.get("replication") in (None, ""):
            continue
        completed.add((int(row["N"]), float(row["arrival_rate"]), int(row["replication"])))
    return completed


def load_existing_outputs(config: FormalHS3Config) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], set[tuple[int, float, int]]]:
    rows = read_csv(Path(config.comparison_output_dir) / "formal_comparison_rows.csv")
    recovery_rows = read_csv(Path(config.recovery_output_dir) / "formal_np_recovery_rows.csv")
    trajectory_rows = read_csv(Path(config.trajectory_output_dir) / "gurobi_incumbent_trajectories.csv")
    return rows, recovery_rows, trajectory_rows, completed_from_rows(rows)


def load_checkpoints(config: FormalHS3Config) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], set[tuple[int, float, int]]]:
    rows: list[dict[str, Any]] = []
    recovery_rows: list[dict[str, Any]] = []
    trajectory_rows: list[dict[str, Any]] = []
    completed: set[tuple[int, float, int]] = set()
    checkpoint_dir = Path(config.comparison_output_dir) / "checkpoints"
    for path in sorted(checkpoint_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        instance = payload["instance"]
        key = (int(instance["N"]), float(instance["arrival_rate"]), int(instance["replication"]))
        if key in completed:
            raise RuntimeError(f"duplicate checkpoint for {key}")
        completed.add(key)
        rows.extend(payload.get("rows", []))
        recovery_rows.extend(payload.get("recovery_rows", []))
        trajectory_rows.extend(payload.get("trajectory_rows", []))
    return rows, recovery_rows, trajectory_rows, completed


def write_checkpoint_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp_path.replace(path)


def merge_rows_by_key(
    existing_rows: list[dict[str, Any]],
    new_rows: list[dict[str, Any]],
    key_func,
) -> list[dict[str, Any]]:
    merged = {key_func(row): row for row in existing_rows}
    for row in new_rows:
        merged[key_func(row)] = row
    return list(merged.values())


def trajectory_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        row_key(row),
        str(row.get("point_index")),
        str(row.get("time_s")),
        str(row.get("incumbent_objective")),
        str(row.get("best_bound")),
    )


def run(
    config: FormalHS3Config,
    resume: bool,
    *,
    rep_start: int = 0,
    rep_end_exclusive: int | None = None,
    checkpoint_only: bool = False,
    append_existing_outputs: bool = False,
) -> dict[str, Any]:
    Path(config.comparison_output_dir).mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    recovery_rows: list[dict[str, Any]] = []
    trajectory_rows: list[dict[str, Any]] = []
    completed: set[tuple[int, float, int]] = set()
    if append_existing_outputs and not checkpoint_only:
        rows, recovery_rows, trajectory_rows, completed = load_existing_outputs(config)
    if resume:
        checkpoint_rows, checkpoint_recovery_rows, checkpoint_trajectory_rows, checkpoint_completed = load_checkpoints(config)
        rows = merge_rows_by_key(rows, checkpoint_rows, row_key)
        recovery_rows = merge_rows_by_key(recovery_rows, checkpoint_recovery_rows, row_key)
        trajectory_rows = merge_rows_by_key(trajectory_rows, checkpoint_trajectory_rows, trajectory_key)
        completed |= checkpoint_completed
    rep_end = config.reps if rep_end_exclusive is None else rep_end_exclusive
    if rep_start < 0 or rep_end < rep_start or rep_end > config.reps:
        raise ValueError("replication range must satisfy 0 <= rep_start <= rep_end <= reps")
    newly_completed = 0
    for n_value in config.n_values:
        for arrival_rate in config.arrival_rates:
            for replication in range(rep_start, rep_end):
                key = (n_value, arrival_rate, replication)
                if key in completed:
                    continue
                collect_trajectory = config.write_trajectory
                payload = run_replication(config, n_value, arrival_rate, replication, collect_trajectory)
                path = checkpoint_path(config, n_value, arrival_rate, replication)
                write_checkpoint_atomic(path, payload)
                rows.extend(payload["rows"])
                recovery_rows.extend(payload["recovery_rows"])
                trajectory_rows.extend(payload["trajectory_rows"])
                completed.add(key)
                newly_completed += 1
                if not checkpoint_only:
                    write_outputs(config, rows, recovery_rows, trajectory_rows)
    if checkpoint_only:
        return {
            "config": asdict(config),
            "checkpoint_only": True,
            "rep_start": rep_start,
            "rep_end_exclusive": rep_end,
            "newly_completed_replications": newly_completed,
            "completed_checkpoint_count": len(completed),
        }
    return write_outputs(config, rows, recovery_rows, trajectory_rows)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=20260712)
    parser.add_argument("--reps", type=int, default=20)
    parser.add_argument("--n-values", default="20,40,60,80")
    parser.add_argument("--approaches", type=int, default=4)
    parser.add_argument("--arrival-rates", default="0.5,1.0,1.5,2.0,2.5")
    parser.add_argument("--thresholds", default="2,4,6,8")
    parser.add_argument("--max-platoon-sizes", default="2,4,6,8")
    parser.add_argument("--hF", type=int, default=1)
    parser.add_argument("--hS", type=int, default=3)
    parser.add_argument("--time-limit", type=float, default=30.0)
    parser.add_argument("--np-recovery-time-limit", type=float, default=600.0)
    parser.add_argument("--skip-np-recovery", action="store_true")
    parser.add_argument("--threads", type=int, default=12)
    parser.add_argument("--formation-repetitions", type=int, default=20)
    parser.add_argument("--bound-output-dir", default="../../results/rule_based_experiments/formal_bound_hS3")
    parser.add_argument("--comparison-output-dir", default="../../results/rule_based_experiments/formal_pp_hS3")
    parser.add_argument("--recovery-output-dir", default="../../results/rule_based_experiments/formal_np_recovery_600s_hS3")
    parser.add_argument("--write-trajectory", action="store_true")
    parser.add_argument("--trajectory-output-dir", default="../../results/rule_based_experiments/formal_pp_hS3")
    parser.add_argument("--representative-threshold", type=int, default=4)
    parser.add_argument("--representative-max-platoon-size", type=int, default=4)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--rep-start", type=int, default=0)
    parser.add_argument("--rep-end-exclusive", type=int)
    parser.add_argument(
        "--checkpoint-only",
        action="store_true",
        help="Write per-replication checkpoints only. Use for parallel chunks, then run a single aggregate pass.",
    )
    parser.add_argument(
        "--append-existing-outputs",
        action="store_true",
        help="Seed aggregation from existing formal CSV outputs before adding resumed checkpoints.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    config = FormalHS3Config(
        seed=args.seed,
        reps=args.reps,
        n_values=parse_int_tuple(args.n_values),
        approaches=args.approaches,
        arrival_rates=parse_float_tuple(args.arrival_rates),
        thresholds=parse_int_tuple(args.thresholds),
        max_platoon_sizes=parse_int_tuple(args.max_platoon_sizes),
        hF=args.hF,
        hS=args.hS,
        time_limit=args.time_limit,
        np_recovery_time_limit=args.np_recovery_time_limit,
        enable_np_recovery=not args.skip_np_recovery,
        threads=args.threads,
        formation_repetitions=args.formation_repetitions,
        bound_output_dir=args.bound_output_dir,
        comparison_output_dir=args.comparison_output_dir,
        recovery_output_dir=args.recovery_output_dir,
        write_trajectory=args.write_trajectory,
        trajectory_output_dir=args.trajectory_output_dir,
        representative_threshold=args.representative_threshold,
        representative_max_platoon_size=args.representative_max_platoon_size,
    )
    payload = run(
        config,
        resume=args.resume,
        rep_start=args.rep_start,
        rep_end_exclusive=args.rep_end_exclusive,
        checkpoint_only=args.checkpoint_only,
        append_existing_outputs=args.append_existing_outputs,
    )
    print(json.dumps(payload, indent=2))
    if payload.get("checkpoint_only"):
        return 0
    checks = payload["checks"]
    return 1 if checks["duplicate_row_key_count"] or checks["bound_violation_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
