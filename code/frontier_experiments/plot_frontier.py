"""Plot a dimension-loss frontier from frontier_driver.py output."""

from __future__ import annotations

import argparse
import json
import os
from fractions import Fraction
from pathlib import Path

FIGSIZE = (4.8, 3.2)
LABEL_FONTSIZE = 11
TICK_FONTSIZE = 10
LEGEND_FONTSIZE = 11
GRID_ALPHA = 0.24

BOUND_COLOR = "#6B8F7C"
BOUND_MARKER = "#B7CDBE"
ACTUAL_COLOR = "#9A6A5C"
ACTUAL_MARKER = "#D4B4A7"
REFERENCE_COLOR = "#7A7F87"

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

    fig, ax = plt.subplots(figsize=FIGSIZE)
    ax.plot(
        x_values,
        bound_values,
        marker="o",
        markersize=5.2,
        markerfacecolor=BOUND_MARKER,
        markeredgecolor=BOUND_COLOR,
        color=BOUND_COLOR,
        linewidth=1.9,
        label="Indexed loss bound",
    )
    if all(value is not None for value in actual_values):
        ax.plot(
            x_values,
            [float(value) for value in actual_values],
            marker="s",
            markersize=5.0,
            markerfacecolor=ACTUAL_MARKER,
            markeredgecolor=ACTUAL_COLOR,
            color=ACTUAL_COLOR,
            linewidth=1.7,
            label="Actual optimality gap",
        )
    ax.axvline(c0, color=REFERENCE_COLOR, linestyle="--", linewidth=1.0, label="Vehicle-level dimension")
    ax.set_xlabel("Ordering variables C(Pi)", fontsize=LABEL_FONTSIZE)
    ax.set_ylabel("Average delay loss", fontsize=LABEL_FONTSIZE)
    ax.tick_params(axis="both", labelsize=TICK_FONTSIZE)
    ax.grid(True, linewidth=0.5, alpha=GRID_ALPHA)
    ax.legend(frameon=False, fontsize=LEGEND_FONTSIZE)
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=300)
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
