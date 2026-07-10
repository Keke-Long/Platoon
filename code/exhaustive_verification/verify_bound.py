"""Staged exact verification of the candidate platoon bound."""

from __future__ import annotations

import argparse
import csv
import json
import platform
import time
from dataclasses import asdict, dataclass, field
from itertools import combinations_with_replacement, product
from pathlib import Path
from typing import Iterator

from enumerate_partitions import enumerate_partitions
from enumerate_sequences import enumerate_fifo_sequences, enumerate_platoon_sequences
from local_repair import (
    LocalRepairViolation,
    check_local_repair_sequence,
    local_repairs_for_sequence,
)
from model import (
    Instance,
    Partition,
    SequenceT,
    Optimum,
    optimum_for_sequences,
    partition_label,
    scaled_candidate_bound,
    sequence_label,
    total_delay,
)


@dataclass
class SearchConfig:
    L_values: tuple[int, ...]
    max_n: int
    max_total_vehicles: int
    max_release: int
    hF: int
    hS_values: tuple[int, ...]
    keep_all_optima: bool
    stop_on_counterexample: bool
    check_local: bool


@dataclass
class SearchStats:
    traffic_instances: int = 0
    partitions: int = 0
    vehicle_sequence_evaluations: int = 0
    platoon_sequence_evaluations: int = 0
    local_repairs_checked: int = 0
    local_repair_violations: int = 0
    zero_bound_cases: int = 0
    positive_bound_cases: int = 0
    violations: int = 0
    max_gap_over_bound_num: int = 0
    max_gap_over_bound_den: int = 1
    min_bound_excess_scaled: int | None = None
    max_bound_excess_scaled: int | None = None
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None

    @property
    def runtime_seconds(self) -> float:
        end = self.end_time if self.end_time is not None else time.time()
        return end - self.start_time

    def record_case(self, scaled_gap: int, scaled_bound: int) -> None:
        excess = scaled_bound - scaled_gap
        if self.min_bound_excess_scaled is None or excess < self.min_bound_excess_scaled:
            self.min_bound_excess_scaled = excess
        if self.max_bound_excess_scaled is None or excess > self.max_bound_excess_scaled:
            self.max_bound_excess_scaled = excess
        if scaled_bound == 0:
            self.zero_bound_cases += 1
            return
        self.positive_bound_cases += 1
        if scaled_gap * self.max_gap_over_bound_den > self.max_gap_over_bound_num * scaled_bound:
            self.max_gap_over_bound_num = scaled_gap
            self.max_gap_over_bound_den = scaled_bound

    def to_json(self, config: SearchConfig) -> dict[str, object]:
        data = asdict(self)
        data["runtime_seconds"] = self.runtime_seconds
        data["max_gap_over_bound"] = (
            f"{self.max_gap_over_bound_num}/{self.max_gap_over_bound_den}"
            if self.positive_bound_cases
            else None
        )
        data["config"] = asdict(config)
        data["platform"] = {
            "python": platform.python_version(),
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "processor": platform.processor(),
        }
        return data


@dataclass(frozen=True)
class BoundCounterexample:
    instance: Instance
    partition: Partition
    unrestricted: Optimum
    platoon: Optimum
    scaled_gap: int
    scaled_bound: int

    def to_json(self) -> dict[str, object]:
        return {
            "type": "global_bound_violation",
            "L": self.instance.L,
            "N": self.instance.N,
            "counts": list(self.instance.counts),
            "hF": self.instance.hF,
            "hS": self.instance.hS,
            "releases": [list(row) for row in self.instance.releases],
            "partition": partition_label(self.partition),
            "unrestricted_total_delay": self.unrestricted.total_delay,
            "platoon_total_delay": self.platoon.total_delay,
            "scaled_gap": self.scaled_gap,
            "scaled_bound": self.scaled_bound,
            "average_gap": f"{self.scaled_gap}/{self.instance.N}",
            "candidate_bound": f"{self.scaled_bound}/{self.instance.N}",
            "unrestricted_optimal_sequences": [
                sequence_label(sequence) for sequence in self.unrestricted.sequences
            ],
            "platoon_optimal_sequences": [
                sequence_label(sequence) for sequence in self.platoon.sequences
            ],
        }


def parse_int_list(value: str) -> tuple[int, ...]:
    return tuple(int(part.strip()) for part in value.split(",") if part.strip())


def count_vectors(config: SearchConfig) -> Iterator[tuple[int, ...]]:
    for L in config.L_values:
        for counts in product(range(1, config.max_n + 1), repeat=L):
            total = sum(counts)
            if total < 2 or total > config.max_total_vehicles:
                continue
            yield tuple(counts)


def release_vectors(count: int, max_release: int) -> tuple[tuple[int, ...], ...]:
    return tuple(combinations_with_replacement(range(max_release + 1), count))


def instances(config: SearchConfig) -> Iterator[Instance]:
    for counts in count_vectors(config):
        releases_by_approach = [release_vectors(count, config.max_release) for count in counts]
        for releases in product(*releases_by_approach):
            for hS in config.hS_values:
                yield Instance(counts=counts, releases=tuple(releases), hF=config.hF, hS=hS)


def optimum_from_cached_delays(
    sequences: Iterator[SequenceT],
    delay_cache: dict[SequenceT, int],
    keep_all: bool,
) -> tuple[Optimum, int]:
    best_delay: int | None = None
    best_sequences: list[SequenceT] = []
    evaluated = 0
    for sequence in sequences:
        evaluated += 1
        delay = delay_cache[sequence]
        if best_delay is None or delay < best_delay:
            best_delay = delay
            best_sequences = [sequence]
        elif keep_all and delay == best_delay:
            best_sequences.append(sequence)
    if best_delay is None:
        raise ValueError("partition produced no feasible sequences")
    return Optimum(best_delay, tuple(best_sequences)), evaluated


def render_counterexample_markdown(counterexample: BoundCounterexample) -> str:
    data = counterexample.to_json()
    return "\n".join(
        [
            "# Candidate Bound Counterexample",
            "",
            f"- Type: {data['type']}",
            f"- L: {data['L']}",
            f"- N: {data['N']}",
            f"- Counts: {data['counts']}",
            f"- hF: {data['hF']}",
            f"- hS: {data['hS']}",
            f"- Releases: {data['releases']}",
            f"- Partition: {data['partition']}",
            f"- Unrestricted total delay: {data['unrestricted_total_delay']}",
            f"- Platoon total delay: {data['platoon_total_delay']}",
            f"- Average gap: {data['average_gap']}",
            f"- Candidate bound: {data['candidate_bound']}",
            "",
            "## Unrestricted Optimal Sequences",
            "",
            json.dumps(data["unrestricted_optimal_sequences"], indent=2),
            "",
            "## Platoon Optimal Sequences",
            "",
            json.dumps(data["platoon_optimal_sequences"], indent=2),
            "",
            "## Proof Step",
            "",
            "The partition-specific global bound is contradicted by this instance. "
            "Run the local-repair checker on this same instance to distinguish whether "
            "the failure originates in the local inequality or in the global telescoping/repair-order argument.",
            "",
        ]
    )


def write_summary_files(
    output_dir: Path,
    config: SearchConfig,
    stats: SearchStats,
    counterexample: BoundCounterexample | None,
    local_violation: LocalRepairViolation | None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    stats.end_time = time.time()
    summary = stats.to_json(config)
    summary["counterexample_found"] = counterexample is not None
    summary["local_repair_violation_found"] = local_violation is not None
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    with (output_dir / "summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["metric", "value"])
        for key, value in summary.items():
            if isinstance(value, (dict, list)):
                value = json.dumps(value, sort_keys=True)
            writer.writerow([key, value])
    if counterexample is not None:
        (output_dir / "counterexample.json").write_text(
            json.dumps(counterexample.to_json(), indent=2),
            encoding="utf-8",
        )
        (output_dir / "counterexample.md").write_text(
            render_counterexample_markdown(counterexample),
            encoding="utf-8",
        )
    if local_violation is not None:
        (output_dir / "local_repair_violation.json").write_text(
            json.dumps(local_violation.to_json(), indent=2),
            encoding="utf-8",
        )


def search(config: SearchConfig, output_dir: Path) -> tuple[SearchStats, BoundCounterexample | None, LocalRepairViolation | None]:
    stats = SearchStats()
    first_counterexample: BoundCounterexample | None = None
    first_local_violation: LocalRepairViolation | None = None

    for instance in instances(config):
        stats.traffic_instances += 1
        releases = instance.release_map
        vehicle_sequences = tuple(enumerate_fifo_sequences(instance.counts))
        delay_cache = {
            sequence: total_delay(sequence, releases, instance.hF, instance.hS)
            for sequence in vehicle_sequences
        }
        stats.vehicle_sequence_evaluations += len(vehicle_sequences)
        unrestricted = optimum_for_sequences(
            vehicle_sequences,
            releases,
            instance.hF,
            instance.hS,
            keep_all=config.keep_all_optima,
        )

        if config.check_local and first_local_violation is None:
            for sequence in vehicle_sequences:
                stats.local_repairs_checked += sum(
                    1 for _ in local_repairs_for_sequence(sequence)
                )
                repairs = list(check_local_repair_sequence(instance, sequence))
                if repairs:
                    stats.local_repair_violations += len(repairs)
                    first_local_violation = repairs[0]
                    if config.stop_on_counterexample:
                        write_summary_files(output_dir, config, stats, None, first_local_violation)
                        return stats, None, first_local_violation

        for partition in enumerate_partitions(instance.counts):
            stats.partitions += 1
            platoon, evaluated = optimum_from_cached_delays(
                enumerate_platoon_sequences(partition),
                delay_cache,
                keep_all=config.keep_all_optima,
            )
            stats.platoon_sequence_evaluations += evaluated
            scaled_gap = platoon.total_delay - unrestricted.total_delay
            scaled_bound = scaled_candidate_bound(instance, partition)
            stats.record_case(scaled_gap, scaled_bound)
            if scaled_gap > scaled_bound:
                stats.violations += 1
                first_counterexample = BoundCounterexample(
                    instance=instance,
                    partition=partition,
                    unrestricted=unrestricted,
                    platoon=platoon,
                    scaled_gap=scaled_gap,
                    scaled_bound=scaled_bound,
                )
                if config.stop_on_counterexample:
                    write_summary_files(output_dir, config, stats, first_counterexample, first_local_violation)
                    return stats, first_counterexample, first_local_violation

    write_summary_files(output_dir, config, stats, first_counterexample, first_local_violation)
    return stats, first_counterexample, first_local_violation


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--L", default="2,3", help="comma-separated approach counts")
    parser.add_argument("--max-n", type=int, default=3)
    parser.add_argument("--max-total-vehicles", type=int, default=7)
    parser.add_argument("--max-release", type=int, default=4)
    parser.add_argument("--hF", type=int, default=1)
    parser.add_argument("--hS", default="2,3,4", help="comma-separated hS values")
    parser.add_argument("--output-dir", default="../../results/exhaustive_verification")
    parser.add_argument("--keep-one-optimum", action="store_true")
    parser.add_argument("--continue-after-counterexample", action="store_true")
    parser.add_argument("--skip-local", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    config = SearchConfig(
        L_values=parse_int_list(args.L),
        max_n=args.max_n,
        max_total_vehicles=args.max_total_vehicles,
        max_release=args.max_release,
        hF=args.hF,
        hS_values=parse_int_list(args.hS),
        keep_all_optima=not args.keep_one_optimum,
        stop_on_counterexample=not args.continue_after_counterexample,
        check_local=not args.skip_local,
    )
    stats, counterexample, local_violation = search(config, Path(args.output_dir))
    print(json.dumps(stats.to_json(config), indent=2))
    if local_violation is not None:
        print("LOCAL_REPAIR_VIOLATION_FOUND")
        return 2
    if counterexample is not None:
        print("COUNTEREXAMPLE_FOUND")
        return 1
    print("NO_COUNTEREXAMPLE_FOUND_IN_TESTED_DOMAIN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
