# Rule-Based Platooning Experiment Design

This file is the single source of truth for Chapter 5 of the manuscript and for all future formal experiment runs on branch `agent/restore-rule-based-platooning-clean`.

Do not change the parameter grid, solver settings, figure definitions, or output meanings without first updating both this file and `paper/sections/experiments.tex`.

## Chapter 5 structure

Chapter 5 contains only two main subsections:

1. `5.1 Validation of the Rule-Level Upper Bound`
   - `5.1.1 Experiment Setting`
   - `5.1.2 Results`
2. `5.2 Validation of the Proposed Platooning Method`
   - `5.2.1 Experiment Setting`
   - `5.2.2 Results`

## Shared traffic settings

Both studies use:

- number of approaches: `L = 4`
- total vehicles: `N in {20, 40, 60, 80}`
- balanced vehicle counts across approaches
- independent Poisson arrivals on each approach
- arrival rates: `lambda in {0.4, 0.7, 1.0}` veh/s
- minimum following headway: `hF = 1 s`
- minimum switching headway: `hS = 3 s`
- platooning thresholds: `delta in {2, 4, 6, 8} s`
- maximum platoon sizes: `Pmax in {2, 4, 6, 8}`
- replications: `20`
- Gurobi threads: `12`
- reproducible instance seeds

The same generated traffic instance must be reused by NP, CHP, and every PP parameter combination.

## Methods

- `NP`: no platooning. Every vehicle remains an independent scheduling unit.
- `CHP`: conventional critical-headway platooning. Consecutive same-approach vehicles join the same platoon when their release gap is no greater than `delta`. No maximum platoon-size cap is imposed.
- `PP`: proposed platooning. The same threshold rule is used, but platoon size is capped by `Pmax`.

The active formal pipeline must not call the archived optimized-partition or dimension-budget methods.

## 5.1 Validation of the rule-level upper bound

### Purpose

Empirically check only

```text
G(Pi) <= Ghat(delta, Pmax)
```

where

```text
G(Pi) = D_PP - D_NP.
```

Do not use the partition-specific bound as the paper-facing validation target. It may remain in internal diagnostic output.

### Solver protocol

- initial downstream time limit: `30 s` per model
- NP recovery limit: `600 s` for unresolved NP models
- Gurobi threads: `12`
- PP must be proven optimal before its gap is used
- NP must be proven optimal before `D_NP` is used
- a bound check is available only when both NP and PP are proven optimal
- the 600-second recovery result may update `D_NP` and the paper-facing gap check
- the original 30-second NP status, incumbent, runtime, and MIP gap must remain preserved

### Required row-level fields

Each PP row used for 5.1 must contain:

- instance identifiers and seed
- `N`, `L`, `lambda`, `delta`, `Pmax`
- stored counts and release times
- `D_NP`
- `D_PP`
- `actual_optimality_gap`
- `rule_level_upper_bound`
- `bound_slack = rule_level_upper_bound - actual_optimality_gap`
- `bound_check_available`
- `bound_valid`
- NP and PP statuses
- original 30-second NP metrics
- optional 600-second NP recovery metrics

### Required summary statistics

Report:

- total PP rows
- valid bound-check rows
- unique instances with valid checks
- coverage rate by `(N, lambda)`
- violation count and violation rate
- mean and median actual gap
- mean and median rule-level upper bound
- mean, median, and minimum bound slack

All manuscript claims must say `among checked cases` or equivalent when coverage is incomplete.

### Required figures

#### Figure: `bound_validation_actual_vs_upper.pdf`

Purpose: show that every checked actual gap is below the rule-level upper bound.

Requirements:

- actual `G` and `Ghat` must both be visible
- colors represent `delta`
- marker shapes represent `Pmax`
- show only rows with `bound_check_available = True`
- state sample coverage in the caption or annotation
- do not call the bound tight

#### Figure: `experimental_tradeoff_solve_time_gap.pdf`

Purpose: show the empirical computation-loss trade-off.

Requirements:

- horizontal axis: downstream solve time or a clearly defined computation metric
- vertical axis: actual gap `G`
- colors represent `delta`
- marker shapes represent `Pmax`
- include only cases with an exact actual gap
- aggregate replications consistently and show uncertainty

## 5.2 Validation of the proposed PP method

### Purpose

Compare NP, CHP, and PP under the same fixed computation budget and demonstrate that PP provides an intermediate performance-computation trade-off.

### Solver protocol

- downstream time limit: `30 s` per model
- Gurobi threads: `12`
- solve NP once per traffic instance
- solve CHP once per `delta`
- solve PP once per `(delta, Pmax)`
- do not rerun NP or CHP redundantly inside the PP loop

The 30-second results are the official computation-comparison results, even if longer NP recovery runs are later available.

### Required metrics

Report:

- average vehicle delay or best incumbent objective
- proven-optimal rate
- terminal MIP gap
- downstream solve time
- end-to-end time
- model construction time
- branch-and-bound node count
- number of platoons or scheduling units
- ordering-variable count
- dimension-reduction ratio

Check

```text
D_NP <= D_PP <= D_CHP
```

only when the corresponding NP, PP, and CHP solutions are all proven optimal.

### Required figures

#### Figure: `pp_delay_vs_threshold_density.pdf`

Purpose: compare NP, CHP, and PP delay as platooning aggressiveness or traffic density increases.

Required panels:

- panel (a): average delay versus `delta`
- panel (b): average delay versus `lambda`

The figure must clearly distinguish NP, CHP, and PP. When multiple PP sizes are shown, marker shapes represent `Pmax`.

#### Figure: `pp_time_and_platoon_count.pdf`

Purpose: explain why platooning reduces computation.

Required content:

- solve time versus `delta`
- solve time versus `lambda`
- number of platoons or scheduling units versus `delta`
- number of platoons or scheduling units versus `lambda`

A four-panel figure is preferred. The same aggregation rule must be used across methods.

#### Figure: `gurobi_solution_quality_over_time.pdf`

Purpose: show how quickly usable solutions are obtained under a limited time budget.

Requirements:

- plot best-found objective or normalized incumbent quality against wall-clock time
- include NP, CHP, and representative PP settings
- choose representative PP settings only after inspecting the formal grid
- record incumbent trajectories through a Gurobi callback
- do not reconstruct trajectories from terminal results
- use the same traffic instance and solver environment for all curves

## Paper-facing tables

The manuscript must include:

1. experiment-setting table for 5.1
2. experiment-setting table for 5.2
3. bound-validation summary table
4. NP/CHP/PP performance summary table

The final two tables are generated only after the formal runs are complete.

## Output directories

Use separate directories:

```text
results/rule_based_experiments/formal_bound_hS3
results/rule_based_experiments/formal_pp_hS3
results/rule_based_experiments/formal_np_recovery_600s_hS3
results/rule_based_experiments/formal_figures_hS3
```

Never overwrite the earlier `formal_unified` results. They remain an archived preliminary run with `hS = 2` and a different parameter grid.

## Execution requirements

All formal scripts must:

- checkpoint after every completed replication or model
- support resume
- skip completed rows safely
- save the full configuration manifest
- preserve stored counts and release times
- write deterministic instance identifiers
- detect duplicate and missing replications
- report Gurobi status, runtime, MIP gap, nodes, and incumbent
- keep 30-second and 600-second NP metrics in separate fields

## Figure style

For figures involving the platooning parameters:

- different colors represent `delta`
- different marker shapes represent `Pmax`
- use the same color and marker mapping in every figure
- use readable fonts and publication-quality vector output
- save both PDF and PNG versions
- do not use the old optimized-frontier figures

## Current status

- Chapter 5 structure and experiment settings are frozen in the manuscript.
- Figure placeholders and final captions are present in `paper/sections/experiments.tex`.
- The previous `formal_unified` run is preliminary evidence only because it used `hS = 2` and `delta = {2,3,4}`.
- The new `hS = 3` formal experiments and final figures remain to be implemented and run.
