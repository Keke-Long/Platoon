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

Run the fair dimension-target scalability suite. The recommended paper design
uses three smaller scenario families rather than the full Cartesian grid.

Scalability fixes `L=4`, balanced demand, and Poisson arrivals while varying
`N`:

```bash
python run_scalability_batches.py \
  --n-values 20,30,40,60 \
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

Robustness fixes `N=30` and varies approaches, demand balance, and arrivals:

```bash
python run_scalability_batches.py \
  --n-values 30 \
  --l-values 3,4 \
  --demand-patterns balanced,unbalanced \
  --arrival-modes uniform,poisson,bursty \
  --targets 0.25,0.5,0.75,0.9 \
  --reps-per-cell 30 \
  --time-limit 30 \
  --threads 1 \
  --resume \
  --output-dir ../../results/frontier_experiments/robustness_final
```

Headway sensitivity fixes one representative scenario and varies `hS/hF`:

```bash
python run_scalability_batches.py \
  --n-values 30 \
  --l-values 4 \
  --demand-patterns balanced \
  --arrival-modes poisson \
  --hS-values 2,3,4 \
  --targets 0.25,0.5,0.75,0.9 \
  --reps-per-cell 30 \
  --time-limit 30 \
  --threads 1 \
  --resume \
  --output-dir ../../results/frontier_experiments/headway_final
```

For a smoke test, use `--reps-per-cell 2` on a single scenario and keep the
output directory clearly named as a smoke result.
The recorded end-to-end time is

```text
T_total = T_partition + T_downstream_wall
```

where partition time is nonzero for the proposed bound-aware partition and
zero for rule-based fixed-size and threshold baselines. The downstream wall
time includes model construction and Gurobi optimization. Vehicle-level runtime
is recorded separately for each traffic instance.

Aggregate completed batches with:

```bash
python aggregate_scalability_batches.py \
  ../../results/frontier_experiments/scalability_final
```

The batch runner writes each scenario under `batches/<scenario>/` and updates a
manifest after every completed scenario. Complete integer-budget frontiers are
generated only for small representative instances; larger instances use sampled
frontier budgets.
