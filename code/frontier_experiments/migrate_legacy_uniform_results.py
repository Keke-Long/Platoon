"""Migrate approved legacy cases into the uniform 600-second experiment.

Legacy rows that already proved optimal are reused. Rows that reached the old
time limit are solved again on the stored instance and partition with the new
uniform limit. One checkpoint is written per traffic instance so the main
formal runner can aggregate migrated and newly generated cases together.
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

VERIFY_DIR = Path(__file__).resolve().parents[1] / "exhaustive_verification"
if str(VERIFY_DIR) not in sys.path:
    sys.path.insert(0, str(VERIFY_DIR))

from model import Instance, Partition
from rule_based_formal_hs3 import (
    NUMERICAL_COMPARISON_TOLERANCE,
    canonical_average_delay,
    read_csv,
    schedule_fields,
    trajectory_points,
    write_checkpoint_atomic,
)
from scheduling_milp import solve_downstream_schedule


def parse_int_tuple(value: str) -> tuple[int, ...]:
    return tuple(int(part.strip()) for part in value.split(",") if part.strip())


def as_partition(value: Any) -> Partition:
    return tuple(tuple(int(size) for size in blocks) for blocks in value)


def as_instance(row: dict[str, Any]) -> Instance:
    return Instance(
        counts=tuple(int(count) for count in row["counts"]),
        releases=tuple(tuple(int(value) for value in releases) for releases in row["releases"]),
        hF=int(row["h_F"]),
        hS=int(row["h_S"]),
    )


def normalized_row(row: dict[str, Any], time_limit: float) -> dict[str, Any]:
    normalized = dict(row)
    normalized["run_role"] = "uniform_600s"
    normalized["time_limit_s"] = time_limit
    for field in tuple(normalized):
        if field.startswith("np_30s") or field.startswith("np_recovery"):
            normalized.pop(field)
    return normalized


def refresh_cross_method_fields(rows: list[dict[str, Any]]) -> None:
    np_row = next(row for row in rows if row["method"] == "NP")
    vehicle_count = int(np_row["N"])
    np_optimal = (
        canonical_average_delay(np_row["objective"], vehicle_count)
        if np_row.get("status") == "OPTIMAL"
        else None
    )
    np_source = "uniform_600s" if np_optimal is not None else None
    chp_by_threshold = {
        int(row["threshold"]): row
        for row in rows
        if row["method"] == "CHP"
    }

    for row in rows:
        row["np_status"] = np_row.get("status")
        row["np_objective"] = np_row.get("objective")
        row["np_terminal_mip_gap"] = np_row.get("terminal_mip_gap")
        row["np_solve_time_s"] = np_row.get("solve_time_s")
        row["np_optimal_objective"] = np_optimal
        row["np_optimal_source"] = np_source

        if row["method"] == "PP":
            threshold = int(row["threshold"])
            chp_row = chp_by_threshold[threshold]
            pp_optimal = (
                canonical_average_delay(row["objective"], vehicle_count)
                if row.get("status") == "OPTIMAL"
                else None
            )
            chp_optimal = (
                canonical_average_delay(chp_row["objective"], vehicle_count)
                if chp_row.get("status") == "OPTIMAL"
                else None
            )
            row["matching_chp_objective"] = chp_optimal
            row["pp_optimal_objective"] = pp_optimal
            actual_gap = (
                float(pp_optimal) - float(np_optimal)
                if pp_optimal is not None and np_optimal is not None
                else None
            )
            row["actual_optimality_gap"] = actual_gap
            row["bound_check_available"] = actual_gap is not None
            if actual_gap is not None:
                slack = float(row["rule_level_upper_bound"]) - actual_gap
                row["bound_slack"] = slack
                row["bound_valid"] = slack >= -NUMERICAL_COMPARISON_TOLERANCE
            else:
                row["bound_slack"] = None
                row["bound_valid"] = None
            order_check = np_optimal is not None and pp_optimal is not None and chp_optimal is not None
            row["delay_order_check_available"] = order_check
            row["np_pp_chp_delay_order_holds"] = (
                float(np_optimal)
                <= float(pp_optimal) + NUMERICAL_COMPARISON_TOLERANCE
                <= float(chp_optimal) + NUMERICAL_COMPARISON_TOLERANCE
                if order_check
                else None
            )
            continue

        row["actual_optimality_gap"] = (
            float(row["objective"]) - float(np_optimal)
            if row.get("status") == "OPTIMAL" and row.get("objective") is not None and np_optimal is not None
            else None
        )
        row["bound_check_available"] = False
        row["bound_valid"] = None
        row["bound_slack"] = None
        row["delay_order_check_available"] = False
        row["np_pp_chp_delay_order_holds"] = None
        if row["method"] == "CHP":
            row["matching_chp_objective"] = row.get("objective") if row.get("status") == "OPTIMAL" else None
        else:
            row["matching_chp_objective"] = None
            row["pp_optimal_objective"] = None


def migrate_instance(
    rows: list[dict[str, Any]],
    *,
    time_limit: float,
    threads: int,
    collect_trajectory: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    migrated = [normalized_row(row, time_limit) for row in rows]
    instance = as_instance(migrated[0])
    trajectory_rows: list[dict[str, Any]] = []
    rerun_count = 0

    for row in migrated:
        if row.get("status") == "OPTIMAL":
            continue
        partition = as_partition(row["partition"])
        should_trace = collect_trajectory and (
            row["method"] == "NP"
            or (row["method"] == "CHP" and int(row["threshold"]) == 4)
            or (
                row["method"] == "PP"
                and int(row["threshold"]) == 4
                and int(row["max_platoon_size"]) == 4
            )
        )
        schedule = solve_downstream_schedule(
            instance,
            partition,
            time_limit=time_limit,
            threads=threads,
            collect_trajectory=should_trace,
        )
        row.update(schedule_fields(schedule))
        row["end_to_end_time_s"] = float(row["end_to_end_time_s"]) + float(row["formation_time_ms"]) / 1000.0
        if should_trace:
            trajectory_rows.extend(trajectory_points(row, schedule))
        rerun_count += 1

    refresh_cross_method_fields(migrated)
    return migrated, trajectory_rows, rerun_count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--legacy-csv", default="../../results/rule_based_experiments/formal_pp_hS3/formal_comparison_rows.csv")
    parser.add_argument("--comparison-output-dir", default="../../results/rule_based_experiments/formal_pp_hS3_600s_r10")
    parser.add_argument("--n-values", default="20,40")
    parser.add_argument("--arrival-rates", default="1.5,2.5")
    parser.add_argument("--reps", type=int, default=10)
    parser.add_argument("--rep-start", type=int, default=0)
    parser.add_argument("--rep-end-exclusive", type=int)
    parser.add_argument("--time-limit", type=float, default=600.0)
    parser.add_argument("--threads", type=int, default=12)
    parser.add_argument("--write-trajectory", action="store_true")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    selected_n = set(parse_int_tuple(args.n_values))
    selected_rates = {float(value) for value in args.arrival_rates.split(",") if value.strip()}
    rep_end = args.reps if args.rep_end_exclusive is None else args.rep_end_exclusive
    if args.rep_start < 0 or rep_end < args.rep_start or rep_end > args.reps:
        raise ValueError("replication range must satisfy 0 <= rep_start <= rep_end <= reps")

    groups: dict[tuple[int, float, int], list[dict[str, Any]]] = defaultdict(list)
    for row in read_csv(Path(args.legacy_csv)):
        key = (int(row["N"]), float(row["arrival_rate"]), int(row["replication"]))
        if key[0] in selected_n and key[1] in selected_rates and args.rep_start <= key[2] < rep_end:
            groups[key].append(row)

    expected_keys = {
        (n_value, rate, replication)
        for n_value in selected_n
        for rate in selected_rates
        for replication in range(args.rep_start, rep_end)
    }
    missing = sorted(expected_keys - set(groups))
    if missing:
        raise RuntimeError(f"legacy CSV is missing {len(missing)} requested instances; first={missing[0]}")

    checkpoint_dir = Path(args.comparison_output_dir) / "checkpoints"
    total_reruns = 0
    migrated_instances = 0
    for key in sorted(groups):
        n_value, rate, replication = key
        instance_rows = groups[key]
        if len(instance_rows) != 21:
            raise RuntimeError(f"expected 21 method rows for {key}, found {len(instance_rows)}")
        instance_id = str(instance_rows[0]["instance_id"])
        checkpoint_path = checkpoint_dir / f"N{n_value}_lambda{str(rate).replace('.', 'p')}_rep{replication:03d}.json"
        if args.resume and checkpoint_path.exists():
            continue
        migrated_rows, trajectory_rows, rerun_count = migrate_instance(
            instance_rows,
            time_limit=args.time_limit,
            threads=args.threads,
            collect_trajectory=args.write_trajectory,
        )
        first = migrated_rows[0]
        payload = {
            "source": "approved_legacy_migration",
            "instance": {
                "instance_id": instance_id,
                "seed": int(first["seed"]),
                "replication": replication,
                "N": n_value,
                "lambda": rate,
                "arrival_rate": rate,
                "total_arrival_rate": rate,
                "per_approach_arrival_rate": float(first["per_approach_arrival_rate"]),
                "counts": first["counts"],
                "releases": first["releases"],
            },
            "rows": migrated_rows,
            "trajectory_rows": trajectory_rows,
        }
        write_checkpoint_atomic(checkpoint_path, payload)
        migrated_instances += 1
        total_reruns += rerun_count

    print(f"migrated_instances={migrated_instances} rerun_method_rows={total_reruns}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
