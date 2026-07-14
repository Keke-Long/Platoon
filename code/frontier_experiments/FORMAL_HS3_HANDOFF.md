# Formal hS=3 Experiment Handoff

This is the operational source of truth for the paper-facing NP/CHP/PP experiment pipeline. Scientific metric definitions are in `EXPERIMENT_DESIGN.md`; figure definitions are in `CHAPTER5_FIGURE_SPEC.md`.

## Fixed Design

```text
L = 4
N = {20, 40, 60, 80}
total arrival rates lambda = {0.5, 1.0, 1.5, 2.0, 2.5}
per-approach Poisson rate = lambda / 4
hF = 1
hS = 3
delta = {2, 4, 6, 8}
Pmax = {2, 4, 6, 8}
replications = 10
Gurobi threads per solve = 12
maximum solve time = 600 seconds for every NP, CHP, and PP model
```

There is no recovery stage. Gurobi stops immediately when it proves optimality. Rows unresolved after 600 seconds retain their incumbent, best bound, and terminal MIP gap and may later be rerun with a longer limit.

PP is the one-pass threshold-and-cap rule. The experiment pipeline must not invoke an optimized partition-selection, frontier, or dimension-budget method.

## Approved Legacy Reuse

Old per-approach `arrival_rate=0.4` rows are treated as total `lambda=1.5`, and old per-approach `arrival_rate=0.7` rows are treated as total `lambda=2.5`. This is an approved project decision.

For the first 10 replications, legacy rows already marked `OPTIMAL` may be migrated without rerunning. Legacy `TIME_LIMIT` rows must be solved again on the stored release-time instance and partition with the uniform 600-second limit. Use `migrate_legacy_uniform_results.py`; do not regenerate those approved traffic instances.

## Result Directories

```text
results/rule_based_experiments/formal_pp_hS3_600s_r10
results/rule_based_experiments/formal_bound_hS3_600s_r10
results/rule_based_experiments/formal_figures_hS3_600s_r10
```

Legacy 30-second results remain under the unsuffixed `formal_*_hS3` directories and must not be mixed directly into the new aggregates.

## Parallel Execution

The workstation has 128 logical CPUs. Use eight checkpoint-only workers with 12 Gurobi threads each, for a maximum of 96 solver threads. Recommended non-overlapping replication ranges are:

```text
0..2, 2..4, 4..5, 5..6, 6..7, 7..8, 8..9, 9..10
```

Each worker uses the same command except for `--rep-start` and `--rep-end-exclusive`:

```bash
cd code/frontier_experiments
python3 rule_based_formal_hs3.py \
  --n-values 20 \
  --arrival-rates 0.5,1.0,2.0 \
  --reps 10 \
  --time-limit 600 \
  --threads 12 \
  --write-trajectory \
  --resume \
  --checkpoint-only \
  --rep-start 0 \
  --rep-end-exclusive 2
```

For `N=20` and `N=40`, migrate approved `lambda={1.5,2.5}` legacy instances and run only the missing rates directly. For `N={60,80}`, run all five rates directly.

Only checkpoint-only workers may run in parallel. Never run more than one aggregate writer at the same time.

For a restartable unattended campaign, use `run_formal_hs3_campaign.py`. It adopts already running workers, fills only missing checkpoints, validates each completed scale, and writes live state to `formal_pp_hS3_600s_r10/campaign_status.json`.

The four-scale campaign is complete; no tmux campaign session should remain active.

## Aggregation

After all checkpoints for the requested scales exist, run one writer. Example after completing `N=20`:

```bash
cd code/frontier_experiments
python3 rule_based_formal_hs3.py \
  --n-values 20 \
  --arrival-rates 0.5,1.0,1.5,2.0,2.5 \
  --reps 10 \
  --time-limit 600 \
  --threads 12 \
  --write-trajectory \
  --resume
```

When extending an existing aggregate to another `N`, include all completed `N` values and add `--append-existing-outputs`.

## Validation

```bash
python3 -m compileall code
python3 code/frontier_experiments/tests/run_tests.py
cd paper && latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
```

The Gurobi Academic WLS license is installed at `/home/klong23/gurobi.lic`. The experiment runner must report zero duplicate row keys and zero bound violations before figures are regenerated.

## Figures

```bash
cd code/frontier_experiments
MPLBACKEND=Agg python3 plot_rule_based_formal_hs3.py \
  --comparison-dir ../../results/rule_based_experiments/formal_pp_hS3_600s_r10 \
  --bound-dir ../../results/rule_based_experiments/formal_bound_hS3_600s_r10 \
  --output-dir ../../results/rule_based_experiments/formal_figures_hS3_600s_r10
```
