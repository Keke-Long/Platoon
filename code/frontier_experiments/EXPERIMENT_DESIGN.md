# Frontier Experiment Design

This document records the finalized experimental design actually used by the
current `code/frontier_experiments` pipeline and the committed result files.
It is a runbook and interpretation guide, not a theoretical statement.

## Roles of the three evidence streams

1. Theoretical proof:
   Establishes the FIFO-indexed loss bound for arbitrary numbers of approaches
   and contiguous same-approach platoon partitions. The theorem does not rely
   on a Poisson model, balanced demand, or any particular numerical scenario.
2. Exhaustive small-instance verification:
   Enumerates FIFO-feasible sequences and contiguous platoon partitions on
   small domains to verify the implementation and look for counterexamples.
   This is implementation evidence, not a substitute for proof.
3. Computational frontier and scalability experiments:
   Evaluate whether the indexed bound helps choose smaller downstream MILPs
   while preserving a deterministic loss guarantee and better solver behavior.

## Core model quantities

The large-instance experiments use the deterministic reduced-dimension measure

```text
C(Pi) = sum_{l < m} K_l K_m
```

where `K_l` is the number of platoons on approach `l`.

The indexed bound used in code is

```text
N * B_idx(Pi) = sum_e max((N - i_e) * max(d_e - hF, 0) - 2 * (hS - hF), 0)
```

All fair method comparisons enforce the same downstream ordering-variable
budget `C(Pi) <= Cbar`. Baselines are not allowed to exceed the budget.

## Traffic-instance generation in the current code

The main generators are defined in
[scalability_suite.py](/home/klong23/Platoon/code/frontier_experiments/scalability_suite.py).

### Vehicle counts by demand pattern

`counts_for(total_vehicles, approaches, demand_pattern)`:

- `balanced`:
  `total_vehicles` is split as evenly as possible. Each approach gets
  `floor(N/L)` vehicles, and the first `N mod L` approaches receive one extra
  vehicle.
- `unbalanced`:
  approach weights are descending integers `[L, L-1, ..., 1]`. Initial counts
  are rounded from the proportional allocation, lower-bounded by one, then
  adjusted until the total matches `N`.

### Release-time generators

`generate_releases(scenario, rng)`:

- `uniform`:
  each release time is an integer sampled uniformly from
  `[0, scenario.max_release]`, then sorted within the approach.
- `poisson`:
  each approach starts from an integer offset in `[0, 3]`. Inter-arrival times
  are exponential with rate `0.45 + 0.1 * (approach_index mod 3)`, accumulated
  and rounded to integers.
- `bursty`:
  each approach creates `max(2, count // 4)` integer burst centers in
  `[0, scenario.max_release]`. Each release picks a center and adds an integer
  perturbation in `[-2, 2]`, then clamps to the same range and sorts.

For the scalability suite,

```text
scenario.max_release = max(10, 2 * N)
```

## Partition methods compared

The compared methods are:

1. `proposed_bound_aware`
   `min B_idx(Pi)` subject to `C(Pi) <= Cbar`, solved by Gurobi in
   [partition_selection.py](/home/klong23/Platoon/code/frontier_experiments/partition_selection.py).
2. `fixed_size_closest_dimension`
   candidate platoon sizes `1, 2, ..., Pmax`, then choose the feasible
   candidate with the largest `C(Pi)` satisfying `C(Pi) <= Cbar`.
3. `threshold_closest_dimension`
   candidate release-gap thresholds from `{0, hF, hS}` plus all observed
   intra-approach release gaps, then choose the feasible candidate with the
   largest `C(Pi)` satisfying `C(Pi) <= Cbar`.

The vehicle-level model is not one of the reduced methods. It is solved
separately as the benchmark scheduling model.

## Headways, platoon size, solver settings

Formal scalability runs use:

- `hF = 1`
- `hS = 2`
- `maximum platoon size = 4`
- downstream `TimeLimit = 30` seconds
- downstream `Threads = 1`
- partition-selection `TimeLimit = 30` seconds
- partition-selection `Threads` follow the Gurobi default environment, but the
  surrounding experiment process runs one partition-selection or scheduling
  model at a time per chunk runner.

## Targets, sampled budgets, and frontiers

The fairness targets are

```text
0.25, 0.5, 0.75, 0.9
```

which are interpreted as target dimension-reduction fractions. The raw budget
is

```text
round(C0 * (1 - target))
```

where `C0` is the vehicle-level ordering-variable count. The effective budget
is then raised, if necessary, to the minimum feasible budget induced by the
maximum platoon-size cap.

Complete frontier generation is controlled separately:

- for small representative instances (`N <= 20`), every integer dimension
  budget from the feasible minimum to `C0` is considered;
- otherwise the code samples budgets with `frontier_budget_count = 12`.

The formal checkpointed `N=30` and `N=40` scenario aggregates contain zero
frontier rows because no large-instance frontier solve finished with a retained
optimal partition under the current settings.

## Seeds and repetitions

Formal controlled scalability uses `30` repetitions per scenario.

Each repetition is generated independently through

```text
replication_seed(base_seed, scenario, replication)
```

implemented as the first 8 bytes of a SHA-256 hash of:

- the base seed,
- the scenario definition,
- the replication index.

This makes every replication reproducible and allows chunked execution without
changing the instance stream.

The current base seed is:

```text
20260710
```

## Runtime, status, MIP gap, nodes, and incumbent definitions

Per-method rows in `fair_dimension_comparison.csv` contain:

- `status`:
  downstream Gurobi final status for the reduced model.
- `objective_average_delay`:
  downstream incumbent average delay at termination. This exists for both
  `OPTIMAL` and `TIME_LIMIT` runs whenever Gurobi found a feasible incumbent.
- `mip_gap`:
  reduced-model MIP gap at termination when reported by Gurobi.
- `nodes`:
  reduced-model branch-and-bound node count.
- `time_to_first_feasible`:
  callback-recorded time to the first incumbent when available.
- `partition_time_seconds`:
  wall time spent constructing or solving the partition method itself.
- `model_construction_seconds`:
  reduced scheduling MILP build time.
- `downstream_optimization_seconds`:
  Gurobi-reported reduced-model optimization runtime.
- `end_to_end_seconds`:
  `partition_time_seconds + downstream wall time`.

Vehicle-level summaries contain:

- `vehicle_level_status`
- `vehicle_level_mip_gap`
- `vehicle_level_nodes`
- `vehicle_level_wall_time_seconds`
- `vehicle_level_average_delay`:
  only when the vehicle-level model proved optimal.
- `vehicle_level_incumbent_average_delay`:
  incumbent objective, even when the vehicle-level model reached the time
  limit, for new runs after the compatibility update.

## When actual gap can be computed

The actual average-delay gap is recorded only when:

1. the reduced model status is `OPTIMAL`;
2. the vehicle-level model status is `OPTIMAL`; and
3. both objective values are available.

If those conditions fail, `actual_average_gap` is left blank and
`all_actual_gaps_within_bound` becomes `N/A` in the summary.

## Checkpoint, resume, chunk, and aggregation workflow

The checkpointed large-instance pipeline is:

1. `scalability_chunk_runner.py`
   runs one scenario over an explicit repetition interval, for example
   `0-4` or `15-19`.
2. Each repetition is written immediately to:

   ```text
   chunks/rep_xxx_yyy/reps/rep_zzz.json
   ```

3. After every repetition, the chunk runner rewrites:

   - `fair_dimension_comparison.csv`
   - `complete_frontier.csv`
   - `summary.csv`
   - `vehicle_level_summary.csv`
   - `chunk_manifest.json`
   - `scalability_chunk.json`

4. `--resume` skips any repetition file that already exists.
5. `aggregate_scalability_chunks.py` merges all chunk directories for a
   scenario and checks:

   - duplicate replications;
   - missing replications;
   - duplicate instance seeds;
   - per-repetition row count;
   - scenario consistency;
   - normalized config consistency;
   - budget violations;
   - known actual-gap violations;
   - reduced-model status counts;
   - vehicle-level status counts.

## Formal completed scalability configurations

### N=20 controlled scalability

Directory:

```text
results/frontier_experiments/scalability_final/batches/N20_L4_balanced_poisson_hS2
```

Configuration:

- `N = 20`
- `L = 4`
- demand pattern `balanced`
- arrival mode `poisson`
- `hF = 1`
- `hS = 2`
- `Pmax = 4`
- `targets = 0.25, 0.5, 0.75, 0.9`
- `repetitions = 30`
- `TimeLimit = 30`
- `Threads = 1`

This run uses the pre-chunk `scalability_suite.py` batch output but follows the
same controlled design.

### N=30 controlled scalability

Directory:

```text
results/frontier_experiments/scalability_checkpointed/N30_L4_balanced_poisson_hS2
```

Same fixed settings as `N=20`, but with:

- `N = 30`
- chunk ranges `0-4, 5-9, 10-14, 15-19, 20-24, 25-29`

### N=40 controlled scalability

Directory:

```text
results/frontier_experiments/scalability_checkpointed/N40_L4_balanced_poisson_hS2
```

Same fixed settings as `N=20`, but with:

- `N = 40`
- chunk ranges `0-4, 5-9, 10-14, 15-19, 20-24, 25-29`

## Result files and field meanings

Scenario-level formal outputs:

- `fair_dimension_comparison.csv`:
  one row per method, target, and repetition.
- `summary.csv`:
  grouped by `N, L, demand_pattern, arrival_mode, target_dimension_reduction,
  method_family`.
- `vehicle_level_summary.csv`:
  deduplicated vehicle-level summary by scenario.
- `aggregate_checks.json`:
  chunk-level integrity checks for checkpointed scenarios.

Cross-scenario formal outputs:

- `results/frontier_experiments/scalability_checkpointed/core_scalability_summary.csv`
- `results/frontier_experiments/scalability_checkpointed/paper_scalability/*.png`
- `results/frontier_experiments/scalability_checkpointed/paper_scalability/fair_method_comparison.csv`
- `results/frontier_experiments/scalability_checkpointed/paper_scalability/time_limit_incumbent_summary.csv`

## Existing non-formal directories

The following directories remain in the repository as development artifacts,
but they are not used as formal manuscript evidence:

- `results/frontier_experiments/pilot_30`
- `results/frontier_experiments/scalability_pilot_wls`
- `results/frontier_experiments/scalability_stress_l4_wls`
- `results/frontier_experiments/smoke*`

They were produced for pilot checks, stress checks, or smoke validation rather
than the finalized controlled scalability protocol.
