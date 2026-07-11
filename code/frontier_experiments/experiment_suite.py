"""Run the three main experiment groups for the indexed platoon bound."""

from __future__ import annotations

import argparse
import csv
import json
import random
import statistics
import sys
from dataclasses import asdict, dataclass
from fractions import Fraction
from pathlib import Path
from typing import Iterable

VERIFY_DIR = Path(__file__).resolve().parents[1] / "exhaustive_verification"
if str(VERIFY_DIR) not in sys.path:
    sys.path.insert(0, str(VERIFY_DIR))

from model import Instance, Partition, partition_label, scaled_indexed_bound  # noqa: E402
from metrics import fraction_label, ordering_variables, partition_metrics, vehicle_level_ordering_variables  # noqa: E402
from partition_methods import (  # noqa: E402
    bound_aware_loss_budget_partition,
    fixed_size_partition,
    release_gap_threshold_partition,
)
from partition_selection import solve_loss_budget, solve_size_budget  # noqa: E402
from scheduling_milp import ScheduleResult, singleton_partition, solve_downstream_schedule  # noqa: E402


@dataclass(frozen=True)
class Scenario:
    name: str
    counts: tuple[int, ...]
    arrival_mode: str
    hF: int
    hS: int
    max_platoon_size: int
    max_release: int


@dataclass(frozen=True)
class SuiteConfig:
    seed: int
    replications: int
    time_limit: float
    partition_solver: str
    threads: int | None
    loss_budget_fraction: float
    output_dir: str


SCENARIOS = (
    Scenario("balanced_uniform_L3", (5, 5, 5), "uniform", 1, 2, 4, 18),
    Scenario("balanced_poisson_L3", (5, 5, 5), "poisson", 1, 2, 4, 18),
    Scenario("balanced_bursty_L3", (5, 5, 5), "bursty", 1, 2, 4, 18),
    Scenario("unbalanced_uniform_L3", (8, 5, 3), "uniform", 1, 2, 4, 20),
    Scenario("balanced_uniform_L4", (4, 4, 4, 4), "uniform", 1, 2, 4, 18),
    Scenario("high_headway_bursty_L3", (5, 5, 5), "bursty", 1, 3, 4, 18),
)


def generate_releases(
    counts: tuple[int, ...],
    mode: str,
    max_release: int,
    rng: random.Random,
) -> tuple[tuple[int, ...], ...]:
    releases: list[tuple[int, ...]] = []
    for approach, count in enumerate(counts):
        if mode == "uniform":
            row = sorted(rng.randint(0, max_release) for _ in range(count))
        elif mode == "poisson":
            current = rng.randint(0, 2)
            row = []
            rate = 0.7 + 0.15 * approach
            for _ in range(count):
                current += rng.expovariate(rate)
                row.append(round(current))
        elif mode == "bursty":
            centers = sorted(rng.randint(0, max_release) for _ in range(max(2, count // 2)))
            row = sorted(
                max(0, min(max_release, rng.choice(centers) + rng.randint(-1, 1)))
                for _ in range(count)
            )
        else:
            raise ValueError(f"unknown arrival mode: {mode}")
        releases.append(tuple(int(value) for value in row))
    return tuple(releases)


def upper_bound_budget(instance: Instance, fraction: float, max_platoon_size: int) -> int:
    aggressive = fixed_size_partition(instance.counts, max_platoon_size)
    max_bound = scaled_indexed_bound(instance, aggressive)
    return round(max_bound * fraction)


def representative_scenario(replication: int) -> Scenario:
    return SCENARIOS[replication % len(SCENARIOS)]


def method_partitions(
    instance: Instance,
    scenario: Scenario,
    scaled_loss_budget: int,
    partition_solver: str,
) -> dict[str, Partition]:
    return {
        "vehicle_level": singleton_partition(instance.counts),
        "fixed_size_2": fixed_size_partition(instance.counts, 2),
        "fixed_size_3": fixed_size_partition(instance.counts, 3),
        "fixed_size_4": fixed_size_partition(instance.counts, 4),
        "release_gap_hF": release_gap_threshold_partition(
            instance,
            threshold=instance.hF,
            max_platoon_size=scenario.max_platoon_size,
        ),
        "release_gap_hS": release_gap_threshold_partition(
            instance,
            threshold=instance.hS,
            max_platoon_size=scenario.max_platoon_size,
        ),
        "bound_aware_loss_budget": bound_aware_loss_budget_partition(
            instance,
            scaled_loss_budget=scaled_loss_budget,
            max_platoon_size=scenario.max_platoon_size,
            solver=partition_solver,
        ),
    }


def solve_and_record(
    instance: Instance,
    scenario: Scenario,
    replication: int,
    method: str,
    partition: Partition,
    vehicle_average_delay: float | None,
    config: SuiteConfig,
) -> dict[str, object]:
    schedule = solve_downstream_schedule(
        instance,
        partition,
        time_limit=config.time_limit,
        threads=config.threads,
    )
    metrics = partition_metrics(instance, partition)
    actual_gap = None
    if schedule.objective_average_delay is not None and vehicle_average_delay is not None:
        actual_gap = schedule.objective_average_delay - vehicle_average_delay
    return {
        "experiment_group": "comparison_runtime",
        "scenario": scenario.name,
        "replication": replication,
        "method": method,
        "counts": list(instance.counts),
        "releases": [list(row) for row in instance.releases],
        "hF": instance.hF,
        "hS": instance.hS,
        "N": instance.N,
        "partition": partition_label(partition),
        "total_platoons": metrics.total_platoons,
        "platoons_by_approach": list(metrics.platoons_by_approach),
        "ordering_variables": metrics.ordering_variables,
        "vehicle_level_ordering_variables": metrics.vehicle_level_ordering_variables,
        "dimension_reduction_fraction": fraction_label(metrics.dimension_reduction_fraction),
        "scaled_indexed_bound": metrics.scaled_indexed_bound,
        "indexed_bound": float(Fraction(metrics.scaled_indexed_bound, instance.N)),
        "status": schedule.status,
        "runtime_seconds": schedule.runtime_seconds,
        "node_count": schedule.node_count,
        "time_to_first_feasible": schedule.time_to_first_feasible,
        "mip_gap": schedule.mip_gap,
        "objective_average_delay": schedule.objective_average_delay,
        "vehicle_level_average_delay": vehicle_average_delay,
        "actual_average_gap": actual_gap,
        "actual_gap_le_indexed_bound": (
            actual_gap is not None
            and actual_gap <= float(Fraction(metrics.scaled_indexed_bound, instance.N)) + 1e-7
        ),
    }


def frontier_rows_for_instance(
    instance: Instance,
    scenario: Scenario,
    replication: int,
    config: SuiteConfig,
    vehicle_average_delay: float | None,
) -> list[dict[str, object]]:
    c0 = vehicle_level_ordering_variables(instance.counts)
    aggressive = fixed_size_partition(instance.counts, scenario.max_platoon_size)
    max_bound = scaled_indexed_bound(instance, aggressive)
    loss_budgets = sorted({round(max_bound * fraction) for fraction in (0.0, 0.1, 0.25, 0.5, 0.75, 1.0)})
    size_budgets = sorted({round(c0 * fraction) for fraction in (0.2, 0.35, 0.5, 0.7, 1.0)})
    rows: list[dict[str, object]] = []

    selected: list[tuple[str, int, Partition]] = []
    for budget in loss_budgets:
        result = solve_loss_budget(
            instance,
            budget,
            max_platoon_size=scenario.max_platoon_size,
            solver=config.partition_solver,  # type: ignore[arg-type]
        )
        if result.partition is not None:
            selected.append(("loss_budget", budget, result.partition))
    for budget in size_budgets:
        result = solve_size_budget(
            instance,
            budget,
            max_platoon_size=scenario.max_platoon_size,
            solver=config.partition_solver,  # type: ignore[arg-type]
        )
        if result.partition is not None:
            selected.append(("size_budget", budget, result.partition))

    seen: set[tuple[str, int, Partition]] = set()
    for budget_type, budget, partition in selected:
        key = (budget_type, budget, partition)
        if key in seen:
            continue
        seen.add(key)
        schedule = solve_downstream_schedule(
            instance,
            partition,
            time_limit=config.time_limit,
            threads=config.threads,
        )
        metrics = partition_metrics(instance, partition)
        actual_gap = None
        if schedule.objective_average_delay is not None and vehicle_average_delay is not None:
            actual_gap = schedule.objective_average_delay - vehicle_average_delay
        rows.append(
            {
                "experiment_group": "dimension_loss_frontier",
                "scenario": scenario.name,
                "replication": replication,
                "budget_type": budget_type,
                "budget": budget,
                "counts": list(instance.counts),
                "hF": instance.hF,
                "hS": instance.hS,
                "N": instance.N,
                "partition": partition_label(partition),
                "total_platoons": metrics.total_platoons,
                "ordering_variables": metrics.ordering_variables,
                "vehicle_level_ordering_variables": metrics.vehicle_level_ordering_variables,
                "dimension_reduction_fraction": fraction_label(metrics.dimension_reduction_fraction),
                "scaled_indexed_bound": metrics.scaled_indexed_bound,
                "indexed_bound": float(Fraction(metrics.scaled_indexed_bound, instance.N)),
                "runtime_seconds": schedule.runtime_seconds,
                "node_count": schedule.node_count,
                "time_to_first_feasible": schedule.time_to_first_feasible,
                "mip_gap": schedule.mip_gap,
                "objective_average_delay": schedule.objective_average_delay,
                "vehicle_level_average_delay": vehicle_average_delay,
                "actual_average_gap": actual_gap,
            }
        )
    return rows


def summarize(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    groups: dict[tuple[str, str], list[dict[str, object]]] = {}
    for row in rows:
        if row.get("experiment_group") != "comparison_runtime":
            continue
        groups.setdefault((str(row["scenario"]), str(row["method"])), []).append(row)
    summary: list[dict[str, object]] = []
    for (scenario, method), group_rows in sorted(groups.items()):
        def values(key: str) -> list[float]:
            return [float(row[key]) for row in group_rows if row.get(key) is not None]

        def mean_ci95(data: list[float]) -> tuple[float | None, float | None]:
            if not data:
                return None, None
            mean = statistics.fmean(data)
            if len(data) < 2:
                return mean, 0.0
            return mean, 1.96 * statistics.stdev(data) / (len(data) ** 0.5)

        runtime = values("runtime_seconds")
        gap = values("actual_average_gap")
        bound = values("indexed_bound")
        dimension = values("ordering_variables")
        nodes = values("node_count")
        reduction = []
        for row in group_rows:
            text = str(row["dimension_reduction_fraction"])
            reduction.append(float(Fraction(text)))
        mean_runtime, ci_runtime = mean_ci95(runtime)
        mean_nodes, ci_nodes = mean_ci95(nodes)
        mean_gap, ci_gap = mean_ci95(gap)
        mean_bound, ci_bound = mean_ci95(bound)
        mean_dimension, ci_dimension = mean_ci95(dimension)
        mean_reduction, ci_reduction = mean_ci95(reduction)
        summary.append(
            {
                "scenario": scenario,
                "method": method,
                "cases": len(group_rows),
                "mean_runtime_seconds": mean_runtime,
                "ci95_runtime_seconds": ci_runtime,
                "mean_node_count": mean_nodes,
                "ci95_node_count": ci_nodes,
                "mean_actual_average_gap": mean_gap,
                "ci95_actual_average_gap": ci_gap,
                "mean_indexed_bound": mean_bound,
                "ci95_indexed_bound": ci_bound,
                "mean_ordering_variables": mean_dimension,
                "ci95_ordering_variables": ci_dimension,
                "mean_dimension_reduction_fraction": mean_reduction,
                "ci95_dimension_reduction_fraction": ci_reduction,
                "all_actual_gaps_within_bound": all(
                    bool(row.get("actual_gap_le_indexed_bound"))
                    for row in group_rows
                    if row.get("actual_average_gap") is not None
                ),
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


def run_suite(config: SuiteConfig) -> dict[str, object]:
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(config.seed)
    all_rows: list[dict[str, object]] = []
    frontier_rows: list[dict[str, object]] = []

    for replication in range(config.replications):
        scenario = representative_scenario(replication)
        releases = generate_releases(scenario.counts, scenario.arrival_mode, scenario.max_release, rng)
        instance = Instance(
            counts=scenario.counts,
            releases=releases,
            hF=scenario.hF,
            hS=scenario.hS,
        )
        scaled_loss_budget = upper_bound_budget(
            instance,
            config.loss_budget_fraction,
            scenario.max_platoon_size,
        )
        vehicle_partition = singleton_partition(instance.counts)
        vehicle_schedule = solve_downstream_schedule(
            instance,
            vehicle_partition,
            time_limit=config.time_limit,
            threads=config.threads,
        )
        vehicle_average_delay = vehicle_schedule.objective_average_delay
        partitions = method_partitions(
            instance,
            scenario,
            scaled_loss_budget,
            config.partition_solver,
        )
        for method, partition in partitions.items():
            all_rows.append(
                solve_and_record(
                    instance,
                    scenario,
                    replication,
                    method,
                    partition,
                    vehicle_average_delay,
                    config,
                )
            )
        if replication < min(6, config.replications):
            frontier_rows.extend(
                frontier_rows_for_instance(
                    instance,
                    scenario,
                    replication,
                    config,
                    vehicle_average_delay,
                )
            )

    summary_rows = summarize(all_rows)
    payload = {
        "config": asdict(config),
        "scenarios": [asdict(scenario) for scenario in SCENARIOS],
        "comparison_runtime_rows": all_rows,
        "dimension_loss_frontier_rows": frontier_rows,
        "summary": summary_rows,
    }
    (output_dir / "experiment_suite.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_csv(output_dir / "comparison_runtime.csv", all_rows)
    write_csv(output_dir / "dimension_loss_frontier.csv", frontier_rows)
    write_csv(output_dir / "summary.csv", summary_rows)
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=20260710)
    parser.add_argument("--replications", type=int, default=30)
    parser.add_argument("--time-limit", type=float, default=5.0)
    parser.add_argument("--partition-solver", choices=("gurobi", "enum", "auto"), default="gurobi")
    parser.add_argument("--threads", type=int)
    parser.add_argument("--loss-budget-fraction", type=float, default=0.5)
    parser.add_argument("--output-dir", default="../../results/frontier_experiments/paper_core_30")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    config = SuiteConfig(
        seed=args.seed,
        replications=args.replications,
        time_limit=args.time_limit,
        partition_solver=args.partition_solver,
        threads=args.threads,
        loss_budget_fraction=args.loss_budget_fraction,
        output_dir=args.output_dir,
    )
    payload = run_suite(config)
    print(json.dumps({
        "output_dir": args.output_dir,
        "comparison_runtime_rows": len(payload["comparison_runtime_rows"]),
        "dimension_loss_frontier_rows": len(payload["dimension_loss_frontier_rows"]),
        "summary_rows": len(payload["summary"]),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
