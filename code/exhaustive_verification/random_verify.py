"""Reproducible random-exact verification for sampled small instances."""

from __future__ import annotations

import argparse
import json
import random
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from enumerate_partitions import enumerate_partitions
from enumerate_sequences import enumerate_fifo_sequences, enumerate_platoon_sequences
from model import (
    Instance,
    Optimum,
    Partition,
    optimum_for_sequences,
    scaled_index_free_bound,
    scaled_indexed_bound,
    total_delay,
)
from verify_bound import (
    BoundCounterexample,
    check_repair_trace,
    parse_int_list,
    render_counterexample_markdown,
)


@dataclass
class RandomConfig:
    seed: int
    samples: int
    L_values: tuple[int, ...]
    max_n: int
    max_total_vehicles: int
    max_release: int
    hF: int
    hS_values: tuple[int, ...]
    partitions_per_instance: int
    check_repair: bool


@dataclass
class RandomStats:
    sampled_instances: int = 0
    sampled_partitions: int = 0
    vehicle_sequence_evaluations: int = 0
    platoon_sequence_evaluations: int = 0
    repair_traces_checked: int = 0
    repair_steps_checked: int = 0
    local_repair_violations: int = 0
    indexed_bound_violations: int = 0
    bound_dominance_violations: int = 0
    indexed_zero_bound_cases: int = 0
    index_free_zero_bound_cases: int = 0
    indexed_positive_bound_cases: int = 0
    index_free_positive_bound_cases: int = 0
    max_gap_over_indexed_bound_num: int = 0
    max_gap_over_indexed_bound_den: int = 1
    max_gap_over_index_free_bound_num: int = 0
    max_gap_over_index_free_bound_den: int = 1
    total_scaled_indexed_bound: int = 0
    total_scaled_index_free_bound: int = 0
    max_scaled_bound_reduction: int = 0
    positive_equality_cases: int = 0
    zero_equality_cases: int = 0
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None

    @property
    def runtime_seconds(self) -> float:
        end = self.end_time if self.end_time is not None else time.time()
        return end - self.start_time

    def record_case(self, scaled_gap: int, scaled_indexed: int, scaled_index_free: int) -> None:
        self.total_scaled_indexed_bound += scaled_indexed
        self.total_scaled_index_free_bound += scaled_index_free
        self.max_scaled_bound_reduction = max(
            self.max_scaled_bound_reduction,
            scaled_index_free - scaled_indexed,
        )
        if scaled_gap == scaled_indexed and scaled_gap > 0:
            self.positive_equality_cases += 1
        if scaled_gap == scaled_indexed and scaled_gap == 0:
            self.zero_equality_cases += 1
        if scaled_indexed == 0:
            self.indexed_zero_bound_cases += 1
        else:
            self.indexed_positive_bound_cases += 1
            if (
                scaled_gap * self.max_gap_over_indexed_bound_den
                > self.max_gap_over_indexed_bound_num * scaled_indexed
            ):
                self.max_gap_over_indexed_bound_num = scaled_gap
                self.max_gap_over_indexed_bound_den = scaled_indexed
        if scaled_index_free == 0:
            self.index_free_zero_bound_cases += 1
        else:
            self.index_free_positive_bound_cases += 1
            if (
                scaled_gap * self.max_gap_over_index_free_bound_den
                > self.max_gap_over_index_free_bound_num * scaled_index_free
            ):
                self.max_gap_over_index_free_bound_num = scaled_gap
                self.max_gap_over_index_free_bound_den = scaled_index_free

    def to_json(self, config: RandomConfig) -> dict[str, object]:
        data = asdict(self)
        data["runtime_seconds"] = self.runtime_seconds
        data["max_gap_over_indexed_bound"] = (
            f"{self.max_gap_over_indexed_bound_num}/{self.max_gap_over_indexed_bound_den}"
            if self.indexed_positive_bound_cases
            else None
        )
        data["max_gap_over_index_free_bound"] = (
            f"{self.max_gap_over_index_free_bound_num}/{self.max_gap_over_index_free_bound_den}"
            if self.index_free_positive_bound_cases
            else None
        )
        data["total_equality_cases"] = self.positive_equality_cases + self.zero_equality_cases
        if self.total_scaled_index_free_bound:
            data["aggregate_indexed_bound_reduction"] = (
                "1 - sum(B_idx)/sum(B_0)"
            )
            data["aggregate_indexed_bound_reduction_fraction"] = (
                f"{self.total_scaled_index_free_bound - self.total_scaled_indexed_bound}/"
                f"{self.total_scaled_index_free_bound}"
            )
        else:
            data["aggregate_indexed_bound_reduction"] = None
            data["aggregate_indexed_bound_reduction_fraction"] = None
        data["config"] = asdict(config)
        return data


def random_counts(rng: random.Random, config: RandomConfig) -> tuple[int, ...]:
    while True:
        L = rng.choice(config.L_values)
        counts = tuple(rng.randint(1, config.max_n) for _ in range(L))
        if 2 <= sum(counts) <= config.max_total_vehicles:
            return counts


def random_releases(
    rng: random.Random,
    counts: tuple[int, ...],
    max_release: int,
) -> tuple[tuple[int, ...], ...]:
    return tuple(
        tuple(sorted(rng.randint(0, max_release) for _ in range(count)))
        for count in counts
    )


def optimum_from_cache(
    partition: Partition,
    delay_cache: dict[tuple[tuple[int, int], ...], int],
) -> tuple[Optimum, int]:
    best_delay: int | None = None
    best_sequences: list[tuple[tuple[int, int], ...]] = []
    evaluated = 0
    for sequence in enumerate_platoon_sequences(partition):
        evaluated += 1
        delay = delay_cache[sequence]
        if best_delay is None or delay < best_delay:
            best_delay = delay
            best_sequences = [sequence]
        elif delay == best_delay:
            best_sequences.append(sequence)
    if best_delay is None:
        raise ValueError("partition produced no feasible sequences")
    return Optimum(best_delay, tuple(best_sequences)), evaluated


def selected_partitions(
    rng: random.Random,
    partitions: tuple[Partition, ...],
    partitions_per_instance: int,
) -> tuple[Partition, ...]:
    if partitions_per_instance <= 0 or partitions_per_instance >= len(partitions):
        return partitions
    indices = rng.sample(range(len(partitions)), partitions_per_instance)
    return tuple(partitions[index] for index in indices)


def write_random_results(
    output_dir: Path,
    config: RandomConfig,
    stats: RandomStats,
    counterexample: BoundCounterexample | None,
    local_violation: dict[str, object] | None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    stats.end_time = time.time()
    summary = stats.to_json(config)
    summary["indexed_counterexample_found"] = counterexample is not None
    summary["local_repair_violation_found"] = local_violation is not None
    (output_dir / "indexed_random_summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    if counterexample is not None:
        (output_dir / "indexed_random_counterexample.json").write_text(
            json.dumps(counterexample.to_json(), indent=2),
            encoding="utf-8",
        )
        (output_dir / "indexed_random_counterexample.md").write_text(
            render_counterexample_markdown(counterexample),
            encoding="utf-8",
        )
    if local_violation is not None:
        (output_dir / "indexed_random_local_repair_violation.json").write_text(
            json.dumps(local_violation, indent=2),
            encoding="utf-8",
        )


def run_random(
    config: RandomConfig,
    output_dir: Path,
) -> tuple[RandomStats, BoundCounterexample | None, dict[str, object] | None]:
    rng = random.Random(config.seed)
    stats = RandomStats()
    first_counterexample: BoundCounterexample | None = None
    first_local_violation: dict[str, object] | None = None

    for _ in range(config.samples):
        counts = random_counts(rng, config)
        instance = Instance(
            counts=counts,
            releases=random_releases(rng, counts, config.max_release),
            hF=config.hF,
            hS=rng.choice(config.hS_values),
        )
        stats.sampled_instances += 1
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
        )

        all_partitions = tuple(enumerate_partitions(instance.counts))
        for partition in selected_partitions(rng, all_partitions, config.partitions_per_instance):
            repair_result = None
            if config.check_repair:
                repair_result, first_local_violation = check_repair_trace(
                    instance,
                    partition,
                    unrestricted,
                )
                stats.repair_traces_checked += 1
                stats.repair_steps_checked += len(repair_result.records)
                if first_local_violation is not None:
                    stats.local_repair_violations += 1
                    write_random_results(output_dir, config, stats, None, first_local_violation)
                    return stats, None, first_local_violation

            stats.sampled_partitions += 1
            platoon, evaluated = optimum_from_cache(partition, delay_cache)
            stats.platoon_sequence_evaluations += evaluated
            scaled_gap = platoon.total_delay - unrestricted.total_delay
            scaled_indexed = scaled_indexed_bound(instance, partition)
            scaled_index_free = scaled_index_free_bound(instance, partition)
            stats.record_case(scaled_gap, scaled_indexed, scaled_index_free)

            if scaled_indexed > scaled_index_free:
                stats.bound_dominance_violations += 1
                first_counterexample = BoundCounterexample(
                    instance=instance,
                    partition=partition,
                    unrestricted=unrestricted,
                    platoon=platoon,
                    scaled_gap=scaled_gap,
                    scaled_indexed_bound=scaled_indexed,
                    scaled_index_free_bound=scaled_index_free,
                    repair_result=repair_result,
                    violation_type="indexed_bound_dominance_violation",
                )
                write_random_results(output_dir, config, stats, first_counterexample, None)
                return stats, first_counterexample, None

            if scaled_gap > scaled_indexed:
                stats.indexed_bound_violations += 1
                first_counterexample = BoundCounterexample(
                    instance=instance,
                    partition=partition,
                    unrestricted=unrestricted,
                    platoon=platoon,
                    scaled_gap=scaled_gap,
                    scaled_indexed_bound=scaled_indexed,
                    scaled_index_free_bound=scaled_index_free,
                    repair_result=repair_result,
                )
                write_random_results(output_dir, config, stats, first_counterexample, None)
                return stats, first_counterexample, None

    write_random_results(output_dir, config, stats, None, None)
    return stats, None, None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=20260710)
    parser.add_argument("--samples", type=int, default=1000)
    parser.add_argument("--L", default="2,3")
    parser.add_argument("--max-n", type=int, default=5)
    parser.add_argument("--max-total-vehicles", type=int, default=10)
    parser.add_argument("--max-release", type=int, default=8)
    parser.add_argument("--hF", type=int, default=1)
    parser.add_argument("--hS", default="2,3,4")
    parser.add_argument("--partitions-per-instance", type=int, default=0)
    parser.add_argument("--skip-repair", action="store_true")
    parser.add_argument("--output-dir", default="../../results/exhaustive_verification/indexed")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    config = RandomConfig(
        seed=args.seed,
        samples=args.samples,
        L_values=parse_int_list(args.L),
        max_n=args.max_n,
        max_total_vehicles=args.max_total_vehicles,
        max_release=args.max_release,
        hF=args.hF,
        hS_values=parse_int_list(args.hS),
        partitions_per_instance=args.partitions_per_instance,
        check_repair=not args.skip_repair,
    )
    stats, counterexample, local_violation = run_random(config, Path(args.output_dir))
    print(json.dumps(stats.to_json(config), indent=2))
    if local_violation is not None:
        print("LOCAL_REPAIR_OR_GLOBAL_REPAIR_INVARIANT_VIOLATION_FOUND")
        return 2
    if counterexample is not None:
        print("INDEXED_COUNTEREXAMPLE_FOUND")
        return 1
    print("NO_COUNTEREXAMPLE_FOUND_IN_INDEXED_RANDOM_TESTED_DOMAIN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
