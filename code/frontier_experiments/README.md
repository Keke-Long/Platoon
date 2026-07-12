# Dimension-Loss Frontier Experiments

This package starts the second experiment stage: using the FIFO-indexed loss
bound to select platoon partitions before constructing the downstream
scheduling MILP.

The partition-selection decisions are boundary cuts. For approach `l`, the
binary variable `cut_l_i` is one when the boundary between vehicles `i` and
`i+1` is cut, and zero when the vehicles are joined in the same platoon.

The model uses the exact scaled bound

```text
N * B_idx(Pi) = sum_e max((N - i_e) * max(d_e - hF, 0) - 2 * (hS - hF), 0)
```

and the deterministic dimension measure

```text
C(Pi) = sum_{l < m} K_l K_m
```

where `K_l` is the number of platoons on approach `l`.

Two partition-selection formulations are implemented:

```text
min C(Pi)      s.t. N * B_idx(Pi) <= scaled_loss_budget
min N*B_idx(Pi) s.t. C(Pi) <= ordering_budget
```

`partition_selection.py` contains both a Gurobi model and an exact enumeration
fallback. The fallback is for smoke tests and small reproducible examples; the
paper's frontier experiments should be run with `--solver gurobi` on a machine
where `gurobipy` and a valid Gurobi license are available.

Example smoke run from this directory:

```bash
python frontier_driver.py \
  --counts 3,3,3 \
  --arrival-mode bursty \
  --hF 1 \
  --hS 2 \
  --max-platoon-size 3 \
  --solver auto \
  --output-dir ../../results/frontier_experiments/smoke
```

Outputs:

```text
frontier.json
pareto_frontier.csv
loss_budget_solutions.csv
size_budget_solutions.csv
```

Plot the nondominated frontier:

```bash
python plot_frontier.py \
  ../../results/frontier_experiments/smoke/frontier.json \
  --output ../../results/frontier_experiments/smoke/frontier.png
```

For small instances, the driver also computes the actual optimality gap by
exact sequence enumeration. For larger instances, pass `--skip-actual-gap` and
compute downstream schedule quality with the later Gurobi scheduling model.

Run the integrated three-part experiment suite:

```bash
python experiment_suite.py \
  --replications 30 \
  --time-limit 5 \
  --partition-solver gurobi \
  --output-dir ../../results/frontier_experiments/pilot_30
```

This produces:

```text
experiment_suite.json
comparison_runtime.csv
dimension_loss_frontier.csv
summary.csv
```

Generate review plots from the suite output:

```bash
python plot_suite.py ../../results/frontier_experiments/pilot_30
```

The suite covers the dimension-loss frontier, comparisons with vehicle-level,
fixed-size, fixed-threshold, and bound-aware partitions, and downstream Gurobi
runtime metrics for each selected partition.

The finalized paper-facing experiment design is documented in
[`EXPERIMENT_DESIGN.md`](./EXPERIMENT_DESIGN.md). Use that file as the source
of truth for formal settings, result locations, and field meanings.

Run the unified rule-based NP/CHP/PP experiment:

```bash
python rule_based_formal_comparison.py \
  --reps 20 \
  --n-values 12,16,20,24 \
  --arrival-rates 0.4,0.7,1.0 \
  --thresholds 2,3,4 \
  --max-platoon-sizes 2,3,4,5 \
  --time-limit 30 \
  --threads 1 \
  --output-dir ../../results/rule_based_experiments/formal_unified
```

For each traffic instance, this solves NP once, CHP once per threshold, and PP
once per `(threshold, max_platoon_size)`. PP rows record the actual gap
`D_PP - D_NP`, the rule-level upper bound, bound-check availability, delay-order
check availability, dimension reduction, formation time, solver time, terminal
MIP gap, and node count. The same output supports bound-effectiveness,
NP/CHP/PP comparison, and trade-off plots.

Run the fair dimension-target scalability suite. The recommended paper design
uses a controlled scalability setting to isolate the effect of vehicle count.

Scalability fixes `L=4`, balanced demand, and Poisson arrivals while varying
`N`:

```bash
python run_scalability_batches.py \
  --n-values 20,30,40 \
  --l-values 4 \
  --demand-patterns balanced \
  --arrival-modes poisson \
  --targets 0.25,0.5,0.75,0.9 \
  --reps-per-cell 30 \
  --time-limit 30 \
  --threads 1 \
  --resume \
  --output-dir ../../results/frontier_experiments/scalability_final
```

The balanced Poisson setting above is a controlled instance generator, not an
assumption required by the FIFO-indexed theorem. A compact heterogeneous
collection may be used as a supplementary illustration by mixing a small
number of approach counts, demand patterns, arrival generators, and admissible
headways. A full factorial robustness study, a separate headway-sensitivity
study, and the `N=60` scalability case are optional extensions rather than
requirements for the current manuscript.

For a smoke test, use `--reps-per-cell 2` on a single scenario and keep the
output directory clearly named as a smoke result.
The recorded end-to-end time is

```text
T_total = T_partition + T_downstream_wall
```

where partition time is measured as wall time for every method. For the
proposed bound-aware method this includes the partition-selection Gurobi solve;
for fixed-size and threshold baselines it includes heuristic partition
construction and feasible-dimension selection. The downstream wall time
includes model construction and Gurobi optimization. Vehicle-level runtime is
recorded separately for each traffic instance, and `vehicle_level_summary.csv`
contains the deduplicated vehicle-level aggregates.

Aggregate completed batches with:

```bash
python aggregate_scalability_batches.py \
  ../../results/frontier_experiments/scalability_final
```

The batch runner writes each scenario under `batches/<scenario>/` and updates a
manifest after every completed scenario. Complete integer-budget frontiers are
generated only for small representative instances; larger instances use sampled
frontier budgets.

For long-running `N=30` and `N=40` scenarios, use the checkpointed chunk
runner instead of rerunning the entire 30-repetition scenario in one process.
Each chunk writes one repetition at a time and can be resumed safely.

Example: five-repetition chunk for the controlled `N=30` scenario

```bash
python scalability_chunk_runner.py \
  --n 30 \
  --l 4 \
  --demand-pattern balanced \
  --arrival-mode poisson \
  --hS 2 \
  --rep-start 0 \
  --rep-end 4 \
  --time-limit 30 \
  --threads 1 \
  --resume \
  --output-dir ../../results/frontier_experiments/scalability_checkpointed/N30_L4_balanced_poisson_hS2/chunks/rep_000_004
```

Aggregate all chunks for a completed scenario with:

```bash
python aggregate_scalability_chunks.py \
  ../../results/frontier_experiments/scalability_checkpointed/N30_L4_balanced_poisson_hS2 \
  --expected-reps 30
```

The aggregate step verifies missing or duplicate seeds, per-repetition row
counts, budget violations, known actual-gap violations, and status totals
before writing the scenario-level CSV outputs.
