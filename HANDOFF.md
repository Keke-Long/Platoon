# Platoon Scheduling Handoff

Current active branch: `agent/restore-rule-based-platooning-clean`.

## Research Objective

The repository supports a manuscript on performance-guaranteed platooning as a preprocessing step for vehicle scheduling at a general conflict area. The active theory is the FIFO-indexed platoon loss bound, and the active computational study is the hS=3 NP/CHP/PP formal experiment grid. Gurobi remains the downstream MILP optimizer.

Old frontier, optimized-partition, dimension-budget, complete-frontier, sampled-budget, and hS=2 workflows were removed because they do not match the final manuscript design.

The manuscript method section has been aligned with the active rule-based implementation: PP is the threshold-and-cap platooning rule using `delta` and `Pmax`, not a separate partition-search method.

The Chapter 5 figure source of truth is `code/frontier_experiments/CHAPTER5_FIGURE_SPEC.md`; do not change figure axes, plot types, encodings, or aggregation rules without explicit project-lead approval.

## Current Completion State

- `N=20`: completed in the active formal aggregate results.
- `N=40`: completed in the active formal aggregate results.
- `N=60`: not started in the active formal aggregate results.
- `N=80`: not started in the active formal aggregate results.
- 600-second NP recovery: not started in the active formal aggregate results.

The committed formal aggregates contain exactly `N={20,40}`.

## Active Scripts

- `code/frontier_experiments/rule_based_formal_hs3.py`
- `code/frontier_experiments/plot_rule_based_formal_hs3.py`
- `code/frontier_experiments/scheduling_milp.py`
- `code/frontier_experiments/partition_methods.py`
- `code/frontier_experiments/metrics.py`
- `code/frontier_experiments/tests/run_tests.py`

Exact verification code remains under `code/exhaustive_verification/`.

## Active Result Files

```text
results/rule_based_experiments/formal_pp_hS3/config_manifest.json
results/rule_based_experiments/formal_pp_hS3/formal_comparison_rows.csv
results/rule_based_experiments/formal_pp_hS3/formal_comparison_summary.csv
results/rule_based_experiments/formal_pp_hS3/formal_comparison_summary.json
results/rule_based_experiments/formal_pp_hS3/gurobi_incumbent_trajectories.csv

results/rule_based_experiments/formal_bound_hS3/config_manifest.json
results/rule_based_experiments/formal_bound_hS3/formal_bound_rows.csv
results/rule_based_experiments/formal_bound_hS3/formal_bound_checkable_rows.csv
results/rule_based_experiments/formal_bound_hS3/formal_bound_summary.json

results/rule_based_experiments/formal_np_recovery_600s_hS3/config_manifest.json
results/rule_based_experiments/formal_np_recovery_600s_hS3/formal_np_recovery_rows.csv
results/rule_based_experiments/formal_np_recovery_600s_hS3/formal_np_recovery_summary.json

results/rule_based_experiments/formal_figures_hS3/bound_validation_actual_vs_upper.pdf
results/rule_based_experiments/formal_figures_hS3/experimental_tradeoff_solve_time_gap.pdf
results/rule_based_experiments/formal_figures_hS3/pp_delay_vs_threshold_density.pdf
results/rule_based_experiments/formal_figures_hS3/pp_time_and_scheduling_units.pdf
results/rule_based_experiments/formal_figures_hS3/gurobi_solution_quality_over_time.pdf
results/rule_based_experiments/formal_figures_hS3/gurobi_solution_quality_over_time_metadata.json
results/rule_based_experiments/formal_figures_hS3/pp_delay_vs_threshold_density_metadata.json
results/rule_based_experiments/formal_figures_hS3/pp_time_and_scheduling_units_metadata.json
```

Paper-facing figure files are:

```text
paper/figures/Picture1.png
paper/figures/Picture2.png
paper/figures/bound_validation_actual_vs_upper.pdf
paper/figures/experimental_tradeoff_solve_time_gap.pdf
paper/figures/pp_delay_vs_threshold_density.pdf
paper/figures/pp_time_and_scheduling_units.pdf
paper/figures/gurobi_solution_quality_over_time.pdf
```

## Test Commands

```bash
python3 -m compileall code
python3 code/frontier_experiments/tests/run_tests.py
cd paper && latexmk -pdf -interaction=nonstopmode main.tex
```

If `latexmk` is unavailable, try:

```bash
cd paper && pdflatex -interaction=nonstopmode main.tex
```

## N=60 Command

Do not run this until `N={20,40}` has been reviewed. When approved, run N=60 in checkpoint-only chunks. Example first chunk:

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

Launch additional non-overlapping chunks by changing only `--rep-start` and `--rep-end-exclusive`, for example `5..10`, `10..15`, and `15..20`.

## Resume Command

Resume any interrupted chunk with the same chunk command. The runner skips completed local checkpoints.

## Aggregate Command

After all approved N=60 chunks finish, run exactly one aggregate writer:

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

`--append-existing-outputs` seeds the aggregate from the existing `N={20,40}` CSV files before adding resumed checkpoints. This is needed because checkpoint directories are local resume artifacts and are not committed.

## Plotting Command

```bash
cd code/frontier_experiments
MPLBACKEND=Agg python3 plot_rule_based_formal_hs3.py
```

The plotter writes PDFs by default. Use `--write-png` only for optional previews.

## Known Limitations

- Checkpoints are intentionally ignored and not committed. The pushed safety tag `pre-handoff-cleanup-20260712` preserves the earlier committed checkpoint state if historical recovery is needed.
- The current environment may not have LaTeX installed; manuscript compilation requires `latexmk` or `pdflatex`.
- Gurobi-backed tests require a reachable Gurobi runtime/token service. In an offline environment, those tests are skipped by the local test runner.
- Run only one aggregate writer at a time. Parallel experiment execution must use `--checkpoint-only` chunks followed by one aggregation pass.
