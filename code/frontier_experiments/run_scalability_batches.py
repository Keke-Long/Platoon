"""Run scalability experiments as independent scenario batches."""

from __future__ import annotations

import argparse
import itertools
import json
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class Batch:
    n: int
    l_value: int
    demand_pattern: str
    arrival_mode: str
    hS: int

    @property
    def name(self) -> str:
        return f"N{self.n}_L{self.l_value}_{self.demand_pattern}_{self.arrival_mode}_hS{self.hS}"


def parse_int_tuple(value: str) -> tuple[int, ...]:
    return tuple(int(part.strip()) for part in value.split(",") if part.strip())


def parse_str_tuple(value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in value.split(",") if part.strip())


def batches(args: argparse.Namespace) -> list[Batch]:
    return [
        Batch(n, l_value, demand, arrival, hS)
        for n, l_value, demand, arrival, hS in itertools.product(
            parse_int_tuple(args.n_values),
            parse_int_tuple(args.l_values),
            parse_str_tuple(args.demand_patterns),
            parse_str_tuple(args.arrival_modes),
            parse_int_tuple(args.hS_values),
        )
    ]


def run_batch(batch: Batch, args: argparse.Namespace) -> dict[str, object]:
    batch_dir = Path(args.output_dir) / "batches" / batch.name
    summary_path = batch_dir / "scalability_suite.json"
    if args.resume and summary_path.exists():
        return {
            "batch": asdict(batch),
            "batch_name": batch.name,
            "status": "SKIPPED_EXISTING",
            "output_dir": str(batch_dir),
        }

    command = [
        sys.executable,
        "scalability_suite.py",
        "--n-values",
        str(batch.n),
        "--l-values",
        str(batch.l_value),
        "--demand-patterns",
        batch.demand_pattern,
        "--arrival-modes",
        batch.arrival_mode,
        "--hS-values",
        str(batch.hS),
        "--targets",
        args.targets,
        "--reps-per-cell",
        str(args.reps_per_cell),
        "--time-limit",
        str(args.time_limit),
        "--threads",
        str(args.threads),
        "--frontier-instance-limit",
        str(args.frontier_instance_limit),
        "--seed",
        str(args.seed),
        "--output-dir",
        str(batch_dir),
    ]
    started = time.perf_counter()
    proc = subprocess.run(command, cwd=Path(__file__).resolve().parent, text=True)
    elapsed = time.perf_counter() - started
    return {
        "batch": asdict(batch),
        "batch_name": batch.name,
        "status": "DONE" if proc.returncode == 0 else f"FAILED_{proc.returncode}",
        "returncode": proc.returncode,
        "wall_time_seconds": elapsed,
        "output_dir": str(batch_dir),
    }


def write_manifest(output_dir: Path, rows: list[dict[str, object]]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "batch_manifest.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=20260710)
    parser.add_argument("--n-values", default="20,30,40,60")
    parser.add_argument("--l-values", default="3,4")
    parser.add_argument("--demand-patterns", default="balanced,unbalanced")
    parser.add_argument("--arrival-modes", default="uniform,poisson,bursty")
    parser.add_argument("--hS-values", default="2")
    parser.add_argument("--targets", default="0.25,0.5,0.75,0.9")
    parser.add_argument("--reps-per-cell", type=int, default=30)
    parser.add_argument("--time-limit", type=float, default=30.0)
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("--frontier-instance-limit", type=int, default=1)
    parser.add_argument("--output-dir", default="../../results/frontier_experiments/scalability_full_wls")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--limit", type=int, help="run only the first N batches")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    output_dir = Path(args.output_dir)
    rows: list[dict[str, object]] = []
    all_batches = batches(args)
    if args.limit is not None:
        all_batches = all_batches[: args.limit]
    for index, batch in enumerate(all_batches, start=1):
        print(f"batch {index}/{len(all_batches)} {batch.name}", flush=True)
        result = run_batch(batch, args)
        rows.append(result)
        write_manifest(output_dir, rows)
        print(json.dumps(result, sort_keys=True), flush=True)
        if str(result["status"]).startswith("FAILED"):
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

