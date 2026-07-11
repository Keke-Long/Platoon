"""Random-instance theory trends for rule-based platooning."""

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

VERIFY_DIR = Path(__file__).resolve().parents[1] / "exhaustive_verification"
if str(VERIFY_DIR) not in sys.path:
    sys.path.insert(0, str(VERIFY_DIR))

from enumerate_sequences import enumerate_fifo_sequences, enumerate_platoon_sequences  # noqa: E402
from metrics import ordering_variables, rule_level_bound, scaled_rule_level_bound  # noqa: E402
from model import Instance, optimum_for_sequences, partition_label, scaled_indexed_bound  # noqa: E402
from partition_methods import form_rule_based_platoons  # noqa: E402
from scheduling_milp import solve_downstream_schedule  # noqa: E402


@dataclass(frozen=True)
class FormalTheoryConfig:
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
    threads: int
    max_exact_total: int
    formation_repetitions: int
    output_dir: str


def parse_int_tuple(value: str) -> tuple[int, ...]:
    return tuple(int(part.strip()) for part in value.split(",") if part.strip())


def parse_float_tuple(value: str) -> tuple[float, ...]:
    return tuple(float(part.strip()) for part in value.split(",") if part.strip())


def balanced_counts(total_vehicles: int, approaches: int) -> tuple[int, ...]:
    base = total_vehicles // approaches
    remainder = total_vehicles % approaches
    return tuple(base + (1 if index < remainder else 0) for index in range(approaches))


def instance_seed(config: FormalTheoryConfig, n_value: int, arrival_rate: float, replication: int) -> int:
    material = json.dumps(
        {
            "base_seed": config.seed,
            "N": n_value,
            "arrival_rate": arrival_rate,
            "replication": replication,
            "approaches": config.approaches,
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


def build_instance(
    config: FormalTheoryConfig,
    n_value: int,
    arrival_rate: float,
    replication: int,
) -> tuple[Instance, int]:
    seed = instance_seed(config, n_value, arrival_rate, replication)
    rng = random.Random(seed)
    counts = balanced_counts(n_value, config.approaches)
    return (
        Instance(
            counts=counts,
            releases=generate_releases(counts, arrival_rate, rng),
            hF=config.hF,
            hS=config.hS,
        ),
        seed,
    )


def exact_optimum_average(instance: Instance, partition=None) -> Fraction | None:
    if partition is None:
        sequences = enumerate_fifo_sequences(instance.counts)
    else:
        sequences = enumerate_platoon_sequences(partition)
    optimum = optimum_for_sequences(
        sequences,
        instance.release_map,
        instance.hF,
        instance.hS,
        keep_all=False,
    )
    return optimum.average_delay


def reference_average(instance: Instance, config: FormalTheoryConfig) -> tuple[float | None, str | None, dict[str, object]]:
    if instance.N <= config.max_exact_total:
        average = exact_optimum_average(instance)
        assert average is not None
        return float(average), "exact_enumeration", {
            "np_status": "EXACT",
            "np_solve_time_s": None,
            "np_terminal_mip_gap": None,
            "np_node_count": None,
        }
    np_formation = form_rule_based_platoons(
        instance,
        "NP",
        timing_repetitions=config.formation_repetitions,
    )
    schedule = solve_downstream_schedule(
        instance,
        np_formation.partition,
        time_limit=config.time_limit,
        threads=config.threads,
    )
    average = (
        schedule.objective_average_delay
        if schedule.status == "OPTIMAL"
        else None
    )
    return average, "np_gurobi_optimal" if average is not None else None, {
        "np_status": schedule.status,
        "np_solve_time_s": schedule.runtime_seconds,
        "np_terminal_mip_gap": schedule.mip_gap,
        "np_node_count": schedule.node_count,
    }


def run_case(
    config: FormalTheoryConfig,
    instance: Instance,
    seed: int,
    replication: int,
    arrival_rate: float,
    threshold: int,
    max_platoon_size: int,
    np_average: float | None,
    reference_source: str | None,
    np_metrics: dict[str, object],
) -> dict[str, object]:
    formation = form_rule_based_platoons(
        instance,
        "PP",
        threshold=threshold,
        max_platoon_size=max_platoon_size,
        timing_repetitions=config.formation_repetitions,
    )
    exact_pp_average: Fraction | None = None
    schedule_status = "NOT_RUN_EXACT_PP"
    objective = None
    solve_time_s = None
    terminal_mip_gap = None
    node_count = None
    if instance.N <= config.max_exact_total:
        exact_pp_average = exact_optimum_average(instance, formation.partition)
        assert exact_pp_average is not None
        objective = float(exact_pp_average)
        schedule_status = "EXACT"
    else:
        schedule = solve_downstream_schedule(
            instance,
            formation.partition,
            time_limit=config.time_limit,
            threads=config.threads,
        )
        objective = schedule.objective_average_delay
        schedule_status = schedule.status
        solve_time_s = schedule.runtime_seconds
        terminal_mip_gap = schedule.mip_gap
        node_count = schedule.node_count

    actual_gap = None
    scaled_actual_gap = None
    if np_average is not None and schedule_status in ("OPTIMAL", "EXACT") and objective is not None:
        actual_gap = objective - np_average
        scaled_actual_gap = round(actual_gap * instance.N)

    scaled_partition_bound = scaled_indexed_bound(instance, formation.partition)
    scaled_rule_bound = scaled_rule_level_bound(instance, threshold, max_platoon_size)
    partition_bound = float(Fraction(scaled_partition_bound, instance.N))
    rule_bound = float(rule_level_bound(instance, threshold, max_platoon_size))
    bound_chain_valid = None
    if scaled_actual_gap is not None:
        bound_chain_valid = (
            0 <= scaled_actual_gap
            and scaled_actual_gap <= scaled_partition_bound
            and scaled_partition_bound <= scaled_rule_bound
        )
    row = {
        "seed": seed,
        "replication": replication,
        "N": instance.N,
        "L": instance.L,
        "counts": list(instance.counts),
        "releases": [list(row) for row in instance.releases],
        "arrival_rate": arrival_rate,
        "h_F": instance.hF,
        "h_S": instance.hS,
        "threshold": threshold,
        "max_platoon_size": max_platoon_size,
        "method": "PP",
        "partition": partition_label(formation.partition),
        "number_of_platoons": sum(len(blocks) for blocks in formation.partition),
        "ordering_variable_count": ordering_variables(formation.partition),
        "formation_time_ms": formation.formation_time_ms,
        "formation_repetitions": config.formation_repetitions,
        "status": schedule_status,
        "objective": objective,
        "actual_optimality_gap": actual_gap,
        "scaled_actual_optimality_gap": scaled_actual_gap,
        "actual_gap_reference": reference_source,
        "solve_time_s": solve_time_s,
        "terminal_mip_gap": terminal_mip_gap,
        "node_count": node_count,
        "partition_specific_upper_bound": partition_bound,
        "scaled_partition_specific_upper_bound": scaled_partition_bound,
        "rule_level_upper_bound": rule_bound,
        "scaled_rule_level_upper_bound": scaled_rule_bound,
        "bound_chain_valid": bound_chain_valid,
    }
    row.update(np_metrics)
    return row


def numeric_values(rows: list[dict[str, object]], field: str) -> list[float]:
    return [float(row[field]) for row in rows if row.get(field) not in (None, "")]


def mean_or_none(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def median_or_none(values: list[float]) -> float | None:
    return float(median(values)) if values else None


def summarize(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    groups: dict[tuple[int, float, int, int], list[dict[str, object]]] = {}
    for row in rows:
        key = (
            int(row["N"]),
            float(row["arrival_rate"]),
            int(row["threshold"]),
            int(row["max_platoon_size"]),
        )
        groups.setdefault(key, []).append(row)
    summary: list[dict[str, object]] = []
    for (n_value, arrival_rate, threshold, max_platoon_size), group in sorted(groups.items()):
        known_gap_rows = [row for row in group if row.get("actual_optimality_gap") not in (None, "")]
        valid_rows = [row for row in known_gap_rows if row.get("bound_chain_valid") is True]
        actual = numeric_values(group, "actual_optimality_gap")
        partition = numeric_values(group, "partition_specific_upper_bound")
        rule = numeric_values(group, "rule_level_upper_bound")
        summary.append(
            {
                "N": n_value,
                "arrival_rate": arrival_rate,
                "threshold": threshold,
                "max_platoon_size": max_platoon_size,
                "cases": len(group),
                "actual_gap_case_count": len(known_gap_rows),
                "violation_count": len(known_gap_rows) - len(valid_rows),
                "violation_rate": (
                    (len(known_gap_rows) - len(valid_rows)) / len(known_gap_rows)
                    if known_gap_rows
                    else None
                ),
                "actual_equals_partition_bound_cases": sum(
                    1
                    for row in known_gap_rows
                    if row["scaled_actual_optimality_gap"]
                    == row["scaled_partition_specific_upper_bound"]
                ),
                "partition_equals_rule_bound_cases": sum(
                    1
                    for row in group
                    if row["scaled_partition_specific_upper_bound"]
                    == row["scaled_rule_level_upper_bound"]
                ),
                "mean_actual_gap": mean_or_none(actual),
                "median_actual_gap": median_or_none(actual),
                "mean_partition_specific_upper_bound": mean_or_none(partition),
                "median_partition_specific_upper_bound": median_or_none(partition),
                "mean_rule_level_upper_bound": mean_or_none(rule),
                "median_rule_level_upper_bound": median_or_none(rule),
                "mean_number_of_platoons": mean_or_none(numeric_values(group, "number_of_platoons")),
                "mean_ordering_variable_count": mean_or_none(numeric_values(group, "ordering_variable_count")),
                "optimality_rate": sum(1 for row in group if row["status"] in ("OPTIMAL", "EXACT")) / len(group),
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


def run(config: FormalTheoryConfig) -> dict[str, object]:
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    for n_value in config.n_values:
        for arrival_rate in config.arrival_rates:
            for replication in range(config.reps):
                instance, seed = build_instance(config, n_value, arrival_rate, replication)
                np_average, reference_source, np_metrics = reference_average(instance, config)
                for threshold in config.thresholds:
                    for max_platoon_size in config.max_platoon_sizes:
                        rows.append(
                            run_case(
                                config,
                                instance,
                                seed,
                                replication,
                                arrival_rate,
                                threshold,
                                max_platoon_size,
                                np_average,
                                reference_source,
                                np_metrics,
                            )
                        )
    summary = summarize(rows)
    known = [row for row in rows if row.get("bound_chain_valid") is not None]
    violations = [row for row in known if row.get("bound_chain_valid") is not True]
    payload = {
        "config": asdict(config),
        "row_count": len(rows),
        "known_gap_row_count": len(known),
        "violation_count": len(violations),
        "summary": summary,
    }
    write_csv(output_dir / "formal_theory_rows.csv", rows)
    write_csv(output_dir / "formal_theory_summary.csv", summary)
    (output_dir / "formal_theory_summary.json").write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=20260711)
    parser.add_argument("--reps", type=int, default=20)
    parser.add_argument("--n-values", default="8,12,16,20")
    parser.add_argument("--approaches", type=int, default=4)
    parser.add_argument("--arrival-rates", default="0.4,0.7,1.0")
    parser.add_argument("--thresholds", default="1,2,3,4")
    parser.add_argument("--max-platoon-sizes", default="2,3,4,5")
    parser.add_argument("--hF", type=int, default=1)
    parser.add_argument("--hS", type=int, default=2)
    parser.add_argument("--time-limit", type=float, default=10.0)
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("--max-exact-total", type=int, default=10)
    parser.add_argument("--formation-repetitions", type=int, default=20)
    parser.add_argument("--output-dir", default="../../results/rule_based_experiments/formal_theory")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    config = FormalTheoryConfig(
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
        threads=args.threads,
        max_exact_total=args.max_exact_total,
        formation_repetitions=args.formation_repetitions,
        output_dir=args.output_dir,
    )
    payload = run(config)
    print(json.dumps(payload, indent=2))
    return 1 if payload["violation_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
