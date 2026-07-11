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
