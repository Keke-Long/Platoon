"""Fair dimension-target and scalability experiments."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import statistics
import sys
import time
from dataclasses import asdict, dataclass
from fractions import Fraction
from pathlib import Path
from typing import Iterable

VERIFY_DIR = Path(__file__).resolve().parents[1] / "exhaustive_verification"
if str(VERIFY_DIR) not in sys.path:
    sys.path.insert(0, str(VERIFY_DIR))

from model import Instance, Partition, partition_label, scaled_indexed_bound  # noqa: E402
from metrics import ordering_variables, partition_metrics, vehicle_level_ordering_variables  # noqa: E402
from partition_methods import fixed_size_partition, release_gap_threshold_partition  # noqa: E402
from partition_selection import PartitionSelectionResult, solve_size_budget  # noqa: E402
from scheduling_milp import singleton_partition, solve_downstream_schedule  # noqa: E402


@dataclass(frozen=True)
class ScalabilityConfig:
    seed: int
    reps_per_cell: int
    n_values: tuple[int, ...]
    l_values: tuple[int, ...]
    demand_patterns: tuple[str, ...]
    arrival_modes: tuple[str, ...]
    targets: tuple[float, ...]
    hF: int
    hS_values: tuple[int, ...]
    max_platoon_size: int
    time_limit: float
    threads: int
    output_dir: str
    frontier_instance_limit: int
    frontier_budget_count: int


@dataclass(frozen=True)
class Scenario:
    name: str
    counts: tuple[int, ...]
    demand_pattern: str
    arrival_mode: str
    hF: int
    hS: int
    max_release: int


def parse_int_tuple(value: str) -> tuple[int, ...]:
    return tuple(int(part.strip()) for part in value.split(",") if part.strip())


def parse_float_tuple(value: str) -> tuple[float, ...]:
    return tuple(float(part.strip()) for part in value.split(",") if part.strip())


def counts_for(total_vehicles: int, approaches: int, demand_pattern: str) -> tuple[int, ...]:
    if total_vehicles < approaches:
        raise ValueError("total_vehicles must be at least the number of approaches")
    if demand_pattern == "balanced":
        base = total_vehicles // approaches
        remainder = total_vehicles % approaches
        return tuple(base + (1 if idx < remainder else 0) for idx in range(approaches))
    if demand_pattern == "unbalanced":
        weights = [approaches - idx for idx in range(approaches)]
        total_weight = sum(weights)
        raw = [max(1, round(total_vehicles * weight / total_weight)) for weight in weights]
        while sum(raw) < total_vehicles:
            raw[0] += 1
        while sum(raw) > total_vehicles:
            idx = max(range(approaches), key=lambda i: raw[i])
            if raw[idx] == 1:
                break
            raw[idx] -= 1
        return tuple(raw)
    raise ValueError(f"unknown demand pattern: {demand_pattern}")


def scenarios(config: ScalabilityConfig) -> list[Scenario]:
    result: list[Scenario] = []
    for n in config.n_values:
        for l_value in config.l_values:
            for demand in config.demand_patterns:
                counts = counts_for(n, l_value, demand)
                for arrival in config.arrival_modes:
                    for hS in config.hS_values:
                        name = f"N{n}_L{l_value}_{demand}_{arrival}_hS{hS}"
                        result.append(
                            Scenario(
                                name=name,
                                counts=counts,
                                demand_pattern=demand,
                                arrival_mode=arrival,
                                hF=config.hF,
                                hS=hS,
                                max_release=max(10, 2 * n),
                            )
                        )
    return result


def generate_releases(scenario: Scenario, rng: random.Random) -> tuple[tuple[int, ...], ...]:
    releases: list[tuple[int, ...]] = []
    for approach, count in enumerate(scenario.counts):
        if scenario.arrival_mode == "uniform":
            row = sorted(rng.randint(0, scenario.max_release) for _ in range(count))
        elif scenario.arrival_mode == "poisson":
            current = rng.randint(0, 3)
            rate = 0.45 + 0.1 * (approach % 3)
            row = []
            for _ in range(count):
                current += rng.expovariate(rate)
                row.append(round(current))
        elif scenario.arrival_mode == "bursty":
            centers = sorted(rng.randint(0, scenario.max_release) for _ in range(max(2, count // 4)))
            row = sorted(
                max(0, min(scenario.max_release, rng.choice(centers) + rng.randint(-2, 2)))
                for _ in range(count)
            )
        else:
            raise ValueError(f"unknown arrival mode: {scenario.arrival_mode}")
        releases.append(tuple(int(value) for value in row))
    return tuple(releases)


def replication_seed(base_seed: int, scenario: Scenario, replication: int) -> int:
    material = json.dumps(
        {
            "base_seed": base_seed,
            "scenario": asdict(scenario),
            "replication": replication,
        },
        sort_keys=True,
    ).encode("utf-8")
    return int.from_bytes(hashlib.sha256(material).digest()[:8], "big")


def instance_for_replication(
    scenario: Scenario,
    replication: int,
    base_seed: int,
) -> tuple[Instance, int]:
    seed = replication_seed(base_seed, scenario, replication)
    rng = random.Random(seed)
    instance = Instance(
        counts=scenario.counts,
        releases=generate_releases(scenario, rng),
        hF=scenario.hF,
        hS=scenario.hS,
    )
    return instance, seed


def target_ordering_budget(instance: Instance, reduction_target: float) -> int:
    c0 = vehicle_level_ordering_variables(instance.counts)
    return max(1, round(c0 * (1.0 - reduction_target)))


def choose_largest_feasible_dimension(
    candidates: Iterable[tuple[str, Partition]],
    target_c: int,
) -> tuple[str, Partition]:
    best_feasible: tuple[tuple[int, str], str, Partition] | None = None
    smallest: tuple[tuple[int, str], str, Partition] | None = None
    for label, partition in candidates:
        c_pi = ordering_variables(partition)
        smallest_key = (c_pi, label)
        if smallest is None or smallest_key < smallest[0]:
            smallest = (smallest_key, label, partition)
        if c_pi <= target_c:
            key = (-c_pi, label)
            if best_feasible is None or key < best_feasible[0]:
                best_feasible = (key, label, partition)
    if best_feasible is not None:
        return best_feasible[1], best_feasible[2]
    raise ValueError("at least one candidate partition is required")


def sampled_budgets(min_budget: int, max_budget: int, count: int) -> list[int]:
    if count <= 0 or min_budget >= max_budget:
        return [min_budget]
    values = {
        round(min_budget + (max_budget - min_budget) * step / count)
        for step in range(count + 1)
    }
    values.add(min_budget)
    values.add(max_budget)
    return sorted(values)


def min_budget_for_max_platoon_size(instance: Instance, max_platoon_size: int) -> int:
    aggressive = tuple(
        tuple(
            [max_platoon_size] * (count // max_platoon_size)
            + ([count % max_platoon_size] if count % max_platoon_size else [])
        )
        for count in instance.counts
    )
    return ordering_variables(aggressive)


def is_small_frontier_instance(instance: Instance) -> bool:
    return instance.N <= 20


def fixed_size_candidates(instance: Instance, max_platoon_size: int) -> list[tuple[str, Partition]]:
    return [
        (f"fixed_size_{size}", fixed_size_partition(instance.counts, size))
        for size in range(1, max_platoon_size + 1)
    ]


def threshold_candidates(instance: Instance, max_platoon_size: int) -> list[tuple[str, Partition]]:
    gaps = {0, instance.hF, instance.hS}
    for releases in instance.releases:
        gaps.update(right - left for left, right in zip(releases, releases[1:], strict=False))
    return [
        (
            f"release_gap_threshold_{threshold}",
            release_gap_threshold_partition(instance, threshold, max_platoon_size=max_platoon_size),
        )
        for threshold in sorted(gaps)
    ]


def solve_partition_proposed(
    instance: Instance,
    target_c: int,
    max_platoon_size: int,
    time_limit: float | None,
) -> tuple[PartitionSelectionResult, Partition]:
    result = solve_size_budget(
        instance,
        target_c,
        max_platoon_size=max_platoon_size,
        solver="gurobi",
        time_limit=time_limit,
    )
    partition = result.partition if result.partition is not None else singleton_partition(instance.counts)
    return result, partition


def timed_baseline_partition(
    builder,
) -> tuple[str, Partition, float, float, float]:
    start = time.perf_counter()
    label, partition = builder()
    elapsed = time.perf_counter() - start
    return label, partition, elapsed, elapsed, 0.0


def record_method(
    instance: Instance,
    scenario: Scenario,
    replication: int,
    target: float,
    target_c: int,
    raw_target_c: int,
    method_family: str,
    method_detail: str,
    partition: Partition,
    partition_time: float,
    partition_model_construction_time: float,
    partition_optimization_time: float,
    vehicle_average_delay: float | None,
    vehicle_schedule,
    config: ScalabilityConfig,
) -> dict[str, object]:
    schedule = solve_downstream_schedule(
        instance,
        partition,
        time_limit=config.time_limit,
        threads=config.threads,
    )
    metrics = partition_metrics(instance, partition)
    theoretical_bound = float(Fraction(metrics.scaled_indexed_bound, instance.N))
    actual_gap = None
    if (
        schedule.status == "OPTIMAL"
        and vehicle_schedule.status == "OPTIMAL"
        and schedule.objective_average_delay is not None
        and vehicle_average_delay is not None
    ):
        actual_gap = schedule.objective_average_delay - vehicle_average_delay
    gap_within_bound = None if actual_gap is None else actual_gap <= theoretical_bound + 1e-7
    return {
        "scenario": scenario.name,
        "replication": replication,
        "target_dimension_reduction": target,
        "raw_target_ordering_budget": raw_target_c,
        "target_ordering_budget": target_c,
        "method_family": method_family,
        "method_detail": method_detail,
        "N": instance.N,
        "L": instance.L,
        "counts": list(instance.counts),
        "demand_pattern": scenario.demand_pattern,
        "arrival_mode": scenario.arrival_mode,
        "hF": instance.hF,
        "hS": instance.hS,
        "max_platoon_size": config.max_platoon_size,
        "partition": partition_label(partition),
        "total_platoons": metrics.total_platoons,
        "platoons_by_approach": list(metrics.platoons_by_approach),
        "ordering_variables": metrics.ordering_variables,
        "vehicle_level_ordering_variables": metrics.vehicle_level_ordering_variables,
        "dimension_reduction_fraction": float(metrics.dimension_reduction_fraction),
        "scaled_indexed_bound": metrics.scaled_indexed_bound,
        "indexed_bound": theoretical_bound,
        "actual_average_gap": actual_gap,
        "actual_gap_le_indexed_bound": gap_within_bound,
        "vehicle_level_average_delay": vehicle_average_delay,
        "vehicle_level_incumbent_average_delay": vehicle_schedule.objective_average_delay,
        "vehicle_level_status": vehicle_schedule.status,
        "vehicle_level_mip_gap": vehicle_schedule.mip_gap,
        "vehicle_level_nodes": vehicle_schedule.node_count,
        "vehicle_level_time_to_first_feasible": vehicle_schedule.time_to_first_feasible,
        "vehicle_level_model_construction_seconds": vehicle_schedule.model_construction_seconds,
        "vehicle_level_downstream_optimization_seconds": vehicle_schedule.runtime_seconds,
        "vehicle_level_wall_time_seconds": vehicle_schedule.end_to_end_seconds,
        "objective_average_delay": schedule.objective_average_delay,
        "status": schedule.status,
        "mip_gap": schedule.mip_gap,
        "nodes": schedule.node_count,
        "time_to_first_feasible": schedule.time_to_first_feasible,
        "partition_time_seconds": partition_time,
        "partition_model_construction_seconds": partition_model_construction_time,
        "partition_optimization_seconds": partition_optimization_time,
        "model_construction_seconds": schedule.model_construction_seconds,
        "downstream_optimization_seconds": schedule.runtime_seconds,
        "end_to_end_seconds": (
            partition_time + schedule.end_to_end_seconds
        ),
    }


def run_replication(
    instance: Instance,
    scenario: Scenario,
    replication: int,
    config: ScalabilityConfig,
    include_frontier: bool,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    rows: list[dict[str, object]] = []
    frontier_rows: list[dict[str, object]] = []
    vehicle_schedule = solve_downstream_schedule(
        instance,
        singleton_partition(instance.counts),
        time_limit=config.time_limit,
        threads=config.threads,
    )
    vehicle_average_delay = (
        vehicle_schedule.objective_average_delay
        if vehicle_schedule.status == "OPTIMAL"
        else None
    )
    for target in config.targets:
        raw_target_c = target_ordering_budget(instance, target)
        target_c = max(
            raw_target_c,
            min_budget_for_max_platoon_size(instance, config.max_platoon_size),
        )

        proposed_result, proposed_partition = solve_partition_proposed(
            instance,
            target_c,
            config.max_platoon_size,
            config.time_limit,
        )
        rows.append(
            record_method(
                instance,
                scenario,
                replication,
                target,
                target_c,
                raw_target_c,
                "proposed_bound_aware",
                "min_Bidx_under_C_budget",
                proposed_partition,
                proposed_result.end_to_end_seconds or 0.0,
                proposed_result.model_construction_seconds or 0.0,
                proposed_result.runtime_seconds or 0.0,
                vehicle_average_delay,
                vehicle_schedule,
                config,
            )
        )

        fixed_label, fixed_partition, fixed_partition_time, fixed_construction_time, fixed_optimization_time = timed_baseline_partition(
            lambda: choose_largest_feasible_dimension(
                fixed_size_candidates(instance, config.max_platoon_size),
                target_c,
            )
        )
        rows.append(
            record_method(
                instance,
                scenario,
                replication,
                target,
                target_c,
                raw_target_c,
                "fixed_size_closest_dimension",
                fixed_label,
                fixed_partition,
                fixed_partition_time,
                fixed_construction_time,
                fixed_optimization_time,
                vehicle_average_delay,
                vehicle_schedule,
                config,
            )
        )

        threshold_label, threshold_partition, threshold_partition_time, threshold_construction_time, threshold_optimization_time = timed_baseline_partition(
            lambda: choose_largest_feasible_dimension(
                threshold_candidates(instance, config.max_platoon_size),
                target_c,
            )
        )
        rows.append(
            record_method(
                instance,
                scenario,
                replication,
                target,
                target_c,
                raw_target_c,
                "threshold_closest_dimension",
                threshold_label,
                threshold_partition,
                threshold_partition_time,
                threshold_construction_time,
                threshold_optimization_time,
                vehicle_average_delay,
                vehicle_schedule,
                config,
            )
        )

    if include_frontier and is_small_frontier_instance(instance):
        frontier_rows.extend(complete_frontier_rows(instance, scenario, replication, config))
    return rows, frontier_rows


def complete_frontier_rows(
    instance: Instance,
    scenario: Scenario,
    replication: int,
    config: ScalabilityConfig,
) -> list[dict[str, object]]:
    c0 = vehicle_level_ordering_variables(instance.counts)
    min_c = min_budget_for_max_platoon_size(instance, config.max_platoon_size)
    rows: list[dict[str, object]] = []
    last_pair: tuple[int | None, int | None] = (None, None)
    if is_small_frontier_instance(instance):
        budgets = range(min_c, c0 + 1)
    else:
        budgets = sampled_budgets(min_c, c0, config.frontier_budget_count)
    for budget in budgets:
        result = solve_size_budget(
            instance,
            budget,
            max_platoon_size=config.max_platoon_size,
            solver="gurobi",
            time_limit=config.time_limit,
        )
        if result.partition is None:
            continue
        metrics = partition_metrics(instance, result.partition)
        pair = (metrics.ordering_variables, metrics.scaled_indexed_bound)
        if pair == last_pair:
            continue
        last_pair = pair
        rows.append(
            {
                "scenario": scenario.name,
                "replication": replication,
                "N": instance.N,
                "L": instance.L,
                "ordering_budget": budget,
                "ordering_variables": metrics.ordering_variables,
                "vehicle_level_ordering_variables": metrics.vehicle_level_ordering_variables,
                "dimension_reduction_fraction": float(metrics.dimension_reduction_fraction),
                "scaled_indexed_bound": metrics.scaled_indexed_bound,
                "indexed_bound": float(Fraction(metrics.scaled_indexed_bound, instance.N)),
                "partition": partition_label(result.partition),
                "partition_time_seconds": result.end_to_end_seconds,
            }
        )
    return rows


def mean_ci95(values: list[float]) -> tuple[float | None, float | None]:
    if not values:
        return None, None
    mean = statistics.fmean(values)
    if len(values) < 2:
        return mean, 0.0
    return mean, 1.96 * statistics.stdev(values) / (len(values) ** 0.5)


def summarize(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    groups: dict[tuple[object, ...], list[dict[str, object]]] = {}
    for row in rows:
        key = (
            row["N"],
            row["L"],
            row["demand_pattern"],
            row["arrival_mode"],
            row["target_dimension_reduction"],
            row["method_family"],
        )
        groups.setdefault(key, []).append(row)
    summary: list[dict[str, object]] = []
    for key, group in sorted(groups.items()):
        def values(field: str) -> list[float]:
            return [float(row[field]) for row in group if row.get(field) not in (None, "")]

        mean_total, ci_total = mean_ci95(values("end_to_end_seconds"))
        mean_partition, ci_partition = mean_ci95(values("partition_time_seconds"))
        mean_construction, ci_construction = mean_ci95(values("model_construction_seconds"))
        mean_downstream, ci_downstream = mean_ci95(values("downstream_optimization_seconds"))
        mean_gap, ci_gap = mean_ci95(values("actual_average_gap"))
        mean_bound, ci_bound = mean_ci95(values("indexed_bound"))
        mean_c, ci_c = mean_ci95(values("ordering_variables"))
        mean_nodes, ci_nodes = mean_ci95(values("nodes"))
        actual_gap_case_count = sum(1 for row in group if row.get("actual_average_gap") is not None)
        all_actual_gaps_within_bound: str | bool
        if actual_gap_case_count == 0:
            all_actual_gaps_within_bound = "N/A"
        else:
            all_actual_gaps_within_bound = all(
                bool(row["actual_gap_le_indexed_bound"])
                for row in group
                if row.get("actual_average_gap") is not None
            )
        summary.append(
            {
                "N": key[0],
                "L": key[1],
                "demand_pattern": key[2],
                "arrival_mode": key[3],
                "target_dimension_reduction": key[4],
                "method_family": key[5],
                "cases": len(group),
                "mean_end_to_end_seconds": mean_total,
                "ci95_end_to_end_seconds": ci_total,
                "mean_partition_time_seconds": mean_partition,
                "ci95_partition_time_seconds": ci_partition,
                "mean_model_construction_seconds": mean_construction,
                "ci95_model_construction_seconds": ci_construction,
                "mean_downstream_optimization_seconds": mean_downstream,
                "ci95_downstream_optimization_seconds": ci_downstream,
                "mean_actual_average_gap": mean_gap,
                "ci95_actual_average_gap": ci_gap,
                "mean_indexed_bound": mean_bound,
                "ci95_indexed_bound": ci_bound,
                "mean_ordering_variables": mean_c,
                "ci95_ordering_variables": ci_c,
                "mean_nodes": mean_nodes,
                "ci95_nodes": ci_nodes,
                "actual_gap_case_count": actual_gap_case_count,
                "statuses": json.dumps(
                    {status: sum(1 for row in group if row["status"] == status) for status in sorted({row["status"] for row in group})},
                    sort_keys=True,
                ),
                "all_actual_gaps_within_bound": all_actual_gaps_within_bound,
            }
        )
    return summary


def vehicle_level_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    dedup: dict[tuple[object, ...], dict[str, object]] = {}
    for row in rows:
        key = (
            row["scenario"],
            row["replication"],
            row["N"],
            row["L"],
            row["demand_pattern"],
            row["arrival_mode"],
            row["hF"],
            row["hS"],
        )
        dedup.setdefault(
            key,
            {
                "scenario": row["scenario"],
                "replication": row["replication"],
                "N": row["N"],
                "L": row["L"],
                "counts": row["counts"],
                "demand_pattern": row["demand_pattern"],
                "arrival_mode": row["arrival_mode"],
                "hF": row["hF"],
                "hS": row["hS"],
                "max_platoon_size": row["max_platoon_size"],
                "vehicle_level_ordering_variables": row["vehicle_level_ordering_variables"],
                "vehicle_level_average_delay": row["vehicle_level_average_delay"],
                "vehicle_level_incumbent_average_delay": row.get(
                    "vehicle_level_incumbent_average_delay",
                    row.get("vehicle_level_average_delay"),
                ),
                "vehicle_level_status": row["vehicle_level_status"],
                "vehicle_level_mip_gap": row["vehicle_level_mip_gap"],
                "vehicle_level_nodes": row["vehicle_level_nodes"],
                "vehicle_level_time_to_first_feasible": row["vehicle_level_time_to_first_feasible"],
                "vehicle_level_model_construction_seconds": row["vehicle_level_model_construction_seconds"],
                "vehicle_level_downstream_optimization_seconds": row["vehicle_level_downstream_optimization_seconds"],
                "vehicle_level_wall_time_seconds": row["vehicle_level_wall_time_seconds"],
            },
        )
    return sorted(dedup.values(), key=lambda item: (str(item["scenario"]), int(item["replication"])))


def summarize_vehicle_level(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    unique_rows = vehicle_level_rows(rows)
    groups: dict[tuple[object, ...], list[dict[str, object]]] = {}
    for row in unique_rows:
        key = (
            row["N"],
            row["L"],
            row["demand_pattern"],
            row["arrival_mode"],
            row["hS"],
        )
        groups.setdefault(key, []).append(row)

    summary: list[dict[str, object]] = []
    for key, group in sorted(groups.items()):
        def values(field: str) -> list[float]:
            return [float(row[field]) for row in group if row.get(field) not in (None, "")]

        mean_delay, ci_delay = mean_ci95(values("vehicle_level_average_delay"))
        mean_incumbent_delay, ci_incumbent_delay = mean_ci95(values("vehicle_level_incumbent_average_delay"))
        mean_gap, ci_gap = mean_ci95(values("vehicle_level_mip_gap"))
        mean_nodes, ci_nodes = mean_ci95(values("vehicle_level_nodes"))
        mean_construction, ci_construction = mean_ci95(values("vehicle_level_model_construction_seconds"))
        mean_runtime, ci_runtime = mean_ci95(values("vehicle_level_downstream_optimization_seconds"))
        mean_total, ci_total = mean_ci95(values("vehicle_level_wall_time_seconds"))
        summary.append(
            {
                "N": key[0],
                "L": key[1],
                "demand_pattern": key[2],
                "arrival_mode": key[3],
                "hS": key[4],
                "cases": len(group),
                "optimal_case_count": sum(1 for row in group if row["vehicle_level_status"] == "OPTIMAL"),
                "mean_vehicle_level_average_delay": mean_delay,
                "ci95_vehicle_level_average_delay": ci_delay,
                "mean_vehicle_level_incumbent_average_delay": mean_incumbent_delay,
                "ci95_vehicle_level_incumbent_average_delay": ci_incumbent_delay,
                "mean_vehicle_level_mip_gap": mean_gap,
                "ci95_vehicle_level_mip_gap": ci_gap,
                "mean_vehicle_level_nodes": mean_nodes,
                "ci95_vehicle_level_nodes": ci_nodes,
                "mean_vehicle_level_model_construction_seconds": mean_construction,
                "ci95_vehicle_level_model_construction_seconds": ci_construction,
                "mean_vehicle_level_downstream_optimization_seconds": mean_runtime,
                "ci95_vehicle_level_downstream_optimization_seconds": ci_runtime,
                "mean_vehicle_level_wall_time_seconds": mean_total,
                "ci95_vehicle_level_wall_time_seconds": ci_total,
                "statuses": json.dumps(
                    {
                        status: sum(1 for row in group if row["vehicle_level_status"] == status)
                        for status in sorted({row["vehicle_level_status"] for row in group})
                    },
                    sort_keys=True,
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


def run(config: ScalabilityConfig) -> dict[str, object]:
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    frontier_rows: list[dict[str, object]] = []
    scenario_list = scenarios(config)

    def write_current_outputs() -> dict[str, object]:
        summary = summarize(rows)
        vehicle_summary = summarize_vehicle_level(rows)
        payload = {
            "config": asdict(config),
            "scenarios": [asdict(scenario) for scenario in scenario_list],
            "rows": rows,
            "frontier_rows": frontier_rows,
            "summary": summary,
            "vehicle_level_summary": vehicle_summary,
        }
        (output_dir / "scalability_suite.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
        write_csv(output_dir / "fair_dimension_comparison.csv", rows)
        write_csv(output_dir / "complete_frontier.csv", frontier_rows)
        write_csv(output_dir / "summary.csv", summary)
        write_csv(output_dir / "vehicle_level_summary.csv", vehicle_summary)
        return payload

    for scenario_index, scenario in enumerate(scenario_list):
        for replication in range(config.reps_per_cell):
            instance, _ = instance_for_replication(scenario, replication, config.seed)
            rep_rows, rep_frontier_rows = run_replication(
                instance,
                scenario,
                replication,
                config,
                include_frontier=len(frontier_rows) < config.frontier_instance_limit,
            )
            rows.extend(rep_rows)
            frontier_rows.extend(rep_frontier_rows)
        print(f"completed {scenario_index + 1}/{len(scenario_list)} {scenario.name}", flush=True)
        write_current_outputs()

    return write_current_outputs()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=20260710)
    parser.add_argument("--reps-per-cell", type=int, default=1)
    parser.add_argument("--n-values", default="20,30,40,60")
    parser.add_argument("--l-values", default="3,4")
    parser.add_argument("--demand-patterns", default="balanced,unbalanced")
    parser.add_argument("--arrival-modes", default="uniform,poisson,bursty")
    parser.add_argument("--targets", default="0.25,0.5,0.75,0.9")
    parser.add_argument("--hF", type=int, default=1)
    parser.add_argument("--hS-values", default="2")
    parser.add_argument("--max-platoon-size", type=int, default=4)
    parser.add_argument("--time-limit", type=float, default=30.0)
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("--frontier-instance-limit", type=int, default=2)
    parser.add_argument("--frontier-budget-count", type=int, default=12)
    parser.add_argument("--output-dir", default="../../results/frontier_experiments/scalability_pilot")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    config = ScalabilityConfig(
        seed=args.seed,
        reps_per_cell=args.reps_per_cell,
        n_values=parse_int_tuple(args.n_values),
        l_values=parse_int_tuple(args.l_values),
        demand_patterns=tuple(part.strip() for part in args.demand_patterns.split(",") if part.strip()),
        arrival_modes=tuple(part.strip() for part in args.arrival_modes.split(",") if part.strip()),
        targets=parse_float_tuple(args.targets),
        hF=args.hF,
        hS_values=parse_int_tuple(args.hS_values),
        max_platoon_size=args.max_platoon_size,
        time_limit=args.time_limit,
        threads=args.threads,
        output_dir=args.output_dir,
        frontier_instance_limit=args.frontier_instance_limit,
        frontier_budget_count=args.frontier_budget_count,
    )
    started = time.perf_counter()
    payload = run(config)
    print(json.dumps({
        "output_dir": args.output_dir,
        "scenarios": len(payload["scenarios"]),
        "rows": len(payload["rows"]),
        "frontier_rows": len(payload["frontier_rows"]),
        "summary_rows": len(payload["summary"]),
        "wall_time_seconds": time.perf_counter() - started,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
