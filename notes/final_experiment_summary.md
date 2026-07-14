# Final Formal Experiment Summary

## Scope

The final results cover `N={20,40,60,80}`. Each scale contains five total arrival rates and 10 traffic replications, for 200 traffic instances and 4,200 downstream model rows. Every model has a 600-second maximum time limit and 12 Gurobi threads.

## Computational Results

| N | NP optimal | CHP optimal | PP optimal | NP mean time (s) | CHP mean time (s) | PP mean time (s) | PP mean dimension reduction |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 20 | 100.0% | 100.0% | 100.0% | 3.77 | 0.02 | 0.04 | 74.4% |
| 40 | 22.0% | 100.0% | 99.1% | 482.88 | 1.65 | 26.54 | 78.8% |
| 60 | 16.0% | 92.5% | 70.0% | 521.71 | 70.28 | 204.40 | 80.0% |
| 80 | 8.0% | 80.5% | 49.1% | 566.50 | 133.49 | 338.09 | 81.0% |

Across all scales, NP proves 73 of 200 models optimal, CHP proves 746 of 800 optimal, and PP proves 2,546 of 3,200 optimal. PP formation time is negligible: its mean is below 0.007 ms at every tested scale.

## Bound Validation

| N | Checked instances | Checked PP rows | Mean actual gap (s) | Median gap (s) | Maximum gap (s) | Violations |
|---:|---:|---:|---:|---:|---:|---:|
| 20 | 50 | 800 | 0.471 | 0.000 | 6.050 | 0 |
| 40 | 11 | 176 | 0.494 | 0.100 | 5.475 | 0 |
| 60 | 8 | 128 | 0.507 | 0.275 | 2.950 | 0 |
| 80 | 4 | 64 | 0.373 | 0.206 | 1.888 | 0 |
| All | 73 | 1,168 | 0.473 | 0.050 | 6.050 | 0 |

The pooled mean rule-level upper bound is 84.004 s and the minimum observed slack is 6.950 s. The bound is valid on the tested exact subset but is conservative. The exact subset shrinks with `N` because unresolved NP rows cannot provide exact reference delays.

All 1,168 exact-check rows also satisfy `D_NP <= D_PP <= D_CHP`. Raw Gurobi objectives remain in the result CSV. Cross-model checks canonicalize proven-optimal average delays to the `1/N` lattice implied by integer total delay, preventing Big-M feasibility tolerances from creating artificial negative gaps.

## Sources

- Comparison rows: `results/rule_based_experiments/formal_pp_hS3_600s_r10/formal_comparison_rows.csv`
- Bound rows: `results/rule_based_experiments/formal_bound_hS3_600s_r10/formal_bound_rows.csv`
- Aggregate summary: `results/rule_based_experiments/formal_pp_hS3_600s_r10/formal_comparison_summary.json`
- Figures: `results/rule_based_experiments/formal_figures_hS3_600s_r10/`
