# Formal hS=3 Experiment Handoff

This document is the operational handoff for the active Chapter 5 experiment pipeline. It should be read with `EXPERIMENT_DESIGN.md`, `../../paper/main.tex`, and `../../paper/sections/experiments.tex`.

## Paper-Level Role

The manuscript studies performance-guaranteed platooning as a preprocessing step for vehicle scheduling at a general conflict area. Gurobi remains the downstream MILP optimizer. The formal hS=3 pipeline evaluates whether the implemented rule-level bound is valid on checkable solved cases and how NP, CHP, and PP trade delay against model size.

The theorem being supported computationally is the FIFO-indexed loss bound in `../../paper/sections/theoretical_analysis.tex`:

```text
0 <= G(Pi) <= Ghat(Pi)
```

The experiments do not prove the theorem; they check the implementation on solved instances and report computation, delay, and dimension-reduction behavior.

## Frozen Formal Grid

```text
L = 4
N = {20, 40, 60, 80}
arrival rates = {0.4, 0.7, 1.0}
hF = 1
hS = 3
delta = {2, 4, 6, 8}
Pmax = {2, 4, 6, 8}
replications = 20
Gurobi threads = 12
initial time limit = 30 seconds
NP recovery time limit = 600 seconds, only when explicitly launched
```

Do not change this grid for paper-facing formal runs.

## Active Files

- `rule_based_formal_hs3.py`: formal NP/CHP/PP runner with checkpoint/resume and append aggregation.
- `plot_rule_based_formal_hs3.py`: paper-facing formal figures A-E.
- `scheduling_milp.py`: downstream Gurobi scheduling model.
- `partition_methods.py`: rule-based NP/CHP/PP partition formation.
- `metrics.py`: ordering-variable and bound utilities.
- `tests/run_tests.py`: local test entry point for the active pipeline.

Archived optimized-frontier, complete-frontier, dimension-budget, and older hS=2 workflows have been removed from the active code path.

## Current Result State

The committed formal aggregate files contain completed initial 30-second runs for `N={20,40}` only. `N=60`, `N=80`, and 600-second NP recovery are not present in the committed formal aggregates.

Expected current aggregate checks:

```text
formal_comparison_rows.csv: N = {20, 40}
formal_bound_rows.csv: N = {20, 40}
initial instances: 120
initial rows: 2520
PP rows: 1920
bound violations: 0
delay-order failures among checked rows: 0
```

Checkpoint directories are local resume artifacts and are ignored by git. The cleanup tag `pre-handoff-cleanup-20260712` preserves the previous committed checkpoint state if an exact historical recovery point is ever needed.

## Formal Result Directories

```text
../../results/rule_based_experiments/formal_pp_hS3/
  config_manifest.json
  formal_comparison_rows.csv
  formal_comparison_summary.csv
  formal_comparison_summary.json
  gurobi_incumbent_trajectories.csv

../../results/rule_based_experiments/formal_bound_hS3/
  config_manifest.json
  formal_bound_rows.csv
  formal_bound_checkable_rows.csv
  formal_bound_summary.json

../../results/rule_based_experiments/formal_np_recovery_600s_hS3/
  config_manifest.json
  formal_np_recovery_rows.csv
  formal_np_recovery_summary.json

../../results/rule_based_experiments/formal_figures_hS3/
  bound_validation_actual_vs_upper.pdf
  experimental_tradeoff_solve_time_gap.pdf
  pp_delay_vs_threshold_density.pdf
  pp_time_and_scheduling_units.pdf
  gurobi_solution_quality_over_time.pdf
  *_metadata.json
```

Paper-facing copies of the five formal PDFs live in `../../paper/figures/`.

## Running the Next Formal Scale

Do not launch `N=60`, `N=80`, or NP recovery until the current `N={20,40}` aggregate state is reviewed.

When `N=60` is approved, use checkpoint-only chunks so multiple processes do not write the aggregate CSV files at the same time. Example for one chunk:

```bash
cd code/frontier_experiments
python3 rule_based_formal_hs3.py \
  --n-values 60 \
  --approaches 4 \
  --arrival-rates 0.4,0.7,1.0 \
  --thresholds 2,4,6,8 \
  --max-platoon-sizes 2,4,6,8 \
  --reps 20 \
  --hF 1 \
  --hS 3 \
  --time-limit 30 \
  --threads 12 \
  --skip-np-recovery \
  --write-trajectory \
  --resume \
  --checkpoint-only \
  --rep-start 0 \
  --rep-end-exclusive 5
```

After all approved `N=60` chunks finish, run a single aggregation pass that seeds from the existing `N={20,40}` CSV files and adds the new checkpoints:

```bash
cd code/frontier_experiments
python3 rule_based_formal_hs3.py \
  --n-values 20,40,60 \
  --approaches 4 \
  --arrival-rates 0.4,0.7,1.0 \
  --thresholds 2,4,6,8 \
  --max-platoon-sizes 2,4,6,8 \
  --reps 20 \
  --hF 1 \
  --hS 3 \
  --time-limit 30 \
  --threads 12 \
  --skip-np-recovery \
  --write-trajectory \
  --resume \
  --append-existing-outputs
```

Use the same pattern for `N=80` only after `N=60` has been reviewed.

## Figure Workflow

Regenerate paper-facing figures with:

```bash
cd code/frontier_experiments
MPLBACKEND=Agg python3 plot_rule_based_formal_hs3.py
```

The plotting script writes PDFs by default. PNG previews are optional and can be produced with `--write-png`.

Figure E selects a representative shared-instance trajectory from the available formal trajectory data. It should prefer an `N>=40` instance where NP has multiple incumbent updates or reaches the time limit and PP has at least two callback points. It should fall back to the older trajectory only if no better instance exists.

## Validation Commands

```bash
python3 -m compileall code
python3 code/frontier_experiments/tests/run_tests.py
cd paper && latexmk -pdf -interaction=nonstopmode main.tex
```

If `latexmk` is unavailable, try `pdflatex main.tex` from `paper/` and report the tool limitation.
