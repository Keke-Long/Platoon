"""Formal NP/CHP/PP comparison over controlled random instances."""

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

from enumerate_sequences import enumerate_fifo_sequences  # noqa: E402
from metrics import ordering_variables, rule_level_bound, scaled_rule_level_bound, vehicle_level_ordering_variables  # noqa: E402
from model import Instance, optimum_for_sequences, partition_label, scaled_indexed_bound  # noqa: E402
from partition_methods import RuleMethod, form_rule_based_platoons  # noqa: E402
from scheduling_milp import solve_downstream_schedule  # noqa: E402


@dataclass(frozen=True)
class FormalComparisonConfig:
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


def instance_seed(config: FormalComparisonConfig, n_value: int, arrival_rate: float, replication: int) -> int:
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


def generate_releases(counts: tuple[int, ...], arrival_rate: float, rng: random.Random) -> tuple[tuple[int, ...], ...]:
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


def build_instance(config: FormalComparisonConfig, n_value: int, arrival_rate: float, replication: int) -> tuple[Instance, int]:
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


def exact_np_average(instance: Instance, max_exact_total: int) -> float | None:
    if instance.N > max_exact_total:
        return None
    optimum = optimum_for_sequences(
        enumerate_fifo_sequences(instance.counts),
        instance.release_map,
        instance.hF,
        instance.hS,
        keep_all=False,
    )
    return float(optimum.average_delay)


def numeric_values(rows: list[dict[str, object]], field: str) -> list[float]:
    return [float(row[field]) for row in rows if row.get(field) not in (None, "")]


def mean_or_none(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def median_or_none(values: list[float]) -> float | None:
    return float(median(values)) if values else None


def run_instance(
    config: FormalComparisonConfig,
    instance: Instance,
    seed: int,
    arrival_rate: float,
    replication: int,
) -> list[dict[str, object]]:
    exact_reference = exact_np_average(instance, config.max_exact_total)
    rows: list[dict[str, object]] = []
    np_average_for_gap: float | None = exact_reference
    np_reference_source = "exact_enumeration" if exact_reference is not None else None

    def solve_row(
        method: RuleMethod,
        threshold: int | None,
        max_platoon_size: int | None,
    ) -> dict[str, object]:
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
            time_limit=config.time_limit,
            threads=config.threads,
        )
        actual_gap = None
        if (
            np_average_for_gap is not None
            and schedule.status == "OPTIMAL"
            and schedule.objective_average_delay is not None
        ):
            actual_gap = schedule.objective_average_delay - np_average_for_gap
        partition_bound = Fraction(scaled_indexed_bound(instance, formation.partition), instance.N)
        if method == "NP":
            scaled_rule_bound = 0
            rule_bound = Fraction(0, 1)
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
            "arrival_rate": arrival_rate,
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
            "formation_repetitions": config.formation_repetitions,
            "model_build_time_s": schedule.model_construction_seconds,
            "solve_time_s": schedule.runtime_seconds,
            "end_to_end_time_s": formation.formation_time_ms / 1000.0 + schedule.end_to_end_seconds,
            "status": schedule.status,
            "objective": schedule.objective_average_delay,
            "actual_optimality_gap": actual_gap,
            "actual_gap_reference": np_reference_source,
            "terminal_mip_gap": schedule.mip_gap,
            "node_count": schedule.node_count,
            "partition_specific_upper_bound": float(partition_bound),
            "scaled_partition_specific_upper_bound": scaled_indexed_bound(instance, formation.partition),
            "rule_level_upper_bound": float(rule_bound),
            "scaled_rule_level_upper_bound": scaled_rule_bound,
        }

    np_row = solve_row("NP", None, None)
    rows.append(np_row)
    if np_average_for_gap is None and np_row["status"] == "OPTIMAL":
        np_average_for_gap = np_row["objective"]  # type: ignore[assignment]
        np_reference_source = "np_gurobi_optimal"
        np_row["actual_gap_reference"] = np_reference_source
        np_row["actual_optimality_gap"] = 0.0

    for threshold in config.thresholds:
        chp_row = solve_row("CHP", threshold, None)
        rows.append(chp_row)
        chp_objective = (
            float(chp_row["objective"])
            if chp_row["status"] == "OPTIMAL" and chp_row.get("objective") is not None
            else None
        )
        for max_platoon_size in config.max_platoon_sizes:
            pp_row = solve_row("PP", threshold, max_platoon_size)
            pp_objective = (
                float(pp_row["objective"])
                if pp_row["status"] == "OPTIMAL" and pp_row.get("objective") is not None
                else None
            )
            relation_holds = None
            if np_average_for_gap is not None and pp_objective is not None and chp_objective is not None:
                relation_holds = (
                    np_average_for_gap <= pp_objective + 1e-7 <= chp_objective + 1e-7
                )
            pp_row["np_pp_chp_delay_order_holds"] = relation_holds
            pp_row["matching_chp_objective"] = chp_objective
            rows.append(pp_row)
        chp_row["np_pp_chp_delay_order_holds"] = None
    np_row["np_pp_chp_delay_order_holds"] = None
    return rows


def summarize(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    groups: dict[tuple[int, float, str, str, str], list[dict[str, object]]] = {}
    for row in rows:
        threshold = str(row.get("threshold") if row.get("threshold") not in (None, "") else "NA")
        pmax = str(row.get("max_platoon_size") if row.get("max_platoon_size") not in (None, "") else "NA")
        groups.setdefault((int(row["N"]), float(row["arrival_rate"]), str(row["method"]), threshold, pmax), []).append(row)
    summary: list[dict[str, object]] = []
    for (n_value, arrival_rate, method, threshold, pmax), group in sorted(groups.items()):
        actual_gap_count = len(numeric_values(group, "actual_optimality_gap"))
        summary.append(
            {
                "N": n_value,
                "arrival_rate": arrival_rate,
                "method": method,
                "threshold": threshold,
                "max_platoon_size": pmax,
                "cases": len(group),
                "case_count": len(group),
                "optimality_rate": sum(1 for row in group if row["status"] == "OPTIMAL") / len(group),
                "mean_average_delay": mean_or_none(numeric_values(group, "objective")),
                "median_average_delay": median_or_none(numeric_values(group, "objective")),
                "mean_actual_optimality_gap": mean_or_none(numeric_values(group, "actual_optimality_gap")),
                "median_actual_optimality_gap": median_or_none(numeric_values(group, "actual_optimality_gap")),
                "actual_gap_case_count": actual_gap_count,
                "actual_gap_availability_rate": actual_gap_count / len(group),
                "mean_number_of_platoons": mean_or_none(numeric_values(group, "number_of_platoons")),
                "mean_ordering_variable_count": mean_or_none(numeric_values(group, "ordering_variable_count")),
                "mean_formation_time_ms": mean_or_none(numeric_values(group, "formation_time_ms")),
                "median_formation_time_ms": median_or_none(numeric_values(group, "formation_time_ms")),
                "mean_solve_time_s": mean_or_none(numeric_values(group, "solve_time_s")),
                "mean_end_to_end_time_s": mean_or_none(numeric_values(group, "end_to_end_time_s")),
                "mean_terminal_mip_gap": mean_or_none(numeric_values(group, "terminal_mip_gap")),
                "mean_node_count": mean_or_none(numeric_values(group, "node_count")),
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


def run(config: FormalComparisonConfig) -> dict[str, object]:
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    for n_value in config.n_values:
        for arrival_rate in config.arrival_rates:
            for replication in range(config.reps):
                instance, seed = build_instance(config, n_value, arrival_rate, replication)
                rows.extend(run_instance(config, instance, seed, arrival_rate, replication))
    summary = summarize(rows)
    relation_rows = [row for row in rows if row.get("method") == "PP" and row.get("np_pp_chp_delay_order_holds") is not None]
    relation_failures = [row for row in relation_rows if row.get("np_pp_chp_delay_order_holds") is not True]
    relation_instances = {
        (row["N"], row["arrival_rate"], row["replication"], row["seed"])
        for row in relation_rows
    }
    payload = {
        "config": asdict(config),
        "row_count": len(rows),
        "delay_order_checked_rows": len(relation_rows),
        "delay_order_checked_instances": len(relation_instances),
        "delay_order_failure_count": len(relation_failures),
        "summary": summary,
    }
    write_csv(output_dir / "formal_comparison_rows.csv", rows)
    write_csv(output_dir / "formal_comparison_summary.csv", summary)
    (output_dir / "formal_comparison_summary.json").write_text(
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
    parser.add_argument("--thresholds", default="3")
    parser.add_argument("--max-platoon-sizes", default="3")
    parser.add_argument("--hF", type=int, default=1)
    parser.add_argument("--hS", type=int, default=2)
    parser.add_argument("--time-limit", type=float, default=10.0)
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("--max-exact-total", type=int, default=10)
    parser.add_argument("--formation-repetitions", type=int, default=20)
    parser.add_argument("--output-dir", default="../../results/rule_based_experiments/formal_comparison")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    config = FormalComparisonConfig(
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
    return 1 if payload["delay_order_failure_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
