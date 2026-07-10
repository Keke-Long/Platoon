# FIFO-Indexed Verification Runs

All runs used exact integer objective comparisons. Deterministic runs enumerate all FIFO sequences and all contiguous partitions in their stated domains. Random-exact runs sample instances and partitions without replacement within each traffic instance, but still compute exact optima for every sampled case.

No counterexample was found in the tested deterministic and random-exact domains. These runs are computational evidence only; the theorem relies on the analytical proof.

Equality cases are split into positive equality cases (`scaled_gap = scaled_indexed_bound > 0`) and zero equality cases (`scaled_gap = scaled_indexed_bound = 0`). The aggregate indexed-bound reduction is `1 - sum(B_idx)/sum(B_0)` over the listed run, not an average per-instance improvement.

| Kind | Run | Instances | Partitions | Vehicle seq evals | Platoon seq evals | Repair traces | Repair steps | Violations | Positive equality | Zero equality | Max gap/indexed | Max gap/index-free | Aggregate indexed-bound reduction | Runtime s |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| deterministic | smoke_deterministic | 392 | 1,152 | 1,744 | 3,664 | 1,152 | 100 | 0 | 60 | 994 | 2/2 | 4/6 | 46.15% | 0.026 |
| random_exact | smoke_random | 25 | 91 | 619 | 955 | 91 | 15 | 0 | 4 | 55 | 1/1 | 1/2 | 39.90% | 0.006 |
| deterministic | deterministic_L2_n4_N7_r6 | 192,423 | 4,499,523 | 4,874,226 | 36,998,430 | 4,499,523 | 1,395,323 | 0 | 93,466 | 2,052,005 | 2/2 | 8/10 | 35.03% | 169.833 |
| deterministic | deterministic_L3_n3_N6_r5 | 204,201 | 1,420,416 | 11,283,786 | 31,745,682 | 1,420,416 | 213,390 | 0 | 999 | 845,548 | 2/2 | 8/10 | 29.40% | 109.591 |
| random_exact | random_seed_20260710 | 1,000 | 12,294 | 350,336 | 628,458 | 12,294 | 5,584 | 0 | 122 | 3,828 | 3/3 | 4/5 | 28.82% | 3.076 |
| random_exact | random_seed_314159 | 3,000 | 21,082 | 1,041,566 | 934,871 | 21,082 | 11,646 | 0 | 191 | 5,806 | 8/8 | 10/12 | 28.39% | 7.682 |
| deterministic | deterministic_hF2_L2_n3_N6_r6 | 28,322 | 318,402 | 397,684 | 1,898,260 | 318,402 | 45,920 | 0 | 5,656 | 223,030 | 2/2 | 10/13 | 35.45% | 9.714 |

The optional broad `hF=2` mixed L=2,3 run was stopped because it exceeded the intended resource budget; it produced no result file. It was replaced by `deterministic_hF2_L2_n3_N6_r6`.
