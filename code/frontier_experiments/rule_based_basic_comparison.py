"""Small NP/CHP/PP downstream scheduling comparison."""

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

VERIFY_DIR = Path(__file__).resolve().parents[1] / "exhaustive_verification"
if str(VERIFY_DIR) not in sys.path:
    sys.path.insert(0, str(VERIFY_DIR))

from enumerate_sequences import enumerate_fifo_sequences  # noqa: E402
from metrics import (  # noqa: E402
    ordering_variables,
    rule_level_bound,
    scaled_rule_level_bound,
    vehicle_level_ordering_variables,
)
from model import Instance, optimum_for_sequences, partition_label, scaled_indexed_bound  # noqa: E402
from partition_methods import RuleMethod, form_rule_based_platoons  # noqa: E402
from scheduling_milp import solve_downstream_schedule  # noqa: E402


@dataclass(frozen=True)
class BasicComparisonConfig:
    seed: int
    reps: int
    n_values: tuple[int, ...]
    approaches: int
    arrival_rate: float
    hF: int
    hS: int
    threshold: int
    max_platoon_size: int
    time_limit: float
    threads: int
    max_exact_total: int
    output_dir: str


def parse_int_tuple(value: str) -> tuple[int, ...]:
    return tuple(int(part.strip()) for part in value.split(",") if part.strip())


def balanced_counts(total_vehicles: int, approaches: int) -> tuple[int, ...]:
    base = total_vehicles // approaches
    remainder = total_vehicles % approaches
    return tuple(base + (1 if index < remainder else 0) for index in range(approaches))


def replication_seed(config: BasicComparisonConfig, n_value: int, replication: int) -> int:
    material = json.dumps(
        {
            "seed": config.seed,
            "N": n_value,
            "replication": replication,
            "approaches": config.approaches,
            "arrival_rate": config.arrival_rate,
        },
        sort_keys=True,
    ).encode("utf-8")
    return int.from_bytes(hashlib.sha256(material).digest()[:8], "big")


def generate_releases(
    counts: tuple[int, ...],
    arrival_rate: float,
    rng: random.Random,
) -> tuple[tuple[int, ...], ...]:
    releases: list[tuple[int, ...]] = []
    for approach, count in enumerate(counts):
        current = rng.randint(0, 2)
        row: list[int] = []
        rate = arrival_rate * (1.0 + 0.1 * (approach % 3))
        for _ in range(count):
            current += rng.expovariate(rate)
            row.append(round(current))
        releases.append(tuple(row))
    return tuple(releases)


def instance_for_replication(
    config: BasicComparisonConfig,
    n_value: int,
    replication: int,
) -> tuple[Instance, int]:
    seed = replication_seed(config, n_value, replication)
    rng = random.Random(seed)
    counts = balanced_counts(n_value, config.approaches)
    return (
        Instance(
            counts=counts,
            releases=generate_releases(counts, config.arrival_rate, rng),
            hF=config.hF,
            hS=config.hS,
        ),
        seed,
    )


def exact_np_average_delay(instance: Instance, max_exact_total: int) -> Fraction | None:
    if instance.N > max_exact_total:
        return None
    optimum = optimum_for_sequences(
        enumerate_fifo_sequences(instance.counts),
        instance.release_map,
        instance.hF,
        instance.hS,
        keep_all=False,
    )
    return optimum.average_delay


def method_inputs(config: BasicComparisonConfig) -> tuple[tuple[RuleMethod, int | None, int | None], ...]:
    return (
        ("NP", None, None),
        ("CHP", config.threshold, None),
        ("PP", config.threshold, config.max_platoon_size),
    )


def row_for_method(
    config: BasicComparisonConfig,
    instance: Instance,
    seed: int,
    replication: int,
    method: RuleMethod,
    threshold: int | None,
    max_platoon_size: int | None,
    exact_np_average: Fraction | None,
    np_schedule_average: float | None,
) -> dict[str, object]:
    formation = form_rule_based_platoons(
        instance,
        method,
        threshold=threshold,
        max_platoon_size=max_platoon_size,
    )
    schedule = solve_downstream_schedule(
        instance,
        formation.partition,
        time_limit=config.time_limit,
        threads=config.threads,
    )
    reference_average: float | None = None
    reference_source = None
    if exact_np_average is not None:
        reference_average = float(exact_np_average)
        reference_source = "exact_enumeration"
    elif np_schedule_average is not None:
        reference_average = np_schedule_average
        reference_source = "np_gurobi_optimal"

    actual_gap = None
    if (
        reference_average is not None
        and schedule.status == "OPTIMAL"
        and schedule.objective_average_delay is not None
    ):
        actual_gap = schedule.objective_average_delay - reference_average

    partition_bound = Fraction(scaled_indexed_bound(instance, formation.partition), instance.N)
    if method == "NP":
        rule_bound = Fraction(0, 1)
        scaled_rule_bound = 0
    else:
        assert threshold is not None
        scaled_rule_bound = scaled_rule_level_bound(instance, threshold, max_platoon_size)
        rule_bound = rule_level_bound(instance, threshold, max_platoon_size)

    return {
        "seed": seed,
        "replication": replication,
        "N": instance.N,
        "L": instance.L,
        "counts": list(instance.counts),
        "releases": [list(row) for row in instance.releases],
        "arrival_rate": config.arrival_rate,
        "h_F": instance.hF,
        "h_S": instance.hS,
        "threshold": threshold,
        "max_platoon_size": formation.max_platoon_size,
        "method": method,
        "partition": partition_label(formation.partition),
        "number_of_platoons": sum(len(blocks) for blocks in formation.partition),
        "ordering_variable_count": ordering_variables(formation.partition),
        "vehicle_level_ordering_variable_count": vehicle_level_ordering_variables(instance.counts),
        "formation_time_ms": formation.formation_time_ms,
        "model_build_time_s": schedule.model_construction_seconds,
        "solve_time_s": schedule.runtime_seconds,
        "end_to_end_time_s": formation.formation_time_ms / 1000.0 + schedule.end_to_end_seconds,
        "status": schedule.status,
        "objective": schedule.objective_average_delay,
        "actual_optimality_gap": actual_gap,
        "actual_gap_reference": reference_source,
        "terminal_mip_gap": schedule.mip_gap,
        "node_count": schedule.node_count,
        "partition_specific_upper_bound": float(partition_bound),
        "scaled_partition_specific_upper_bound": scaled_indexed_bound(instance, formation.partition),
        "rule_level_upper_bound": float(rule_bound),
        "scaled_rule_level_upper_bound": scaled_rule_bound,
    }


def run_replication(
    config: BasicComparisonConfig,
    n_value: int,
    replication: int,
) -> list[dict[str, object]]:
    instance, seed = instance_for_replication(config, n_value, replication)
    exact_average = exact_np_average_delay(instance, config.max_exact_total)
    np_formation = form_rule_based_platoons(instance, "NP")
    np_schedule = solve_downstream_schedule(
        instance,
        np_formation.partition,
        time_limit=config.time_limit,
        threads=config.threads,
    )
    np_schedule_average = (
        np_schedule.objective_average_delay
        if np_schedule.status == "OPTIMAL"
        else None
    )
    rows: list[dict[str, object]] = []
    for method, threshold, max_platoon_size in method_inputs(config):
        if method == "NP":
            schedule_average_reference = np_schedule_average
        else:
            schedule_average_reference = np_schedule_average
        rows.append(
            row_for_method(
                config,
                instance,
                seed,
                replication,
                method,
                threshold,
                max_platoon_size,
                exact_average,
                schedule_average_reference,
            )
        )
    return rows


def summarize(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    groups: dict[tuple[int, str], list[dict[str, object]]] = {}
    for row in rows:
        groups.setdefault((int(row["N"]), str(row["method"])), []).append(row)
    summary: list[dict[str, object]] = []
    for (n_value, method), group in sorted(groups.items()):
        def values(field: str) -> list[float]:
            return [float(row[field]) for row in group if row.get(field) not in (None, "")]

        count = len(group)
        summary.append(
            {
                "N": n_value,
                "method": method,
                "cases": count,
                "optimality_rate": sum(1 for row in group if row["status"] == "OPTIMAL") / count,
                "mean_average_delay": sum(values("objective")) / len(values("objective")) if values("objective") else None,
                "mean_actual_optimality_gap": sum(values("actual_optimality_gap")) / len(values("actual_optimality_gap")) if values("actual_optimality_gap") else None,
                "actual_gap_case_count": len(values("actual_optimality_gap")),
                "mean_number_of_platoons": sum(values("number_of_platoons")) / count,
                "mean_ordering_variable_count": sum(values("ordering_variable_count")) / count,
                "mean_formation_time_ms": sum(values("formation_time_ms")) / count,
                "mean_solve_time_s": sum(values("solve_time_s")) / count,
                "mean_terminal_mip_gap": sum(values("terminal_mip_gap")) / len(values("terminal_mip_gap")) if values("terminal_mip_gap") else None,
                "mean_node_count": sum(values("node_count")) / count,
            }
        )
    return summary


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
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


def run(config: BasicComparisonConfig) -> dict[str, object]:
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    for n_value in config.n_values:
        for replication in range(config.reps):
            rows.extend(run_replication(config, n_value, replication))
    summary = summarize(rows)
    payload = {
        "config": asdict(config),
        "row_count": len(rows),
        "summary": summary,
    }
    write_csv(output_dir / "rule_based_basic_rows.csv", rows)
    write_csv(output_dir / "rule_based_basic_summary.csv", summary)
    (output_dir / "rule_based_basic_summary.json").write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=20260711)
    parser.add_argument("--reps", type=int, default=2)
    parser.add_argument("--n-values", default="8,12")
    parser.add_argument("--approaches", type=int, default=4)
    parser.add_argument("--arrival-rate", type=float, default=0.7)
    parser.add_argument("--hF", type=int, default=1)
    parser.add_argument("--hS", type=int, default=2)
    parser.add_argument("--threshold", type=int, default=2)
    parser.add_argument("--max-platoon-size", type=int, default=3)
    parser.add_argument("--time-limit", type=float, default=10.0)
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("--max-exact-total", type=int, default=10)
    parser.add_argument("--output-dir", default="../../results/rule_based_experiments/basic_smoke")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    config = BasicComparisonConfig(
        seed=args.seed,
        reps=args.reps,
        n_values=parse_int_tuple(args.n_values),
        approaches=args.approaches,
        arrival_rate=args.arrival_rate,
        hF=args.hF,
        hS=args.hS,
        threshold=args.threshold,
        max_platoon_size=args.max_platoon_size,
        time_limit=args.time_limit,
        threads=args.threads,
        max_exact_total=args.max_exact_total,
        output_dir=args.output_dir,
    )
    payload = run(config)
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
