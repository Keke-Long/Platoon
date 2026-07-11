"""Plot a dimension-loss frontier from frontier_driver.py output."""

from __future__ import annotations

import argparse
import json
import os
from fractions import Fraction
from pathlib import Path


def parse_fraction(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, int | float):
        return float(value)
    text = str(value)
    if "/" in text:
        numerator, denominator = text.split("/", maxsplit=1)
        return float(Fraction(int(numerator), int(denominator)))
    return float(text)


def load_payload(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def plot_frontier(input_path: Path, output_path: Path) -> None:
    os.environ.setdefault("MPLCONFIGDIR", str(output_path.parent / ".mplconfig"))
    import matplotlib.pyplot as plt

    payload = load_payload(input_path)
    pareto = payload["pareto_frontier"]
    if not isinstance(pareto, list) or not pareto:
        raise ValueError("frontier input contains no pareto_frontier rows")

    rows = sorted(
        pareto,
        key=lambda row: (
            int(row["ordering_variables"]),
            int(row["scaled_indexed_bound"]),
        ),
    )
    n = int(payload["N"])
    c0 = int(payload["vehicle_level_ordering_variables"])
    x_values = [int(row["ordering_variables"]) for row in rows]
    bound_values = [int(row["scaled_indexed_bound"]) / n for row in rows]
    actual_values = [
        parse_fraction(row.get("actual_average_gap")) if isinstance(row, dict) else None
        for row in rows
    ]

    fig, ax = plt.subplots(figsize=(6.2, 4.1))
    ax.plot(x_values, bound_values, marker="o", linewidth=1.8, label="Indexed loss bound")
    if all(value is not None for value in actual_values):
        ax.plot(
            x_values,
            [float(value) for value in actual_values],
            marker="s",
            linewidth=1.4,
            label="Actual optimality gap",
        )
    ax.axvline(c0, color="0.35", linestyle="--", linewidth=1.0, label="Vehicle-level dimension")
    ax.set_xlabel("Ordering variables C(Pi)")
    ax.set_ylabel("Average delay loss")
    ax.set_title("Dimension-loss frontier")
    ax.grid(True, linewidth=0.4, alpha=0.4)
    ax.legend(frameon=False)
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=200)
    plt.close(fig)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="path to frontier.json")
    parser.add_argument("--output", type=Path, default=Path("frontier.png"))
    return parser


def main() -> int:
    args = build_parser().parse_args()
    plot_frontier(args.input, args.output)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

