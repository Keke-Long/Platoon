"""Aggregate checkpointed scalability chunk outputs for a single scenario."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

from scalability_suite import summarize, summarize_vehicle_level, write_csv  # noqa: E402


EXPECTED_METHODS_PER_TARGET = 3


def read_chunk(chunk_dir: Path) -> dict[str, object]:
    return json.loads((chunk_dir / "scalability_chunk.json").read_text(encoding="utf-8"))


def aggregate(root: Path, expected_reps: int | None = None) -> dict[str, object]:
    chunk_dirs = sorted(path for path in (root / "chunks").glob("*") if path.is_dir())
    if not chunk_dirs:
        raise ValueError(f"no chunk directories found under {root / 'chunks'}")

    chunk_payloads = [read_chunk(path) for path in chunk_dirs]
    scenario_blobs = {json.dumps(payload["scenario"], sort_keys=True) for payload in chunk_payloads}
    config_blobs = {json.dumps(payload["config"], sort_keys=True) for payload in chunk_payloads}
    rep_payloads: dict[int, dict[str, object]] = {}
    duplicate_replications: list[int] = []
    duplicate_instance_seeds: list[int] = []
    seen_instance_seeds: set[int] = set()
    rows: list[dict[str, object]] = []
    frontier_rows: list[dict[str, object]] = []

    for payload in chunk_payloads:
        for rep_payload in payload["replications"]:
            replication = int(rep_payload["replication"])
            if replication in rep_payloads:
                duplicate_replications.append(replication)
            rep_payloads[replication] = rep_payload
            instance_seed = int(rep_payload["instance_seed"])
            if instance_seed in seen_instance_seeds:
                duplicate_instance_seeds.append(instance_seed)
            seen_instance_seeds.add(instance_seed)
            rows.extend(rep_payload["rows"])
            frontier_rows.extend(rep_payload.get("frontier_rows", []))

    sorted_replications = sorted(rep_payloads)
    missing_replications: list[int] = []
    if expected_reps is not None:
        expected = list(range(expected_reps))
        missing_replications = [rep for rep in expected if rep not in rep_payloads]

    methods_per_rep = {
        replication: len(rep_payloads[replication]["rows"])
        for replication in sorted_replications
    }
    targets_per_rep = {
        replication: len({row["target_dimension_reduction"] for row in rep_payloads[replication]["rows"]})
        for replication in sorted_replications
    }
    expected_rows_per_rep = {
        replication: targets_per_rep[replication] * EXPECTED_METHODS_PER_TARGET
        for replication in sorted_replications
    }
    bad_method_counts = {
        replication: methods_per_rep[replication]
        for replication in sorted_replications
        if methods_per_rep[replication] != expected_rows_per_rep[replication]
    }

    budget_violations = [
        row for row in rows
        if int(row["ordering_variables"]) > int(row["target_ordering_budget"])
    ]
    actual_gap_violations = [
        row for row in rows
        if row.get("actual_average_gap") not in (None, "")
        and not bool(row.get("actual_gap_le_indexed_bound"))
    ]

    row_status_counts = Counter(str(row["status"]) for row in rows)
    vehicle_status_counts = Counter(str(row["vehicle_level_status"]) for row in rows)
    rows_by_rep = Counter(int(row["replication"]) for row in rows)

    summary = summarize(rows)
    vehicle_level_summary = summarize_vehicle_level(rows)

    output_payload = {
        "scenario": json.loads(next(iter(scenario_blobs))),
        "config_count": len(config_blobs),
        "chunk_count": len(chunk_dirs),
        "replication_count": len(sorted_replications),
        "replications": sorted_replications,
        "missing_replications": missing_replications,
        "duplicate_replications": sorted(set(duplicate_replications)),
        "duplicate_instance_seeds": sorted(set(duplicate_instance_seeds)),
        "methods_per_rep": methods_per_rep,
        "expected_rows_per_rep": expected_rows_per_rep,
        "bad_method_counts": bad_method_counts,
        "rows_by_rep": dict(rows_by_rep),
        "row_count": len(rows),
        "frontier_row_count": len(frontier_rows),
        "summary_row_count": len(summary),
        "vehicle_level_summary_row_count": len(vehicle_level_summary),
        "budget_violation_count": len(budget_violations),
        "actual_gap_violation_count": len(actual_gap_violations),
        "row_status_counts": dict(row_status_counts),
        "vehicle_status_counts": dict(vehicle_status_counts),
    }

    write_csv(root / "fair_dimension_comparison.csv", rows)
    write_csv(root / "complete_frontier.csv", frontier_rows)
    write_csv(root / "summary.csv", summary)
    write_csv(root / "vehicle_level_summary.csv", vehicle_level_summary)
    (root / "aggregate_checks.json").write_text(json.dumps(output_payload, indent=2), encoding="utf-8")
    return output_payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--expected-reps", type=int)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    print(json.dumps(aggregate(args.root, expected_reps=args.expected_reps), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
