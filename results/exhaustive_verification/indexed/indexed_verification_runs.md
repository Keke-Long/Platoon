# FIFO-Indexed Verification Runs

All runs used exact integer objective comparisons. Deterministic runs enumerate all FIFO sequences and all contiguous partitions in their stated domains. Random-exact runs sample instances and partitions without replacement within each traffic instance, but still compute exact optima for every sampled case.

No counterexample was found in the tested deterministic and random-exact domains. These runs are computational evidence only; the theorem relies on the analytical proof.

| Kind | Run | Instances | Partitions | Vehicle seq evals | Platoon seq evals | Repair traces | Repair steps | Violations | Equality cases | Max gap/indexed | Max gap/index-free | Indexed reduction | Runtime s |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| deterministic | smoke_deterministic | 392 | 1,152 | 1,744 | 3,664 | 1,152 | 100 | 0 | 1,054 | 2/2 | 4/6 | 46.15% | 0.028 |
| random_exact | smoke_random | 25 | 91 | 619 | 955 | 91 | 15 | 0 | 59 | 1/1 | 1/2 | 39.90% | 0.006 |
| deterministic | deterministic_L2_n4_N7_r6 | 192,423 | 4,499,523 | 4,874,226 | 36,998,430 | 4,499,523 | 1,395,323 | 0 | 2,145,471 | 2/2 | 8/10 | 35.03% | 173.308 |
| deterministic | deterministic_L3_n3_N6_r5 | 204,201 | 1,420,416 | 11,283,786 | 31,745,682 | 1,420,416 | 213,390 | 0 | 846,547 | 2/2 | 8/10 | 29.40% | 109.833 |
| random_exact | random_seed_20260710 | 1,000 | 12,294 | 350,336 | 628,458 | 12,294 | 5,584 | 0 | 3,950 | 3/3 | 4/5 | 28.82% | 3.162 |
| random_exact | random_seed_314159 | 3,000 | 21,082 | 1,041,566 | 934,871 | 21,082 | 11,646 | 0 | 5,997 | 8/8 | 10/12 | 28.39% | 7.436 |
| deterministic | deterministic_hF2_L2_n3_N6_r6 | 28,322 | 318,402 | 397,684 | 1,898,260 | 318,402 | 45,920 | 0 | 228,686 | 2/2 | 10/13 | 35.45% | 9.939 |

The optional broad `hF=2` mixed L=2,3 run was stopped because it exceeded the intended resource budget; it produced no result file. It was replaced by `deterministic_hF2_L2_n3_N6_r6`.
