"""Run the complete uniform-600-second formal experiment campaign.

The campaign is restartable. It adopts already running workers, waits for them
to finish, and launches only replication ranges whose checkpoints are missing.
At most eight worker processes are active at once.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Iterable


HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
RESULT_ROOT = REPO_ROOT / "results" / "rule_based_experiments"
COMPARISON_DIR = RESULT_ROOT / "formal_pp_hS3_600s_r10"
BOUND_DIR = RESULT_ROOT / "formal_bound_hS3_600s_r10"
FIGURE_DIR = RESULT_ROOT / "formal_figures_hS3_600s_r10"
CHECKPOINT_DIR = COMPARISON_DIR / "checkpoints"
LOG_DIR = COMPARISON_DIR / "campaign_logs"
STATUS_PATH = COMPARISON_DIR / "campaign_status.json"

RATES = (0.5, 1.0, 1.5, 2.0, 2.5)
MISSING_LEGACY_RATES = (0.5, 1.0, 2.0)
LEGACY_RATES = (1.5, 2.5)
SCALES = (20, 40, 60, 80)
MAX_WORKERS = 8


def rate_label(rate: float) -> str:
    return f"{rate:g}".replace(".", "p")


def checkpoint_path(n_value: int, rate: float, replication: int) -> Path:
    return CHECKPOINT_DIR / f"N{n_value}_lambda{rate_label(rate)}_rep{replication:03d}.json"


def missing_checkpoints(n_value: int, rates: Iterable[float]) -> list[Path]:
    return [
        checkpoint_path(n_value, rate, replication)
        for rate in rates
        for replication in range(10)
        if not checkpoint_path(n_value, rate, replication).exists()
    ]


def write_status(current_stage: str, scales: dict[str, str], **details: Any) -> None:
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "design": {
            "N": list(SCALES),
            "total_arrival_rates": list(RATES),
            "replications": 10,
            "time_limit_seconds": 600,
            "worker_processes": 8,
            "gurobi_threads_per_solve": 12,
        },
        "current_stage": current_stage,
        "scales": scales,
        "updated_at_unix": time.time(),
        **details,
    }
    temporary = STATUS_PATH.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    temporary.replace(STATUS_PATH)


def active_worker_count(script_name: str, n_value: int) -> int:
    result = subprocess.run(
        ["ps", "-eo", "args="],
        check=True,
        capture_output=True,
        text=True,
    )
    n_token = f"--n-values {n_value}"
    return sum(script_name in line and n_token in line for line in result.stdout.splitlines())


def wait_for_adopted_workers(
    script_name: str,
    n_value: int,
    stage: str,
    scales: dict[str, str],
    poll_seconds: int,
) -> None:
    while (count := active_worker_count(script_name, n_value)) > 0:
        write_status(stage, scales, adopted_worker_processes=count)
        print(f"{stage}: waiting for {count} adopted worker processes", flush=True)
        time.sleep(poll_seconds)


def worker_command(
    script_name: str,
    n_value: int,
    rates: Iterable[float],
    rep_start: int,
    rep_end: int,
) -> list[str]:
    command = [
        sys.executable,
        str(HERE / script_name),
        "--n-values",
        str(n_value),
        "--arrival-rates",
        ",".join(f"{rate:g}" for rate in rates),
        "--reps",
        "10",
        "--rep-start",
        str(rep_start),
        "--rep-end-exclusive",
        str(rep_end),
        "--time-limit",
        "600",
        "--threads",
        "12",
        "--write-trajectory",
        "--resume",
    ]
    if script_name == "rule_based_formal_hs3.py":
        command.append("--checkpoint-only")
    return command


def stage_jobs(
    script_name: str,
    n_value: int,
    rates: tuple[float, ...],
) -> list[tuple[tuple[float, ...], int, int]]:
    if script_name == "migrate_legacy_uniform_results.py":
        ranges = ((0, 3), (3, 6), (6, 8), (8, 10))
    elif n_value == 40:
        ranges = ((0, 4), (4, 7), (7, 10))
    else:
        ranges = ((0, 5), (5, 10))
    return [((rate,), rep_start, rep_end) for rate in rates for rep_start, rep_end in ranges]


def run_worker_group(
    script_name: str,
    n_value: int,
    rates: tuple[float, ...],
    stage: str,
    scales: dict[str, str],
    poll_seconds: int,
) -> None:
    wait_for_adopted_workers(script_name, n_value, stage, scales, poll_seconds)
    if not missing_checkpoints(n_value, rates):
        print(f"{stage}: all checkpoints already exist", flush=True)
        return

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    pending = stage_jobs(script_name, n_value, rates)
    processes: list[tuple[subprocess.Popen[str], Any, str]] = []
    failures: list[tuple[str, int]] = []

    def launch_job(job: tuple[tuple[float, ...], int, int]) -> None:
        job_rates, rep_start, rep_end = job
        command = worker_command(script_name, n_value, job_rates, rep_start, rep_end)
        rate_token = "_".join(rate_label(rate) for rate in job_rates)
        job_name = f"lambda{rate_token}_rep{rep_start:02d}_{rep_end:02d}"
        log_path = LOG_DIR / f"{stage}_{job_name}.log"
        log_handle = log_path.open("a", encoding="utf-8")
        process = subprocess.Popen(
            command,
            cwd=HERE,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            text=True,
        )
        processes.append((process, log_handle, job_name))

    while pending or processes:
        while pending and len(processes) < MAX_WORKERS:
            launch_job(pending.pop(0))
        time.sleep(poll_seconds)
        still_running = []
        for process, log_handle, job_name in processes:
            returncode = process.poll()
            if returncode is None:
                still_running.append((process, log_handle, job_name))
                continue
            log_handle.close()
            if returncode != 0:
                failures.append((job_name, returncode))
        processes = still_running
        missing = len(missing_checkpoints(n_value, rates))
        write_status(
            stage,
            scales,
            running_worker_processes=len(processes),
            pending_worker_jobs=len(pending),
            missing_stage_checkpoints=missing,
        )
        print(
            f"{stage}: workers={len(processes)}, pending_jobs={len(pending)}, missing_checkpoints={missing}",
            flush=True,
        )
    if failures:
        raise RuntimeError(f"{stage}: worker failures={failures}")
    missing = missing_checkpoints(n_value, rates)
    if missing:
        raise RuntimeError(f"{stage}: {len(missing)} checkpoints are still missing")


def aggregate(completed_scales: tuple[int, ...], scales: dict[str, str]) -> dict[str, Any]:
    command = [
        sys.executable,
        str(HERE / "rule_based_formal_hs3.py"),
        "--n-values",
        ",".join(str(value) for value in completed_scales),
        "--arrival-rates",
        ",".join(f"{rate:g}" for rate in RATES),
        "--reps",
        "10",
        "--time-limit",
        "600",
        "--threads",
        "12",
        "--write-trajectory",
        "--resume",
    ]
    subprocess.run(command, cwd=HERE, check=True)
    summary_path = COMPARISON_DIR / "formal_comparison_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    checks = summary["checks"]
    expected_instances = len(completed_scales) * len(RATES) * 10
    expected_rows = expected_instances * 21
    expected_pp_rows = expected_instances * 16
    required = {
        "expected_instance_count": expected_instances,
        "observed_instance_count": expected_instances,
        "expected_initial_row_count": expected_rows,
        "observed_initial_row_count": expected_rows,
        "expected_pp_rows": expected_pp_rows,
        "observed_pp_rows": expected_pp_rows,
        "duplicate_row_key_count": 0,
        "bound_violation_count": 0,
        "delay_order_failure_count": 0,
    }
    mismatches = {key: (checks.get(key), value) for key, value in required.items() if checks.get(key) != value}
    if mismatches:
        raise RuntimeError(f"aggregate validation failed: {mismatches}")
    write_status(f"N={completed_scales[-1]} complete", scales, checks=checks)
    return summary


def run_figures() -> None:
    command = [
        sys.executable,
        str(HERE / "plot_rule_based_formal_hs3.py"),
        "--comparison-dir",
        str(COMPARISON_DIR),
        "--bound-dir",
        str(BOUND_DIR),
        "--output-dir",
        str(FIGURE_DIR),
    ]
    subprocess.run(command, cwd=HERE, check=True, env={**os.environ, "MPLBACKEND": "Agg"})


def planned_commands() -> list[list[str]]:
    commands = []
    for n_value, rates, script_name in (
        (40, LEGACY_RATES, "migrate_legacy_uniform_results.py"),
        (40, MISSING_LEGACY_RATES, "rule_based_formal_hs3.py"),
        (60, RATES, "rule_based_formal_hs3.py"),
        (80, RATES, "rule_based_formal_hs3.py"),
    ):
        for job_rates, rep_start, rep_end in stage_jobs(script_name, n_value, rates):
            commands.append(worker_command(script_name, n_value, job_rates, rep_start, rep_end))
    return commands


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--poll-seconds", type=int, default=30)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.poll_seconds < 1:
        raise ValueError("poll-seconds must be positive")
    if args.dry_run:
        print(json.dumps(planned_commands(), indent=2))
        return 0

    scales = {str(n_value): "pending" for n_value in SCALES}
    if not missing_checkpoints(20, RATES):
        scales["20"] = "complete"

    scales["40"] = "running"
    run_worker_group(
        "migrate_legacy_uniform_results.py",
        40,
        LEGACY_RATES,
        "N40_legacy",
        scales,
        args.poll_seconds,
    )
    run_worker_group(
        "rule_based_formal_hs3.py",
        40,
        MISSING_LEGACY_RATES,
        "N40_new_rates",
        scales,
        args.poll_seconds,
    )
    scales["40"] = "complete"
    aggregate((20, 40), scales)

    for n_value in SCALES[2:]:
        scales[str(n_value)] = "running"
        run_worker_group(
            "rule_based_formal_hs3.py",
            n_value,
            RATES,
            f"N{n_value}_all_rates",
            scales,
            args.poll_seconds,
        )
        scales[str(n_value)] = "complete"
        aggregate(tuple(value for value in SCALES if value <= n_value), scales)

    run_figures()
    write_status("campaign complete", scales)
    print("campaign complete", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
