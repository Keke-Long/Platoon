"""Aggregate independent scalability batch outputs."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


FILES = (
    "fair_dimension_comparison.csv",
    "complete_frontier.csv",
    "summary.csv",
)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
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
        writer.writerows(rows)


def aggregate(root: Path) -> dict[str, object]:
    batch_dirs = sorted((root / "batches").glob("*"))
    outputs: dict[str, list[dict[str, str]]] = {name: [] for name in FILES}
    batch_status = []
    for batch_dir in batch_dirs:
        if not batch_dir.is_dir():
            continue
        payload_path = batch_dir / "scalability_suite.json"
        status = "MISSING"
        if payload_path.exists():
            payload = json.loads(payload_path.read_text(encoding="utf-8"))
            status = "DONE"
            batch_status.append(
                {
                    "batch": batch_dir.name,
                    "rows": len(payload.get("rows", [])),
                    "frontier_rows": len(payload.get("frontier_rows", [])),
                    "summary_rows": len(payload.get("summary", [])),
                    "status": status,
                }
            )
        else:
            batch_status.append({"batch": batch_dir.name, "status": status})
        for filename in FILES:
            for row in read_csv(batch_dir / filename):
                row["batch"] = batch_dir.name
                outputs[filename].append(row)

    for filename, rows in outputs.items():
        write_csv(root / filename, rows)
    result = {
        "batch_count": len(batch_status),
        "batches": batch_status,
        "row_counts": {filename: len(rows) for filename, rows in outputs.items()},
    }
    (root / "aggregate_manifest.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    print(json.dumps(aggregate(args.root), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

