# Next Experiment Plan

This plan is intentionally minimal. It prepares the next implementation phase without running the full experiment suite and without restoring optimization-based partition selection.

## Immediate coding task

Create a new rule-based experiment path that standardizes three methods:

```text
NP  = singleton_partition(counts)
CHP = release_gap_threshold_partition(instance, threshold=delta, max_platoon_size=None)
PP  = release_gap_threshold_partition(instance, threshold=delta, max_platoon_size=P_max)
```

Recommended first code change:

1. Add a small method wrapper module or functions in `code/frontier_experiments/partition_methods.py` for `NP`, `CHP`, and `PP`.
2. Add tests proving the wrappers preserve FIFO order, operate per approach, use consecutive release gaps, enforce the finite PP cap, and do not call partition-selection code.
3. Add `rule_level_upper_bound(instance, threshold, max_platoon_size)` near `metrics.partition_metrics`.
4. Add a new lightweight driver that emits the unified schema documented in `paper/notes/code_and_experiment_audit.md`.

Do not modify `partition_selection.py` for PP. Keep it only as archived historical infrastructure.

## Experiment A: Theory verification

Purpose: verify the implemented calculations for the corrected bound chain on small instances where NP can be solved exactly.

Inputs:

```text
small N
small L
integer nondecreasing release times
h_F, h_S
threshold delta grid
maximum platoon size P_max grid
```

Methods:

```text
NP
CHP
PP
```

Measurements:

```text
actual_optimality_gap
partition_specific_upper_bound
rule_level_upper_bound
number_of_platoons
ordering_variable_count
```

Required check:

```text
0 <= actual_optimality_gap
actual_optimality_gap <= partition_specific_upper_bound
partition_specific_upper_bound <= rule_level_upper_bound
```

Stop condition: if a counterexample appears, stop expanding the search, minimize it, independently recompute it, and report the failed proof step. Numerical verification remains implementation evidence, not proof.

## Experiment B: NP versus CHP versus PP

Purpose: compare the three primary methods under the corrected research claim.

Design:

- Use the same \(\delta\) for CHP and PP in every comparable run.
- Use finite \(P_{\max}\) only for PP.
- Do not choose thresholds or platoon sizes by solving an optimization problem.

Metrics:

```text
average delay
actual gap when NP optimum is available
number of platoons
ordering-variable count
formation runtime
model build time
solver runtime
end-to-end runtime
optimality rate
terminal MIP gap
node count
partition-specific upper bound
rule-level upper bound
```

Interpretation:

- NP is the quality reference when solved.
- CHP may produce the fewest platoons and fastest downstream solve, but may create excessive loss.
- PP should be evaluated as a trade-off: less excessive loss than CHP while retaining substantial dimension reduction and computational benefit relative to NP.

## Experiment C: Trade-off analysis

Purpose: show transparent trade-offs without optimized partition frontiers.

Design:

- Sweep a grid of \((\delta,P_{\max})\) values for PP.
- Include CHP at the same \(\delta\) values with no effective cap.
- Include NP as the singleton reference.

Plots/tables:

```text
actual optimality gap vs ordering-variable count
partition-specific upper bound vs ordering-variable count
rule-level upper bound vs ordering-variable count
average delay vs number of platoons
```

Every PP point must be labeled or traceable to its explicit \((\delta,P_{\max})\). Do not use an optimized dimension-loss frontier.

## Experiment D: Scalability

Purpose: test whether rule-based preprocessing plus downstream scheduling scales better than vehicle-level scheduling.

Design:

- Compare NP, CHP, and PP for increasing \(N\).
- Keep \(L\), headways, arrival generator settings, time limit, and threads controlled within a main scalability study.
- Record rule-formation time separately from downstream model build and solve time.

Metrics:

```text
ordering-variable count
number of platoons
formation_time_ms
model_build_time_s
solve_time_s
end_to_end_time_s
status
terminal_mip_gap
node_count
objective
```

Large-instance note: when NP does not prove optimality, do not report actual platooning-induced optimality gaps. Report solver status, incumbent objective, terminal MIP gap, nodes, and runtime instead.

## Manuscript update sequence

1. Replace Section 4 with theory-guided rule-based platooning.
2. Implement the NP/CHP/PP experiment driver and schema.
3. Run Experiment A smoke/exact checks.
4. Run a small NP/CHP/PP smoke experiment.
5. Only after smoke validation, run the larger Experiment B-D suite.
6. Regenerate figures and tables from the new schema.
7. Rewrite Section 5 and the conclusion from the new results.

The exact next recommended coding task is: add standardized `NP`, `CHP`, and `PP` partition wrappers plus tests, and add the rule-level upper-bound metric helper.
