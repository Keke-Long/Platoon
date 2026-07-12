# Formal hS=3 Experiment Handoff

This document records the current paper-facing formal experiment workflow for
the rule-based platooning study. It is intended for project handoff and should
be read together with `EXPERIMENT_DESIGN.md`, `README.md`, and
`../../paper/sections/experiments.tex`.

## Paper-level role

The paper proves and evaluates a performance-guaranteed preprocessing method
for vehicle scheduling at a general conflict area. The solver contribution is
not a new MILP algorithm; Gurobi remains the downstream optimizer. The method
reduces MILP dimension by grouping contiguous same-approach vehicles into
platoons while controlling the scheduling-delay loss.

The proof result supported by this experiment is the FIFO-indexed platoon loss
bound in `../../paper/sections/theoretical_analysis.tex`. For a contiguous
platoon partition `Pi`, the manuscript proves

```text
0 <= G(Pi) <= Ghat(Pi),
```

where `G(Pi)` is the average-delay gap between the platoon-constrained optimum
and the vehicle-level optimum, and `Ghat(Pi)` is the FIFO-indexed analytical
upper bound. The formal hS=3 experiments do not prove the theorem; they check
the implemented rule-level bound on solved instances and quantify the
dimension/runtime/delay tradeoff.

## Formal grid

The frozen formal grid is:

```text
L = 4
N = {20, 40, 60, 80}
arrival rates = {0.4, 0.7, 1.0}
hF = 1
hS = 3
delta = {2, 4, 6, 8}
Pmax = {2, 4, 6, 8}
replications = 20
threads = 12
initial time limit = 30 seconds
NP recovery time limit = 600 seconds, only when explicitly launched
```

Do not change this grid for paper-facing formal runs. The current instruction
is to run only the N=40 initial run next; do not launch N=60, N=80, or the
600-second NP recovery until the N=40 initial run has been reviewed.

## Main scripts

- `rule_based_formal_hs3.py`: formal NP/CHP/PP runner with checkpoint/resume.
- `plot_rule_based_formal_hs3.py`: paper-facing formal figures A-E.
- `partition_methods.py`: rule-based partition formation.
- `scheduling_milp.py`: downstream Gurobi scheduling model.
- `metrics.py`: ordering-variable counts and rule-level bound utilities.
- `tests/test_plot_rule_based_formal_hs3.py`: plotting and trajectory-selection tests.

## Output directories

```text
results/rule_based_experiments/formal_pp_hS3/
  formal_comparison_rows.csv
  formal_comparison_summary.csv
  gurobi_incumbent_trajectories.csv
  checkpoints/

results/rule_based_experiments/formal_bound_hS3/
  formal_bound_rows.csv
  formal_bound_checkable_rows.csv
  formal_bound_summary.json

results/rule_based_experiments/formal_np_recovery_600s_hS3/
  formal_np_recovery_rows.csv
  formal_np_recovery_summary.json

results/rule_based_experiments/formal_figures_hS3/
  bound_validation_actual_vs_upper.{pdf,png}
  experimental_tradeoff_solve_time_gap.{pdf,png}
  pp_delay_vs_threshold_density.{pdf,png}
  pp_time_and_platoon_count.{pdf,png}
  gurobi_solution_quality_over_time.{pdf,png}
```

Paper-facing copies of the formal figures are stored under `../../paper/figures/`.

## Completed status

The N=20 formal run is accepted and has been written into
`../../paper/sections/experiments.tex` as preliminary N=20-only results.

Accepted N=20 statistics:

```text
PP bound-checkable rows: 960
bound-check coverage: 100%
bound violations: 0
mean actual G: 0.331
median actual G: 0.000
mean Ghat: 52.200
median Ghat: 45.275
minimum slack: 6.950
delay-order failures among checked rows: 0 / 960
mean NP delay: 8.531
mean PP delay: 8.862
mean CHP delay: 8.977
PP mean platoon count: 7.786
PP mean ordering-variable count: 26.416
PP mean dimension-reduction ratio: 82.4%
```

These numbers are N=20-only and must not be moved into the abstract or
conclusion.

## Current N=40 run

The N=40 initial run was launched with checkpoint/resume enabled and NP
recovery disabled:

```bash
cd code/frontier_experiments
python3 rule_based_formal_hs3.py \
  --n-values 20,40 \
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
  --resume
```

Including `20,40` is intentional: the runner loads the accepted N=20
checkpoints, skips them, and continues with missing N=40 replications while
preserving aggregate outputs across N=20 and N=40.

Progress can be checked with:

```bash
find ../../results/rule_based_experiments/formal_pp_hS3/checkpoints \
  -maxdepth 1 -name 'N40_*.json' | wc -l
```

There are 60 N=40 checkpoints expected: 3 arrival rates times 20
replications. The runner rewrites aggregate CSV/JSON files after each completed
replication, so these files are dirty while the run is active.

## Resume command

If the process is interrupted, resume with the same command above. Do not
delete checkpoints. The runner identifies completed replications from
`formal_pp_hS3/checkpoints/`.

## Figure workflow

Regenerate formal figures with:

```bash
cd code/frontier_experiments
MPLBACKEND=Agg python3 plot_rule_based_formal_hs3.py
```

Then copy the generated paper-facing figures from
`../../results/rule_based_experiments/formal_figures_hS3/` to
`../../paper/figures/`.

Figure E is provisional while only N=20 trajectories are available. After N=40
finishes, the plotting script prefers an N>=40 instance where:

```text
NP has multiple incumbent updates or reaches the time limit;
PP has at least two callback points;
NP, CHP, and PP use the same traffic instance.
```

It falls back to the provisional N=20 trajectory only if no better instance is
available.

## Validation commands

Plotting tests:

```bash
PYTHONPATH=code/frontier_experiments python3 -m pytest \
  code/frontier_experiments/tests/test_plot_rule_based_formal_hs3.py
```

If `pytest` is not installed, the same tests can be run directly by loading the
test module, as was done in the current environment.

Syntax check:

```bash
python3 -m py_compile \
  code/frontier_experiments/plot_rule_based_formal_hs3.py \
  code/frontier_experiments/rule_based_formal_hs3.py \
  code/frontier_experiments/tests/test_plot_rule_based_formal_hs3.py
```

Manuscript compile target:

```bash
cd paper
latexmk -pdf -interaction=nonstopmode main.tex
```

In the current environment, both `latexmk` and `pdflatex` were unavailable, so
the manuscript source was not locally compiled after the latest figure/text
update.

## Code cleanup priorities before handoff

1. Keep `rule_based_formal_hs3.py` as the source of truth for the formal hS=3
   runner until the current N=40 run finishes.
2. Do not edit the frozen experiment grid or accepted N=20 data.
3. Avoid parallel writers to the same output directory. If parallel execution
   is needed, first add explicit chunk output directories or a safe merge step.
4. After N=40 completes, commit the generated N=40 checkpoints and aggregate
   outputs separately from any code cleanup commit.
5. If more runtime reduction is needed, add a formal chunk runner for
   `rule_based_formal_hs3.py` rather than launching multiple processes against
   the same output directory.
6. Keep plotting presentation changes separate from numerical data changes.
