from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from aggregate_scalability_chunks import aggregate  # noqa: E402
from scalability_suite import Scenario, instance_for_replication, replication_seed  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]


def test_replication_seed_and_instance_are_deterministic() -> None:
    scenario = Scenario(
        name="N30_L4_balanced_poisson_hS2",
        counts=(8, 8, 7, 7),
        demand_pattern="balanced",
        arrival_mode="poisson",
        hF=1,
        hS=2,
        max_release=60,
    )
    seed_a = replication_seed(20260710, scenario, 7)
    seed_b = replication_seed(20260710, scenario, 7)
    seed_c = replication_seed(20260710, scenario, 8)
    instance_a, _ = instance_for_replication(scenario, 7, 20260710)
    instance_b, _ = instance_for_replication(scenario, 7, 20260710)
    assert seed_a == seed_b
    assert seed_a != seed_c
    assert instance_a.releases == instance_b.releases


def test_chunk_runner_resume_and_aggregate() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        scenario_root = Path(tmpdir) / "scenario"
        chunk_dir = scenario_root / "chunks" / "rep_000_001"
        command = [
            sys.executable,
            "scalability_chunk_runner.py",
            "--n",
            "8",
            "--l",
            "4",
            "--demand-pattern",
            "balanced",
            "--arrival-mode",
            "poisson",
            "--hS",
            "2",
            "--rep-start",
            "0",
            "--rep-end",
            "1",
            "--time-limit",
            "5",
            "--threads",
            "1",
            "--output-dir",
            str(chunk_dir),
            "--resume",
        ]
        subprocess.run(command, cwd=ROOT, check=True)
        subprocess.run(command, cwd=ROOT, check=True)

        checks = aggregate(scenario_root, expected_reps=2)
        assert checks["replication_count"] == 2
        assert checks["duplicate_replications"] == []
        assert checks["missing_replications"] == []
        assert checks["budget_violation_count"] == 0
        assert checks["actual_gap_violation_count"] == 0

        rep_paths = sorted((chunk_dir / "reps").glob("rep_*.json"))
        assert len(rep_paths) == 2
        payload = json.loads((chunk_dir / "chunk_manifest.json").read_text(encoding="utf-8"))
        assert payload["completed_rep_count"] == 2
