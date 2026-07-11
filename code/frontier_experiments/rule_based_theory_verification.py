"""Small exact checks for rule-based platooning bounds."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import asdict, dataclass
from fractions import Fraction
from itertools import product
from pathlib import Path
from statistics import median

VERIFY_DIR = Path(__file__).resolve().parents[1] / "exhaustive_verification"
if str(VERIFY_DIR) not in sys.path:
    sys.path.insert(0, str(VERIFY_DIR))

from enumerate_sequences import enumerate_fifo_sequences, enumerate_platoon_sequences  # noqa: E402
from metrics import (  # noqa: E402
    ordering_variables,
    rule_level_bound,
    scaled_rule_level_bound,
)
from model import (  # noqa: E402
    Instance,
    optimum_for_sequences,
    partition_label,
    scaled_indexed_bound,
)
from partition_methods import form_rule_based_platoons  # noqa: E402


@dataclass(frozen=True)
class TheoryConfig:
    counts: tuple[int, ...]
    hF: int
    hS_values: tuple[int, ...]
    max_release: int
    thresholds: tuple[int, ...]
    max_platoon_sizes: tuple[int, ...]
    formation_repetitions: int
    output_dir: str


def parse_int_tuple(value: str) -> tuple[int, ...]:
    return tuple(int(part.strip()) for part in value.split(",") if part.strip())


def nondecreasing_rows(count: int, max_release: int) -> tuple[tuple[int, ...], ...]:
    rows: list[tuple[int, ...]] = []

    def rec(prefix: list[int], start: int) -> None:
        if len(prefix) == count:
            rows.append(tuple(prefix))
            return
        for value in range(start, max_release + 1):
            prefix.append(value)
            rec(prefix, value)
            prefix.pop()

    rec([], 0)
    return tuple(rows)


def instances(config: TheoryConfig) -> tuple[Instance, ...]:
    per_approach = [nondecreasing_rows(count, config.max_release) for count in config.counts]
    result: list[Instance] = []
    for hS in config.hS_values:
        for releases in product(*per_approach):
            result.append(
                Instance(
                    counts=config.counts,
                    releases=tuple(releases),
                    hF=config.hF,
                    hS=hS,
                )
            )
    return tuple(result)


def fraction_label(value: Fraction) -> str:
    if value.denominator == 1:
        return str(value.numerator)
    return f"{value.numerator}/{value.denominator}"


def row_for_case(
    instance_id: int,
    instance: Instance,
    threshold: int,
    max_platoon_size: int,
    formation_repetitions: int,
) -> dict[str, object]:
    formation = form_rule_based_platoons(
        instance,
        "PP",
        threshold=threshold,
        max_platoon_size=max_platoon_size,
        timing_repetitions=formation_repetitions,
    )
    unrestricted = optimum_for_sequences(
        enumerate_fifo_sequences(instance.counts),
        instance.release_map,
        instance.hF,
        instance.hS,
        keep_all=False,
    )
    platoon = optimum_for_sequences(
        enumerate_platoon_sequences(formation.partition),
        instance.release_map,
        instance.hF,
        instance.hS,
        keep_all=False,
    )
    scaled_gap = platoon.total_delay - unrestricted.total_delay
    scaled_partition_bound = scaled_indexed_bound(instance, formation.partition)
    scaled_rule_bound = scaled_rule_level_bound(instance, threshold, max_platoon_size)
    valid_chain = (
        0 <= scaled_gap
        and scaled_gap <= scaled_partition_bound
        and scaled_partition_bound <= scaled_rule_bound
    )
    return {
        "instance_id": instance_id,
        "N": instance.N,
        "L": instance.L,
        "counts": list(instance.counts),
        "releases": [list(row) for row in instance.releases],
        "h_F": instance.hF,
        "h_S": instance.hS,
        "threshold": threshold,
        "max_platoon_size": max_platoon_size,
        "method": formation.method,
        "partition": partition_label(formation.partition),
        "number_of_platoons": sum(len(blocks) for blocks in formation.partition),
        "ordering_variable_count": ordering_variables(formation.partition),
        "formation_time_ms": formation.formation_time_ms,
        "formation_repetitions": formation_repetitions,
        "scaled_actual_optimality_gap": scaled_gap,
        "actual_optimality_gap": fraction_label(Fraction(scaled_gap, instance.N)),
        "scaled_partition_specific_upper_bound": scaled_partition_bound,
        "partition_specific_upper_bound": fraction_label(
            Fraction(scaled_partition_bound, instance.N)
        ),
        "scaled_rule_level_upper_bound": scaled_rule_bound,
        "rule_level_upper_bound": fraction_label(
            rule_level_bound(instance, threshold, max_platoon_size)
        ),
        "bound_chain_valid": valid_chain,
    }


def summarize(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    groups: dict[tuple[int, int], list[dict[str, object]]] = {}
    for row in rows:
        key = (int(row["threshold"]), int(row["max_platoon_size"]))
        groups.setdefault(key, []).append(row)
    summary: list[dict[str, object]] = []
    for (threshold, max_platoon_size), group in sorted(groups.items()):
        count = len(group)
        scaled_gaps = [int(row["scaled_actual_optimality_gap"]) for row in group]
        scaled_partition_bounds = [
            int(row["scaled_partition_specific_upper_bound"]) for row in group
        ]
        scaled_rule_bounds = [int(row["scaled_rule_level_upper_bound"]) for row in group]
        n_values = [int(row["N"]) for row in group]
        actual_gaps = [
            scaled_gap / n_value
            for scaled_gap, n_value in zip(scaled_gaps, n_values, strict=True)
        ]
        partition_bounds = [
            scaled_bound / n_value
            for scaled_bound, n_value in zip(scaled_partition_bounds, n_values, strict=True)
        ]
        rule_bounds = [
            scaled_bound / n_value
            for scaled_bound, n_value in zip(scaled_rule_bounds, n_values, strict=True)
        ]
        valid_cases = sum(1 for row in group if row["bound_chain_valid"])
        summary.append(
            {
                "threshold": threshold,
                "max_platoon_size": max_platoon_size,
                "cases": count,
                "valid_cases": valid_cases,
                "violation_rate": (count - valid_cases) / count,
                "actual_equals_partition_bound_cases": sum(
                    1
                    for gap, bound in zip(scaled_gaps, scaled_partition_bounds, strict=True)
                    if gap == bound
                ),
                "partition_equals_rule_bound_cases": sum(
                    1
                    for partition_bound, rule_bound in zip(
                        scaled_partition_bounds,
                        scaled_rule_bounds,
                        strict=True,
                    )
                    if partition_bound == rule_bound
                ),
                "full_chain_equality_cases": sum(
                    1
                    for gap, partition_bound, rule_bound in zip(
                        scaled_gaps,
                        scaled_partition_bounds,
                        scaled_rule_bounds,
                        strict=True,
                    )
                    if gap == partition_bound == rule_bound
                ),
                "mean_actual_gap": sum(actual_gaps) / count,
                "median_actual_gap": median(actual_gaps),
                "mean_partition_specific_upper_bound": sum(partition_bounds) / count,
                "median_partition_specific_upper_bound": median(partition_bounds),
                "mean_rule_level_upper_bound": sum(rule_bounds) / count,
                "median_rule_level_upper_bound": median(rule_bounds),
                "mean_scaled_actual_gap": sum(scaled_gaps) / count,
                "median_scaled_actual_gap": median(scaled_gaps),
                "mean_scaled_partition_bound": sum(scaled_partition_bounds) / count,
                "median_scaled_partition_bound": median(scaled_partition_bounds),
                "mean_scaled_rule_bound": sum(scaled_rule_bounds) / count,
                "median_scaled_rule_bound": median(scaled_rule_bounds),
                "mean_number_of_platoons": sum(int(row["number_of_platoons"]) for row in group) / count,
                "mean_ordering_variable_count": sum(int(row["ordering_variable_count"]) for row in group) / count,
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


def run(config: TheoryConfig) -> dict[str, object]:
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    for instance_id, instance in enumerate(instances(config)):
        for threshold in config.thresholds:
            for max_platoon_size in config.max_platoon_sizes:
                rows.append(
                    row_for_case(
                        instance_id,
                        instance,
                        threshold,
                        max_platoon_size,
                        config.formation_repetitions,
                    )
                )
    summary = summarize(rows)
    violations = [row for row in rows if not row["bound_chain_valid"]]
    payload = {
        "config": asdict(config),
        "case_count": len(rows),
        "violation_count": len(violations),
        "summary": summary,
        "first_violation": violations[0] if violations else None,
    }
    write_csv(output_dir / "rule_based_theory_rows.csv", rows)
    write_csv(output_dir / "rule_based_theory_summary.csv", summary)
    (output_dir / "rule_based_theory_summary.json").write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--counts", default="2,2")
    parser.add_argument("--hF", type=int, default=1)
    parser.add_argument("--hS-values", default="2,3")
    parser.add_argument("--max-release", type=int, default=3)
    parser.add_argument("--thresholds", default="0,1,2,3")
    parser.add_argument("--max-platoon-sizes", default="1,2,3,4")
    parser.add_argument("--formation-repetitions", type=int, default=20)
    parser.add_argument("--output-dir", default="../../results/rule_based_experiments/theory_smoke")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    config = TheoryConfig(
        counts=parse_int_tuple(args.counts),
        hF=args.hF,
        hS_values=parse_int_tuple(args.hS_values),
        max_release=args.max_release,
        thresholds=parse_int_tuple(args.thresholds),
        max_platoon_sizes=parse_int_tuple(args.max_platoon_sizes),
        formation_repetitions=args.formation_repetitions,
        output_dir=args.output_dir,
    )
    payload = run(config)
    print(json.dumps(payload, indent=2))
    return 1 if payload["violation_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
