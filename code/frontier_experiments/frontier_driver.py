"""Generate dimension-loss frontier data for a single traffic instance."""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from dataclasses import asdict, dataclass
from fractions import Fraction
from pathlib import Path
from typing import Iterable

VERIFY_DIR = Path(__file__).resolve().parents[1] / "exhaustive_verification"
if str(VERIFY_DIR) not in sys.path:
    sys.path.insert(0, str(VERIFY_DIR))

from enumerate_partitions import enumerate_partitions  # noqa: E402
from enumerate_sequences import enumerate_fifo_sequences, enumerate_platoon_sequences  # noqa: E402
from model import Instance, Partition, optimum_for_sequences, partition_label, total_delay  # noqa: E402
from metrics import (  # noqa: E402
    fraction_label,
    partition_metrics,
    respects_max_platoon_size,
    vehicle_level_ordering_variables,
)
from partition_selection import solve_loss_budget, solve_size_budget  # noqa: E402


@dataclass(frozen=True)
class FrontierConfig:
    counts: tuple[int, ...]
    hF: int
    hS: int
    releases: tuple[tuple[int, ...], ...]
    max_platoon_size: int | None
    solver: str
    compute_actual_gap: bool
    max_total_for_exact_gap: int
    seed: int
    arrival_mode: str


def parse_int_tuple(value: str) -> tuple[int, ...]:
    return tuple(int(part.strip()) for part in value.split(",") if part.strip())


def generate_releases(
    counts: tuple[int, ...],
    mode: str,
    max_release: int,
    seed: int,
) -> tuple[tuple[int, ...], ...]:
    rng = random.Random(seed)
    releases: list[tuple[int, ...]] = []
    for count in counts:
        if mode == "uniform":
            row = sorted(rng.randint(0, max_release) for _ in range(count))
        elif mode == "poisson":
            current = 0.0
            row = []
            for _ in range(count):
                current += rng.expovariate(1.0)
                row.append(round(current))
        elif mode == "bursty":
            centers = sorted(rng.randint(0, max_release) for _ in range(max(1, count // 3)))
            row = sorted(
                max(0, min(max_release, rng.choice(centers) + rng.randint(-1, 1)))
                for _ in range(count)
            )
        else:
            raise ValueError(f"unknown arrival mode: {mode}")
        releases.append(tuple(int(value) for value in row))
    return tuple(releases)


def all_valid_partitions(instance: Instance, max_platoon_size: int | None) -> list[Partition]:
    return [
        partition
        for partition in enumerate_partitions(instance.counts)
        if respects_max_platoon_size(partition, max_platoon_size)
    ]


def nondominated_pairs(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    """Keep rows not dominated in both C(Pi) and B_idx(Pi)."""

    frontier: list[dict[str, object]] = []
    for row in rows:
        c_pi = int(row["ordering_variables"])
        bound = int(row["scaled_indexed_bound"])
        dominated = False
        for other in rows:
            other_c = int(other["ordering_variables"])
            other_bound = int(other["scaled_indexed_bound"])
            if (
                other_c <= c_pi
                and other_bound <= bound
                and (other_c < c_pi or other_bound < bound)
            ):
                dominated = True
                break
        if not dominated:
            frontier.append(row)
    return sorted(frontier, key=lambda item: (int(item["ordering_variables"]), int(item["scaled_indexed_bound"])))


def exact_gap_map(instance: Instance, partitions: Iterable[Partition]) -> dict[Partition, int]:
    releases = instance.release_map
    vehicle_sequences = tuple(enumerate_fifo_sequences(instance.counts))
    delay_cache = {
        sequence: total_delay(sequence, releases, instance.hF, instance.hS)
        for sequence in vehicle_sequences
    }
    unrestricted = optimum_for_sequences(
        vehicle_sequences,
        releases,
        instance.hF,
        instance.hS,
        keep_all=False,
    )
    gaps: dict[Partition, int] = {}
    for partition in partitions:
        platoon = optimum_for_sequences(
            enumerate_platoon_sequences(partition),
            releases,
            instance.hF,
            instance.hS,
            keep_all=False,
        )
        gaps[partition] = platoon.total_delay - unrestricted.total_delay
    return gaps


def row_for_partition(
    instance: Instance,
    partition: Partition,
    actual_scaled_gap: int | None,
) -> dict[str, object]:
    metrics = partition_metrics(instance, partition)
    row: dict[str, object] = {
        "partition": partition_label(partition),
        "platoons_by_approach": list(metrics.platoons_by_approach),
        "total_platoons": metrics.total_platoons,
        "ordering_variables": metrics.ordering_variables,
        "vehicle_level_ordering_variables": metrics.vehicle_level_ordering_variables,
        "dimension_reduction_fraction": fraction_label(metrics.dimension_reduction_fraction),
        "scaled_indexed_bound": metrics.scaled_indexed_bound,
        "indexed_bound": fraction_label(Fraction(metrics.scaled_indexed_bound, instance.N)),
    }
    if actual_scaled_gap is not None:
        row["actual_scaled_gap"] = actual_scaled_gap
        row["actual_average_gap"] = fraction_label(Fraction(actual_scaled_gap, instance.N))
        row["gap_le_indexed_bound"] = actual_scaled_gap <= metrics.scaled_indexed_bound
    return row


def budget_values(rows: list[dict[str, object]], key: str) -> list[int]:
    return sorted({int(row[key]) for row in rows})


def generate_frontier(config: FrontierConfig, output_dir: Path) -> dict[str, object]:
    instance = Instance(
        counts=config.counts,
        releases=config.releases,
        hF=config.hF,
        hS=config.hS,
    )
    partitions = all_valid_partitions(instance, config.max_platoon_size)
    compute_actual = config.compute_actual_gap and instance.N <= config.max_total_for_exact_gap
    gaps = exact_gap_map(instance, partitions) if compute_actual else {}

    all_rows = [
        row_for_partition(instance, partition, gaps.get(partition))
        for partition in partitions
    ]
    pareto_rows = nondominated_pairs(all_rows)

    loss_budget_rows = []
    for budget in budget_values(all_rows, "scaled_indexed_bound"):
        result = solve_loss_budget(
            instance,
            budget,
            config.max_platoon_size,
            solver=config.solver,  # type: ignore[arg-type]
        )
        row = result.to_json()
        if result.partition is not None:
            row.update(row_for_partition(instance, result.partition, gaps.get(result.partition)))
        loss_budget_rows.append(row)

    size_budget_rows = []
    for budget in budget_values(all_rows, "ordering_variables"):
        result = solve_size_budget(
            instance,
            budget,
            config.max_platoon_size,
            solver=config.solver,  # type: ignore[arg-type]
        )
        row = result.to_json()
        if result.partition is not None:
            row.update(row_for_partition(instance, result.partition, gaps.get(result.partition)))
        size_budget_rows.append(row)

    output_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "config": asdict(config),
        "N": instance.N,
        "vehicle_level_ordering_variables": vehicle_level_ordering_variables(instance.counts),
        "partition_count": len(partitions),
        "actual_gap_computed": compute_actual,
        "pareto_frontier": pareto_rows,
        "loss_budget_solutions": loss_budget_rows,
        "size_budget_solutions": size_budget_rows,
    }
    (output_dir / "frontier.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_csv(output_dir / "pareto_frontier.csv", pareto_rows)
    write_csv(output_dir / "loss_budget_solutions.csv", loss_budget_rows)
    write_csv(output_dir / "size_budget_solutions.csv", size_budget_rows)
    return payload


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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--counts", default="4,4,4")
    parser.add_argument("--hF", type=int, default=1)
    parser.add_argument("--hS", type=int, default=2)
    parser.add_argument("--releases", help="semicolon-separated rows, e.g. 0,1,3;0,2,5")
    parser.add_argument("--arrival-mode", choices=("uniform", "poisson", "bursty"), default="uniform")
    parser.add_argument("--max-release", type=int, default=8)
    parser.add_argument("--seed", type=int, default=20260710)
    parser.add_argument("--max-platoon-size", type=int)
    parser.add_argument("--solver", choices=("auto", "gurobi", "enum"), default="auto")
    parser.add_argument("--skip-actual-gap", action="store_true")
    parser.add_argument("--max-total-for-exact-gap", type=int, default=9)
    parser.add_argument("--output-dir", default="../../results/frontier_experiments/smoke")
    return parser


def parse_releases(value: str) -> tuple[tuple[int, ...], ...]:
    return tuple(parse_int_tuple(row) for row in value.split(";") if row.strip())


def main() -> int:
    args = build_parser().parse_args()
    counts = parse_int_tuple(args.counts)
    releases = (
        parse_releases(args.releases)
        if args.releases
        else generate_releases(counts, args.arrival_mode, args.max_release, args.seed)
    )
    config = FrontierConfig(
        counts=counts,
        hF=args.hF,
        hS=args.hS,
        releases=releases,
        max_platoon_size=args.max_platoon_size,
        solver=args.solver,
        compute_actual_gap=not args.skip_actual_gap,
        max_total_for_exact_gap=args.max_total_for_exact_gap,
        seed=args.seed,
        arrival_mode=args.arrival_mode,
    )
    payload = generate_frontier(config, Path(args.output_dir))
    print(json.dumps({
        "output_dir": args.output_dir,
        "partition_count": payload["partition_count"],
        "pareto_points": len(payload["pareto_frontier"]),
        "actual_gap_computed": payload["actual_gap_computed"],
        "vehicle_level_ordering_variables": payload["vehicle_level_ordering_variables"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

