"""Run a single scalability scenario in checkpointed repetition chunks."""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict
from pathlib import Path

from scalability_suite import (  # noqa: E402
    ScalabilityConfig,
    Scenario,
    complete_frontier_rows,
    counts_for,
    instance_for_replication,
    run_replication,
    summarize,
    summarize_vehicle_level,
    write_csv,
)


def parse_float_tuple(value: str) -> tuple[float, ...]:
    return tuple(float(part.strip()) for part in value.split(",") if part.strip())


def chunk_name(rep_start: int, rep_end: int) -> str:
    return f"rep_{rep_start:03d}_{rep_end:03d}"


def rep_path(output_dir: Path, replication: int) -> Path:
    return output_dir / "reps" / f"rep_{replication:03d}.json"


def load_rep_payloads(output_dir: Path) -> list[dict[str, object]]:
    payloads: list[dict[str, object]] = []
    for path in sorted((output_dir / "reps").glob("rep_*.json")):
        payloads.append(json.loads(path.read_text(encoding="utf-8")))
    return payloads


def write_outputs(
    output_dir: Path,
    config: ScalabilityConfig,
    scenario: Scenario,
    rep_start: int,
    rep_end: int,
) -> dict[str, object]:
    rep_payloads = load_rep_payloads(output_dir)
    rows = [row for payload in rep_payloads for row in payload["rows"]]
    frontier_rows = [row for payload in rep_payloads for row in payload.get("frontier_rows", [])]
    summary = summarize(rows)
    vehicle_summary = summarize_vehicle_level(rows)
    manifest = {
        "config": asdict(config),
        "scenario": asdict(scenario),
        "rep_start": rep_start,
        "rep_end": rep_end,
        "expected_replications": list(range(rep_start, rep_end + 1)),
        "completed_replications": [payload["replication"] for payload in rep_payloads],
        "completed_rep_count": len(rep_payloads),
        "rows": len(rows),
        "frontier_rows": len(frontier_rows),
        "summary_rows": len(summary),
        "vehicle_level_summary_rows": len(vehicle_summary),
    }
    payload = {
        "config": asdict(config),
        "scenario": asdict(scenario),
        "rep_start": rep_start,
        "rep_end": rep_end,
        "replications": rep_payloads,
        "rows": rows,
        "frontier_rows": frontier_rows,
        "summary": summary,
        "vehicle_level_summary": vehicle_summary,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "chunk_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (output_dir / "scalability_chunk.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_csv(output_dir / "fair_dimension_comparison.csv", rows)
    write_csv(output_dir / "complete_frontier.csv", frontier_rows)
    write_csv(output_dir / "summary.csv", summary)
    write_csv(output_dir / "vehicle_level_summary.csv", vehicle_summary)
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=20260710)
    parser.add_argument("--n", type=int, required=True)
    parser.add_argument("--l", type=int, required=True)
    parser.add_argument("--demand-pattern", required=True)
    parser.add_argument("--arrival-mode", required=True)
    parser.add_argument("--hF", type=int, default=1)
    parser.add_argument("--hS", type=int, default=2)
    parser.add_argument("--targets", default="0.25,0.5,0.75,0.9")
    parser.add_argument("--time-limit", type=float, default=30.0)
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("--max-platoon-size", type=int, default=4)
    parser.add_argument("--frontier-instance-limit", type=int, default=1)
    parser.add_argument("--frontier-budget-count", type=int, default=12)
    parser.add_argument("--rep-start", type=int, required=True)
    parser.add_argument("--rep-end", type=int, required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--resume", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.rep_start < 0 or args.rep_end < args.rep_start:
        raise ValueError("invalid repetition range")
    scenario = Scenario(
        name=f"N{args.n}_L{args.l}_{args.demand_pattern}_{args.arrival_mode}_hS{args.hS}",
        counts=counts_for(args.n, args.l, args.demand_pattern),
        demand_pattern=args.demand_pattern,
        arrival_mode=args.arrival_mode,
        hF=args.hF,
        hS=args.hS,
        max_release=max(10, 2 * args.n),
    )
    config = ScalabilityConfig(
        seed=args.seed,
        reps_per_cell=args.rep_end - args.rep_start + 1,
        n_values=(args.n,),
        l_values=(args.l,),
        demand_patterns=(args.demand_pattern,),
        arrival_modes=(args.arrival_mode,),
        targets=parse_float_tuple(args.targets),
        hF=args.hF,
        hS_values=(args.hS,),
        max_platoon_size=args.max_platoon_size,
        time_limit=args.time_limit,
        threads=args.threads,
        output_dir=args.output_dir,
        frontier_instance_limit=args.frontier_instance_limit,
        frontier_budget_count=args.frontier_budget_count,
    )
    output_dir = Path(args.output_dir)
    (output_dir / "reps").mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    completed = 0
    skipped = 0
    for replication in range(args.rep_start, args.rep_end + 1):
        destination = rep_path(output_dir, replication)
        if args.resume and destination.exists():
            skipped += 1
            continue
        instance, instance_seed = instance_for_replication(scenario, replication, args.seed)
        rep_started = time.perf_counter()
        rep_rows, rep_frontier_rows = run_replication(
            instance,
            scenario,
            replication,
            config,
            include_frontier=args.frontier_instance_limit > 0 and not any((output_dir / "reps").glob("rep_*.json")),
        )
        payload = {
            "replication": replication,
            "instance_seed": instance_seed,
            "scenario": asdict(scenario),
            "rows": rep_rows,
            "frontier_rows": rep_frontier_rows,
            "wall_time_seconds": time.perf_counter() - rep_started,
        }
        destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        completed += 1
        manifest = write_outputs(output_dir, config, scenario, args.rep_start, args.rep_end)
        print(
            json.dumps(
                {
                    "replication": replication,
                    "instance_seed": instance_seed,
                    "completed_rep_count": manifest["completed_rep_count"],
                    "rows": manifest["rows"],
                    "wall_time_seconds": payload["wall_time_seconds"],
                },
                sort_keys=True,
            ),
            flush=True,
        )
    manifest = write_outputs(output_dir, config, scenario, args.rep_start, args.rep_end)
    print(
        json.dumps(
            {
                "output_dir": args.output_dir,
                "scenario": scenario.name,
                "rep_start": args.rep_start,
                "rep_end": args.rep_end,
                "completed": completed,
                "skipped": skipped,
                "completed_rep_count": manifest["completed_rep_count"],
                "rows": manifest["rows"],
                "summary_rows": manifest["summary_rows"],
                "vehicle_level_summary_rows": manifest["vehicle_level_summary_rows"],
                "wall_time_seconds": time.perf_counter() - started,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
