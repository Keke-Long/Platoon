# Platoon Scheduling Handoff

Current active branch: `agent/restore-rule-based-platooning-clean`.

## Research Objective

The repository supports a manuscript on performance-guaranteed platooning as a preprocessing step for vehicle scheduling at a general conflict area. The active theory is the FIFO-indexed platoon loss bound, and the active computational study is the hS=3 NP/CHP/PP formal experiment grid. Gurobi remains the downstream MILP optimizer.

Old frontier, optimized-partition, dimension-budget, complete-frontier, sampled-budget, and hS=2 workflows were removed because they do not match the final manuscript design.

The manuscript method section has been aligned with the active rule-based implementation: PP is the threshold-and-cap platooning rule using `delta` and `Pmax`, not a separate partition-search method.

The Chapter 5 figure source of truth is `code/frontier_experiments/CHAPTER5_FIGURE_SPEC.md`; do not change figure axes, plot types, encodings, or aggregation rules without explicit project-lead approval.

Arrival-rate convention: `lambda` now means the total vehicle arrival rate into the entire conflict area. For `L=4`, each approach is generated independently with per-approach Poisson rate `lambda/4`. The approved total-arrival-rate grid is `{0.5, 1.0, 1.5, 2.0, 2.5}` veh/s.

## Uniform 600-Second Experiment State

- `N=20`: complete under the new 600-second, 10-replication design; all 50 NP, 200 CHP, and 800 PP rows are optimal, with zero bound violations and zero delay-order failures.
- `N=40`: complete under the new design; NP has 11 optimal and 39 time-limit rows, CHP has 200 optimal rows, and PP has 793 optimal and 7 time-limit rows. The 176 exact-gap-checkable PP rows have zero bound violations and zero delay-order failures.
- `N=60`: complete under the new design; NP has 8 optimal and 42 time-limit rows, CHP has 185 optimal and 15 time-limit rows, and PP has 560 optimal and 240 time-limit rows. The 128 exact-gap-checkable PP rows have zero bound violations and zero delay-order failures.
- `N=80`: complete under the new design; NP has 4 optimal and 46 time-limit rows, CHP has 161 optimal and 39 time-limit rows, and PP has 393 optimal and 407 time-limit rows. The 64 exact-gap-checkable PP rows have zero bound violations and zero delay-order failures.

All NP, CHP, and PP models now use one common 600-second maximum time limit. There is no recovery stage. Gurobi stops immediately when optimality is proved, and only unresolved cases may later be rerun with a longer limit.

Current total-arrival-rate state:

- old `arrival_rate=0.4` rows are reused and relabeled as total `lambda=1.5` with per-approach rate `0.375`;
- old `arrival_rate=0.7` rows are reused and relabeled as total `lambda=2.5` with per-approach rate `0.625`;
- old `arrival_rate=1.0` rows are deleted and not used;
- all five rates are complete for `N={20,40,60,80}`.

This remapping is an approved project decision. Treat the reused `lambda={1.5,2.5}` rows as final and do not rerun them solely to replace the historical rate labels.

The legacy 30-second aggregates are retained as source data. For the first 10 replications of `lambda={1.5,2.5}`, rows already proved optimal may be migrated into the new result set; unresolved rows are rerun for up to 600 seconds on the same stored instances.

## Next Experiment Order

1. Compile and audit the manuscript when a LaTeX toolchain is available.

## Operational Sources

- `code/frontier_experiments/EXPERIMENT_DESIGN.md` is the source of truth for the scientific grid and metric definitions.
- `code/frontier_experiments/CHAPTER5_FIGURE_SPEC.md` is the source of truth for paper-facing figures.
- `code/frontier_experiments/FORMAL_HS3_HANDOFF.md` is the source of truth for execution commands, result paths, aggregation, plotting, and validation.
- `code/exhaustive_verification/README.md` is the source of truth for exact small-instance verification.
- `notes/final_experiment_summary.md` is the concise final summary of the completed `N={20,40,60}` study.

Keep operational commands in the corresponding source document rather than copying them back into this project-level handoff.

## Known Limitations

- Checkpoints are intentionally ignored and not committed. The pushed safety tag `pre-handoff-cleanup-20260712` preserves the earlier committed checkpoint state if historical-state restoration is needed.
- The current environment may not have LaTeX installed; manuscript compilation requires `latexmk` or `pdflatex`.
- Gurobi-backed tests require a reachable Gurobi runtime/token service. In an offline environment, those tests are skipped by the local test runner.
- Run only one aggregate writer at a time. Parallel experiment execution must use `--checkpoint-only` chunks followed by one aggregation pass.
