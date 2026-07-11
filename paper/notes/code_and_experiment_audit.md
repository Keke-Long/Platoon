# Code and Experiment Audit

Branch reviewed: `agent/restore-rule-based-platooning-clean`.

## Active manuscript old-direction audit

| File | Old-direction content | Classification | Notes |
|---|---|---|---|
| `paper/main.tex` | Abstract says the framework seeks a platoon partition and reports 72--76% optimized-partition scalability reductions. | Rewrite | Directly contradicts the restored rule-based method. Replace after new NP/CHP/PP experiments exist. |
| `paper/sections/dimension_reduction.tex` | MILP encoding of a contiguous partition, cut variables, product variables, loss-budget formulation, computation-size formulation, Gurobi partition selection. | Remove/rewrite | This entire section should become theory-guided rule-based platooning: NP, CHP, PP, online algorithm, complexity. |
| `paper/sections/experiments.tex` | Bound-selected versus oracle comparison, selection regret, dimension-budget comparisons, proposed bound-aware partition, old scalability figures and table. | Rewrite/archive results | Keep small exact verification logic as theory verification infrastructure. Do not use old optimized-partition results as PP evidence. |
| `paper/sections/conclusion.tex` | Claims the bound guides aggregation-level selection and cites optimized-partition scalability outcomes. | Rewrite | Final conclusion should reflect deterministic threshold-and-size preprocessing. |
| `paper/notes/phase1_sections_3_6_revision_map.md` | Names the withdrawn optimization-based material. | Retain only as historical development material | Correctly records what must be withdrawn; no action needed. |

## Code architecture map

```text
input generation
-> platoon formation
-> scheduling model construction
-> solver execution
-> result collection
-> plotting
```

### Input generation

| Module | Current role | Status |
|---|---|---|
| `code/frontier_experiments/frontier_driver.py` | Generates small single-instance frontier inputs with uniform, Poisson, or bursty releases. | Reuse with modification |
| `code/frontier_experiments/experiment_suite.py` | Generates pilot comparison scenarios for optimized-partition experiments. | Reuse generation helpers only |
| `code/frontier_experiments/scalability_suite.py` | Generates scalable scenarios, replications, deterministic seeds, and release times. | Reuse with modification |
| `code/frontier_experiments/scalability_chunk_runner.py` | Runs checkpointed chunks for scalability experiments. | Reuse with modification |
| `code/exhaustive_verification/verify_bound.py` and `random_verify.py` | Exact and random-exact verification input generation. | Reuse unchanged for theory checks |

### Platoon formation

| Module | Current role | Status |
|---|---|---|
| `code/frontier_experiments/partition_methods.py::release_gap_threshold_partition` | Implements per-approach consecutive release-gap threshold partitioning with optional max platoon size. | Reuse unchanged as the rule core |
| `code/frontier_experiments/scheduling_milp.py::singleton_partition` | Creates singleton partitions. | Reuse unchanged for NP |
| `code/frontier_experiments/partition_methods.py::fixed_size_partition` | Fixed-size baseline. | Archive or keep as secondary baseline only |
| `code/frontier_experiments/partition_methods.py::bound_aware_loss_budget_partition` and `bound_aware_size_budget_partition` | Calls optimized partition-selection models. | Archive for historical development |
| `code/frontier_experiments/partition_selection.py` | Gurobi and enumeration models for loss-budget and size-budget partition selection. | Archive; do not use for PP |
| `code/exhaustive_verification/enumerate_partitions.py` | Exhaustively enumerates contiguous partitions. | Reuse for small theory verification/oracle checks, not PP formation |

### Scheduling model construction and solver execution

| Module | Current role | Status |
|---|---|---|
| `code/frontier_experiments/scheduling_milp.py` | Builds and solves downstream vehicle/platoon MILP with Gurobi for any contiguous partition. | Reuse with modification |
| `code/exhaustive_verification/model.py` | Exact completion-time recursion, delay, internal links, indexed bound. | Reuse unchanged |
| `code/exhaustive_verification/enumerate_sequences.py` | Enumerates FIFO and platoon-constrained sequences for exact small instances. | Reuse unchanged |
| `code/exhaustive_verification/global_repair.py` | Implements proof repair trace checks. | Reuse unchanged for proof verification |

### Result collection

| Module | Current role | Status |
|---|---|---|
| `code/frontier_experiments/metrics.py` | Ordering-variable counts, platoon counts, dimension reduction, partition-specific indexed bound. | Reuse with modification |
| `code/frontier_experiments/scalability_suite.py::record_method` | Collects solver status, MIP gap, nodes, timing, actual gap when vehicle optimum is known. | Reuse with modification |
| `code/frontier_experiments/aggregate_scalability_batches.py` and `aggregate_scalability_chunks.py` | Aggregates old scalability outputs and frontier rows. | Reuse with modification |

### Plotting

| Module | Current role | Status |
|---|---|---|
| `code/frontier_experiments/plot_scalability_summary.py` | Builds runtime, MIP-gap, node, optimality-rate, and dimension-reduction plots for old method families. | Reuse with modification |
| `code/frontier_experiments/plot_suite.py` | Plots optimized dimension-loss frontier and old pilot comparisons. | Archive or heavily modify |
| `code/frontier_experiments/plot_frontier.py` | Plots Pareto frontier from optimized partition enumeration. | Archive for historical development |
| `code/exhaustive_verification/plot_bound_tightness.py` | Plots indexed-bound tightness from exact verifier rows. | Reuse with modification for theory verification if needed |

## Correct rule-based implementation status

An implementation equivalent to the requested `form_platoons(release_times_by_approach, threshold, max_platoon_size=None)` already exists as:

```python
code/frontier_experiments/partition_methods.py::release_gap_threshold_partition(
    instance,
    threshold,
    max_platoon_size=None,
)
```

Behavior check:

- Preserves FIFO order: yes; it emits contiguous block sizes in original release order.
- Processes each approach independently: yes; it loops over `instance.releases`.
- Uses consecutive release-time gaps: yes; it checks `right - left`.
- Starts a new platoon when threshold is exceeded: yes; `can_join` becomes false.
- Starts a new platoon when the size cap is reached: yes; `block_size >= max_platoon_size` prevents joining.
- Avoids Gurobi and global search: yes.
- Runtime is approximately linear in vehicle count: yes; one pass over consecutive gaps.

Recommended standardization:

- Keep `release_gap_threshold_partition` as the core implementation.
- Add small wrappers or method labels for `NP`, `CHP`, and `PP` in the next implementation phase:
  - `NP`: `singleton_partition(instance.counts)`.
  - `CHP`: `release_gap_threshold_partition(instance, threshold, max_platoon_size=None)`.
  - `PP`: `release_gap_threshold_partition(instance, threshold, max_platoon_size=P_max)`.
- Add explicit tests for threshold-only CHP with no cap and PP with a finite cap across multiple approaches.

## Current experiment and result audit

| Experiment/result family | What it evaluates | Uses optimized partitioning? | Valid for NP/CHP/PP? | Must rerun? | Plotting reuse |
|---|---|---:|---:|---:|---|
| Bound-selected versus oracle tightness in `paper/sections/experiments.tex` and `results/exhaustive_verification/indexed/tightness_*` | Small exact comparison of minimizing \(B_{\mathrm{idx}}\) versus actual-gap oracle under dimension budgets. | Yes for selector/oracle framing. | Not as PP evidence; useful only as historical/theory-support context. | Yes if included in new story; redesign as rule-level verification over \((\delta,P_{\max})\). | `plot_bound_tightness.py` can be modified. |
| Dimension-budget experiments in `experiment_suite.py`, `scalability_suite.py`, and `fair_dimension_comparison.csv` | Methods selected to satisfy common ordering-variable budgets. | Yes for `proposed_bound_aware`; threshold baseline also selected from candidate thresholds to match dimension. | No; not the fixed NP/CHP/PP comparison. | Yes. | Aggregation and grouped bar mechanics reusable. |
| Loss-budget experiments in `frontier_driver.py`, `partition_selection.py`, and `loss_budget_solutions.csv` | Minimize dimension subject to indexed-bound budget. | Yes. | No. | Yes if any analogous result is desired; otherwise archive. | Mostly archive. |
| Optimized frontier experiments in `frontier_driver.py`, `plot_frontier.py`, `plot_suite.py`, and `complete_frontier.csv` | Nondominated or budget-selected \(C(\Pi)\)-\(B_{\mathrm{idx}}\) partitions. | Yes. | No. | Replace with transparent grid over \((\delta,P_{\max})\). | Plot style reusable; frontier logic not reusable. |
| Current scalability experiments in `results/frontier_experiments/scalability_*` | Vehicle-level plus optimized bound-aware, fixed-size, and threshold-closest-dimension methods. | Yes. | No; vehicle-level rows can inform feasibility expectations only. | Yes. | `plot_scalability_summary.py` reusable after method remapping and schema changes. |
| Current MIP-gap plots | Terminal solver MIP gap for old method families. | Indirectly yes. | No. | Yes. | Reuse plotting pattern. |
| Runtime plots | End-to-end time including old partition-selection solve. | Yes for proposed method. | No. | Yes, with `formation_time_ms` separated from scheduling time. | Reuse plotting pattern. |
| Node-count plots | Branch-and-bound node count for old downstream models. | Indirectly yes. | No. | Yes. | Reuse plotting pattern. |
| Dimension-reduction plots | Ordering-variable count for old method families. | Yes. | No. | Yes. | Reuse plotting pattern. |

Do not relabel old `proposed_bound_aware` results as PP.

## Proposed unified result schema

Use one row per `(seed, scenario, method, threshold, max_platoon_size)` run:

| Field | Meaning and availability |
|---|---|
| `seed` | Random seed for the traffic instance. |
| `N` | Total vehicles. |
| `L` | Number of approaches. |
| `arrival_rate` | Arrival-rate parameter when the generator has one; otherwise blank/null with arrival mode recorded in metadata. |
| `h_F` | Following headway. |
| `h_S` | Switching headway. |
| `threshold` | Critical headway \(\delta\); null for NP if not applicable. |
| `max_platoon_size` | Finite \(P_{\max}\) for PP; null or `N`/large sentinel for CHP; `1` for NP if convenient. |
| `method` | One of `NP`, `CHP`, `PP`. |
| `number_of_platoons` | Total scheduling units \(K\). |
| `ordering_variable_count` | \(\sum_{l<l'}K_lK_{l'}\). |
| `formation_time_ms` | Wall time for rule-based platoon formation only. |
| `model_build_time_s` | Downstream scheduling model construction time. |
| `solve_time_s` | Downstream solver runtime. |
| `end_to_end_time_s` | Formation plus model build plus solve. |
| `status` | Downstream solver status. |
| `objective` | Average delay, or total delay if a separate `objective_units` field is added. Prefer average delay for manuscript alignment. |
| `actual_optimality_gap` | Available only when the NP optimum is known; PP/CHP objective minus NP optimal objective. |
| `terminal_mip_gap` | Solver terminal MIP gap. This is not the platooning-induced optimality gap. |
| `node_count` | Solver branch-and-bound node count. |
| `partition_specific_upper_bound` | \(\widehat{G}(\Pi)\), computed from the actual partition. |
| `rule_level_upper_bound` | \(\widehat{G}(\delta,P_{\max})\), computed from rule parameters. |

Implementation note: `metrics.partition_metrics` already computes ordering variables and \(\widehat{G}(\Pi)\). A new helper should compute the rule-level bound from `N`, `hF`, `hS`, `threshold`, and `max_platoon_size`.
