# Repository Cleanup Audit for Current Manuscript and hS=3 Pipeline

Audit date: 2026-07-12

Scope: current manuscript and the active hS=3 NP/CHP/PP formal experiment
pipeline. This audit is descriptive only. No files were deleted, moved, or
renamed as part of this task.

## Verified State

- Current branch: `agent/restore-rule-based-platooning-clean`
- Branch head at audit start: `b2b4067`
- Working tree at audit start: clean
- Active formal runner: `code/frontier_experiments/rule_based_formal_hs3.py`
- Active formal plotter: `code/frontier_experiments/plot_rule_based_formal_hs3.py`
- Active downstream solver: `code/frontier_experiments/scheduling_milp.py`
- Active handoff document: `code/frontier_experiments/FORMAL_HS3_HANDOFF.md`

## Result Integrity Checks

| Check | Finding |
|---|---|
| N=20 checkpoint count | 60 files in `results/rule_based_experiments/formal_pp_hS3/checkpoints` |
| N=40 checkpoint count | 60 files in `results/rule_based_experiments/formal_pp_hS3/checkpoints` |
| Total committed checkpoint count in formal checkpoint directory | 120 files |
| N=60/N=80 partial checkpoints | None found in `formal_pp_hS3/checkpoints` |
| Aggregate `formal_comparison_rows.csv` Ns | exactly `{20,40}` |
| Aggregate `formal_rule_based_rows.csv` Ns | exactly `{20,40}` |
| Aggregate `formal_bound_rows.csv` Ns | exactly `{20,40}` |
| Aggregate row count | 2520 initial rows, 1920 PP rows |
| Aggregate duplicate keys | 0 |
| Aggregate bound violations | 0 among currently checkable rows |
| Aggregate delay-order failures | 0 among currently checkable rows |

## Manuscript Reference Checks

- `paper/sections/experiments.tex` references only these formal experiment
  figure PDFs:
  - `figures/bound_validation_actual_vs_upper.pdf`
  - `figures/experimental_tradeoff_solve_time_gap.pdf`
  - `figures/pp_delay_vs_threshold_density.pdf`
  - `figures/pp_time_and_platoon_count.pdf`
  - `figures/gurobi_solution_quality_over_time.pdf`
- `paper/sections/introduction.tex` references `figures/Picture1.png`.
- `paper/sections/formulation.tex` references `figures/Picture2.png`.
- No current `\includegraphics` command references old frontier/scalability
  figures such as `runtime_by_scale.png`, `dimension_reduction_by_scale.png`,
  `mip_gap_by_scale.png`, `nodes_by_scale.png`, or
  `optimality_rate_by_scale.png`.
- The current manuscript still contains non-final process language in
  `paper/sections/experiments.tex` about N=20-only and later larger-scale
  results. Per the latest project direction, this should be removed when the
  manuscript is next edited, but this audit task did not modify manuscript
  files.
- The current abstract and conclusion still contain older scalability wording
  about N=20/30/40 and old percentage ranges. These are not figure references,
  but they should be reconciled with the final formal hS=3 experiment story
  before submission.

## FORMAL_HS3_HANDOFF.md Accuracy

`code/frontier_experiments/FORMAL_HS3_HANDOFF.md` is useful, but it is now
partially stale:

- It says the current instruction is to run only the N=40 initial run next.
  That run is now complete.
- It describes N=40 as an active/current run and says aggregate files are dirty
  while the run is active. The working tree is now clean and N=40 has been
  committed.
- It says Figure E is provisional while only N=20 trajectories are available.
  The formal plot metadata now selects an N=40 representative instance.
- It does not describe the checkpoint-only parallel chunk mode added in
  `0aed831`.

Recommended action: keep the handoff file, but update it before external
handoff so it reflects the completed N=40 initial run and the parallel
checkpoint-only workflow.

## Cleanup Audit Table

| Path | Type | Referenced by current manuscript | Imported or called by active hS3 pipeline | Still scientifically needed | Recommended action | Reason |
|---|---|---:|---:|---:|---|---|
| `paper/main.tex` | documentation | yes | no | yes | keep | Official manuscript entry point. |
| `paper/sections/formulation.tex` | documentation | yes | no | yes | keep | Defines model used by proof and experiments. |
| `paper/sections/theoretical_analysis.tex` | documentation | yes | no | yes | keep | Contains FIFO-indexed loss-bound proof. |
| `paper/sections/dimension_reduction.tex` | documentation | yes | no | yes | keep | Current manuscript section, but should be checked for consistency with rule-based PP rather than optimized partition selection. |
| `paper/sections/experiments.tex` | documentation | yes | no | yes | keep | Current experiment section; needs future final-result wording cleanup, not deletion. |
| `paper/figures/Picture1.png` | figure | yes | no | yes | keep | Referenced by introduction. |
| `paper/figures/Picture2.png` | figure | yes | no | yes | keep | Referenced by formulation. |
| `paper/figures/bound_validation_actual_vs_upper.pdf` | figure | yes | no | yes | keep | Paper-facing Figure A. |
| `paper/figures/experimental_tradeoff_solve_time_gap.pdf` | figure | yes | no | yes | keep | Paper-facing Figure B. |
| `paper/figures/pp_delay_vs_threshold_density.pdf` | figure | yes | no | yes | keep | Paper-facing Figure C. |
| `paper/figures/pp_time_and_platoon_count.pdf` | figure | yes | no | yes | keep | Paper-facing Figure D. |
| `paper/figures/gurobi_solution_quality_over_time.pdf` | figure | yes | no | yes | keep | Paper-facing Figure E. |
| `paper/figures/bound_validation_actual_vs_upper.png` | figure | no | no | uncertain | archive | Duplicate PNG of a PDF used by manuscript; useful for quick preview but not required for LaTeX. |
| `paper/figures/experimental_tradeoff_solve_time_gap.png` | figure | no | no | uncertain | archive | Duplicate PNG of a PDF used by manuscript; useful for preview only. |
| `paper/figures/pp_delay_vs_threshold_density.png` | figure | no | no | uncertain | archive | Duplicate PNG of a PDF used by manuscript; useful for preview only. |
| `paper/figures/pp_time_and_platoon_count.png` | figure | no | no | uncertain | archive | Duplicate PNG of a PDF used by manuscript; useful for preview only. |
| `paper/figures/gurobi_solution_quality_over_time.png` | figure | no | no | uncertain | archive | Duplicate PNG of a PDF used by manuscript; useful for preview only. |
| `paper/figures/indexed_bound_tightness.pdf` | figure | no | no | uncertain | archive | Historical/theory-support figure not referenced by current manuscript. |
| `paper/figures/indexed_bound_tightness.png` | figure | no | no | uncertain | archive | Historical duplicate not referenced by current manuscript. |
| `paper/figures/dimension_reduction_by_scale.png` | figure | no | no | no | archive | Old scalability/frontier-style figure not referenced by current manuscript. |
| `paper/figures/runtime_by_scale.png` | figure | no | no | no | archive | Old scalability figure not referenced by current manuscript. |
| `paper/figures/mip_gap_by_scale.png` | figure | no | no | no | archive | Old scalability figure not referenced by current manuscript. |
| `paper/figures/nodes_by_scale.png` | figure | no | no | no | archive | Old scalability figure not referenced by current manuscript. |
| `paper/figures/optimality_rate_by_scale.png` | figure | no | no | no | archive | Old scalability figure not referenced by current manuscript. |
| `code/frontier_experiments/rule_based_formal_hs3.py` | code | no | yes | yes | keep | Active formal hS=3 NP/CHP/PP runner. |
| `code/frontier_experiments/plot_rule_based_formal_hs3.py` | code | no | yes | yes | keep | Active formal hS=3 figure generator. |
| `code/frontier_experiments/scheduling_milp.py` | code | no | yes | yes | keep | Active downstream Gurobi scheduling model. |
| `code/frontier_experiments/partition_methods.py` | code | no | yes | yes | keep | Active NP/CHP/PP partition formation logic. |
| `code/frontier_experiments/metrics.py` | code | no | yes | yes | keep | Active ordering-variable, dimension-reduction, and rule-bound metrics. |
| `code/exhaustive_verification/model.py` and related model/enumeration modules | code | no | yes | yes | keep | `rule_based_formal_hs3.py` imports `model.py`; exact verification code also preserves theorem support. |
| `code/frontier_experiments/FORMAL_HS3_HANDOFF.md` | documentation | no | no | yes | keep | Handoff document, but now needs state refresh after N=40 completion. |
| `code/frontier_experiments/EXPERIMENT_DESIGN.md` | documentation | no | no | yes | keep | Frozen formal design source; `Current status` section is stale and should be refreshed. |
| `code/frontier_experiments/README.md` | documentation | no | no | uncertain | archive | Mostly documents old dimension-loss frontier and scalability workflows; keep only if clearly marked historical. |
| `code/frontier_experiments/frontier_driver.py` | code | no | no | uncertain | archive | Old complete frontier/loss-budget driver; not called by hS=3 rule-based pipeline. |
| `code/frontier_experiments/partition_selection.py` | code | no | no | uncertain | archive | Implements optimized loss-budget/size-budget partition selection; explicitly excluded from active hS=3 PP. |
| `code/frontier_experiments/legacy_partition_methods.py` | code | no | no | uncertain | archive | Wraps optimized partition-selection methods; not active. |
| `code/frontier_experiments/experiment_suite.py` | code | no | no | uncertain | archive | Old integrated frontier experiment suite using optimized/budget methods. |
| `code/frontier_experiments/scalability_suite.py` | code | no | no | uncertain | archive | Old scalability code using `proposed_bound_aware`, `fixed_size_closest_dimension`, and `threshold_closest_dimension`. |
| `code/frontier_experiments/scalability_chunk_runner.py` | code | no | no | uncertain | archive | Old chunk runner for scalability suite, not active formal hS=3 runner. |
| `code/frontier_experiments/run_scalability_batches.py` | code | no | no | uncertain | archive | Old scalability batch launcher, not active. |
| `code/frontier_experiments/aggregate_scalability_batches.py` | code | no | no | uncertain | archive | Old scalability aggregation utility, not active. |
| `code/frontier_experiments/aggregate_scalability_chunks.py` | code | no | no | uncertain | archive | Old scalability chunk aggregation utility, not active. |
| `code/frontier_experiments/plot_scalability_summary.py` | code | no | no | no | archive | Plots old method families including `proposed_bound_aware`, `fixed_size_closest_dimension`, and `threshold_closest_dimension`. |
| `code/frontier_experiments/plot_suite.py` | code | no | no | no | archive | Plots old integrated frontier outputs. |
| `code/frontier_experiments/plot_frontier.py` | code | no | no | no | archive | Plots old dimension-loss frontiers. |
| `code/frontier_experiments/plot_rule_based_diagnostics.py` | code | no | no | uncertain | archive | Earlier diagnostics plotter, not active hS=3 formal figure generator. |
| `code/frontier_experiments/rule_based_formal_comparison.py` | code | no | no | no | archive | Earlier formal unified runner with different grid; superseded by `rule_based_formal_hs3.py`. |
| `code/frontier_experiments/rule_based_formal_theory.py` | code | no | no | uncertain | archive | Earlier theory/formal exact runner; useful historically, not active formal hS=3 pipeline. |
| `code/frontier_experiments/rule_based_theory_verification.py` | code | no | no | uncertain | archive | Earlier verification runner; not active. |
| `code/frontier_experiments/rule_based_basic_comparison.py` | code | no | no | no | archive | Basic smoke/comparison runner superseded by formal hS=3 runner. |
| `code/frontier_experiments/tests/test_plot_rule_based_formal_hs3.py` | test | no | yes | yes | keep | Active formal plotter and trajectory-selection tests. |
| `code/frontier_experiments/tests/test_partition_methods.py` | test | no | yes | yes | keep | Tests active partition primitives used by hS=3 runner. |
| `code/frontier_experiments/tests/test_metrics.py` | test | no | yes | yes | keep | Tests active metric utilities used by hS=3 runner. |
| `code/frontier_experiments/tests/test_scheduling_milp.py` | test | no | yes | yes | keep | Tests active downstream MILP implementation. |
| `code/frontier_experiments/tests/test_partition_selection.py` | test | no | no | uncertain | archive | Tests old optimized partition-selection module. |
| `code/frontier_experiments/tests/test_scalability_suite.py` | test | no | no | uncertain | archive | Tests old scalability suite and old method families. |
| `code/frontier_experiments/tests/test_scalability_chunks.py` | test | no | no | uncertain | archive | Tests old scalability chunk runner/aggregator. |
| `code/frontier_experiments/tests/run_tests.py` | test | no | no | yes | keep | General local fallback test runner; still useful if `pytest` unavailable. |
| `code/frontier_experiments/__pycache__/` | code | no | no | no | delete | Generated Python bytecode cache; should not be committed or preserved. |
| `results/rule_based_experiments/formal_pp_hS3/formal_comparison_rows.csv` | result | no | yes | yes | keep | Active aggregate NP/CHP/PP row file for N={20,40}. |
| `results/rule_based_experiments/formal_pp_hS3/formal_comparison_summary.csv` | result | no | yes | yes | keep | Active aggregate summary for formal comparison. |
| `results/rule_based_experiments/formal_pp_hS3/formal_comparison_summary.json` | result | no | yes | yes | keep | Active machine-readable checks and summary. |
| `results/rule_based_experiments/formal_pp_hS3/formal_rule_based_rows.csv` | result | no | yes | uncertain | archive | Duplicate of `formal_comparison_rows.csv`; retained for backward compatibility but redundant. |
| `results/rule_based_experiments/formal_pp_hS3/formal_rule_based_summary.csv` | result | no | yes | uncertain | archive | Duplicate of `formal_comparison_summary.csv`; retained for backward compatibility but redundant. |
| `results/rule_based_experiments/formal_pp_hS3/formal_rule_based_summary.json` | result | no | yes | uncertain | archive | Duplicate of `formal_comparison_summary.json`; retained for backward compatibility but redundant. |
| `results/rule_based_experiments/formal_pp_hS3/gurobi_incumbent_trajectories.csv` | result | no | yes | yes | keep | Active source for Figure E. |
| `results/rule_based_experiments/formal_pp_hS3/checkpoints/N20_*.json` | checkpoint | no | yes | yes | keep | Committed exact completed checkpoints for N=20; required for resume/reaggregation provenance. |
| `results/rule_based_experiments/formal_pp_hS3/checkpoints/N40_*.json` | checkpoint | no | yes | yes | keep | Committed completed checkpoints for N=40; required for resume/reaggregation provenance. |
| `results/rule_based_experiments/formal_bound_hS3/formal_bound_rows.csv` | result | no | yes | yes | keep | Active PP bound rows for formal hS=3. |
| `results/rule_based_experiments/formal_bound_hS3/formal_bound_checkable_rows.csv` | result | no | yes | yes | keep | Active exact bound-check subset; currently N=20 only. |
| `results/rule_based_experiments/formal_bound_hS3/formal_bound_summary.json` | result | no | yes | yes | keep | Active bound summary and checks. |
| `results/rule_based_experiments/formal_bound_hS3/config_manifest.json` | result | no | yes | yes | keep | Active configuration manifest. |
| `results/rule_based_experiments/formal_np_recovery_600s_hS3/` | result | no | yes | yes | keep | Active designated recovery output directory; currently no recovery rows because recovery has not been launched. |
| `results/rule_based_experiments/formal_figures_hS3/*.pdf` | figure | no | yes | yes | keep | Active generated formal figures used to copy paper-facing PDFs. |
| `results/rule_based_experiments/formal_figures_hS3/*.png` | figure | no | yes | uncertain | archive | Preview duplicates of active PDFs; useful for inspection, not manuscript-required. |
| `results/rule_based_experiments/formal_figures_hS3/*_metadata.json` | result | no | yes | yes | keep | Captures aggregation/selection metadata for formal figures. |
| `results/rule_based_experiments/formal_figures_hS3/.mplconfig/` | result | no | no | no | delete | Matplotlib runtime cache/config directory. |
| `results/rule_based_experiments/formal_pilot/` | result | no | no | no | archive | Earlier pilot result set, superseded by hS=3 formal pipeline. |
| `results/rule_based_experiments/formal_unified/` | result | no | no | no | archive | Archived preliminary run with different hS/grid; not current manuscript evidence. |
| `results/rule_based_experiments/smoke_hS3/` | result | no | no | uncertain | archive | Smoke result set; useful for debugging provenance but not current manuscript evidence. |
| `results/rule_based_experiments/basic_smoke/` | result | no | no | no | archive | Old smoke output. |
| `results/rule_based_experiments/theory_smoke/` | result | no | no | uncertain | archive | Old theory smoke output, not active formal result. |
| `results/frontier_experiments/pilot_30/` | result | no | no | no | archive | Old optimized/frontier pilot results. |
| `results/frontier_experiments/scalability_final/` | result | no | no | no | archive | Old scalability/budget result tree; not referenced by current manuscript figures. |
| `results/frontier_experiments/scalability_checkpointed/` | result | no | no | no | archive | Old checkpointed scalability results; not active hS=3 formal output. |
| `results/frontier_experiments/scalability_checkpointed/paper_scalability/` | result | no | no | no | archive | Old paper-scalability figure/data set; no current figure references. |
| `results/frontier_experiments/scalability_pilot_wls/` | result | no | no | no | archive | Old scalability pilot. |
| `results/frontier_experiments/scalability_stress_l4_wls/` | result | no | no | no | archive | Old scalability stress result. |
| `results/frontier_experiments/smoke*/` | result | no | no | no | archive | Old frontier/scalability smoke outputs. |
| `results/exhaustive_verification/indexed/*` | result | no | no | yes | keep | Supports theorem verification/proof audit; not part of hS=3 formal pipeline but scientifically relevant. |
| `results/exhaustive_verification/indexed/tightness_L3_counts_3_2_1_r5/` | result | no | no | yes | keep | Indexed-bound tightness/equality evidence; scientifically useful even if not currently figure-referenced. |
| `results/exhaustive_verification/random_seed_*` | result | no | no | yes | keep | Historical exact/random verification evidence for theorem support. |
| `code/exhaustive_verification/plot_bound_tightness.py` | code | no | no | yes | keep | Generates indexed-bound tightness artifacts; useful for theorem support. |
| `code/exhaustive_verification/tests/` | test | no | no | yes | keep | Tests exact verification model/enumeration logic. |
| `paper/notes/code_and_experiment_audit.md` | documentation | no | no | yes | keep | Historical audit explains why optimized frontier results should not be reused as PP evidence. |
| `paper/notes/next_experiment_plan.md` | documentation | no | no | yes | keep | Documents transition plan toward rule-based PP. |
| `paper/notes/codex_corrected_direction_review.md` | documentation | no | no | yes | keep | Records correction of manuscript direction. |
| `paper/notes/phase1_sections_3_6_revision_map.md` | documentation | no | no | yes | keep | Records planned removal of optimized partition-selection framing. |
| `EXPERIMENT_HANDOFF.md` | documentation | no | no | uncertain | archive | Historical index-free/exhaustive verification handoff; superseded for current formal hS=3 pipeline. |

## Specific Findings for Requested Attention Areas

1. Old frontier and dimension-budget code:
   `frontier_driver.py`, `experiment_suite.py`, `scalability_suite.py`,
   `run_scalability_batches.py`, `scalability_chunk_runner.py`, and related
   aggregators/plotters are not called by the active hS=3 pipeline. They should
   be archived rather than kept in the active experiment namespace.

2. `proposed_bound_aware` partition-selection code:
   The method family appears in old scalability code and plots. It is not used
   by `rule_based_formal_hs3.py`; recommended action is archive.

3. `fixed_size_closest_dimension` and `threshold_closest_dimension` baselines:
   These appear in old scalability code and tests. They are not active NP/CHP/PP
   formal baselines; recommended action is archive.

4. Complete-frontier and sampled-budget scripts:
   `frontier_driver.py`, `partition_selection.py`, `plot_frontier.py`,
   `plot_suite.py`, and scalability `complete_frontier` generation are not
   active; archive.

5. Old scalability result directories:
   `results/frontier_experiments/*` is not referenced by current manuscript
   figures and is not active hS=3 output; archive.

6. Indexed-bound tightness scripts and results:
   Keep. They are not part of hS=3 NP/CHP/PP experiments but remain
   scientifically useful for theorem support and proof audit.

7. Duplicate `formal_comparison_*` and `formal_rule_based_*` files:
   `formal_rule_based_*` duplicates `formal_comparison_*` in the active output
   directory. Recommended action is archive or remove after dependent scripts
   are updated to use only `formal_comparison_*`.

8. Committed checkpoint directories:
   The active formal checkpoint directory contains exactly 120 committed
   checkpoint files: 60 for N=20 and 60 for N=40. Keep for provenance and
   reaggregation. No N=60/N=80 checkpoint files exist.

9. Duplicate PDF/PNG files under `paper/figures`:
   The manuscript uses the PDF formal figures. PNG duplicates are useful for
   preview but not required by LaTeX. Old scale figures under `paper/figures`
   are unreferenced and should be archived.

10. Unused tests and old README/design documents:
    Keep tests for active `partition_methods`, `metrics`, `scheduling_milp`,
    and formal plotting. Archive tests for old partition selection and
    scalability suites. `EXPERIMENT_DESIGN.md` and `FORMAL_HS3_HANDOFF.md`
    should be updated rather than deleted; `README.md` mostly describes old
    frontier work and should be archived or rewritten.

## Recommended Cleanup Sequence

1. Update manuscript text to remove process/provisional language only when the
   next manuscript-editing task is explicitly requested.
2. Update `FORMAL_HS3_HANDOFF.md` and `EXPERIMENT_DESIGN.md` to reflect that
   N=40 initial results are complete and checkpoint-only parallel chunks exist.
3. Create an archive directory for old frontier/scalability code and old result
   trees, preserving provenance but separating them from the active formal
   hS=3 pipeline.
4. Remove generated runtime caches such as `__pycache__/` and
   `.mplconfig/` from active directories.
5. Consolidate duplicate `formal_rule_based_*` outputs after confirming no
   active script still reads them.
6. Keep committed N=20/N=40 checkpoints until a smaller, documented provenance
   format is agreed upon.
