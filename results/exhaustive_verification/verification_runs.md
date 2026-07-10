# Verification Runs

All listed runs used exact integer objective comparisons. Deterministic runs enumerate all FIFO sequences and all contiguous partitions in their stated domain. Random-exact runs sample instances and partitions, but still compute exact optima for every sampled case.

| Kind | Run | Instances | Partitions | Vehicle seq evals | Platoon seq evals | Local repairs | Violations | Max gap/bound | Runtime s |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| deterministic | L2_n2_N4_release3 | 588 | 1,728 | 2,616 | 5,496 | 2,040 | 0 | 4/6 | 0.035 |
| deterministic | L2_n3_N6_release4 | 9,075 | 91,875 | 114,750 | 530,550 | 197,700 | 0 | 6/8 | 2.381 |
| deterministic | L3_n2_N6_release3 | 8,232 | 41,472 | 396,432 | 909,072 | 678,240 | 0 | 7/10 | 5.479 |
| deterministic | L3_n3_N7_release3 | 57,912 | 686,592 | 7,114,032 | 25,439,472 | 16,492,320 | 0 | 9/12 | 129.188 |
| deterministic | L2_n5_N9_release3 | 37,467 | 2,506,752 | 2,417,190 | 38,059,002 | 7,526,706 | 0 | 8/10 | 109.038 |
| deterministic | deterministic_L2_n4_N7_r6 | 192,423 | 4,499,523 | 4,874,226 | 36,998,430 | 10,971,492 | 0 | 8/10 | 134.974 |
| deterministic | deterministic_L3_n3_N6_r5 | 204,201 | 1,420,416 | 11,283,786 | 31,745,682 | 18,890,172 | 0 | 8/10 | 166.706 |
| random_exact | random_seed_20260710 | 1,000 | 12,332 | 361,540 | 614,194 | 1,406,125 | 0 | 6/7 | 8.737 |
| random_exact | random_seed_314159 | 3,000 | 21,197 | 1,055,870 | 934,357 | 4,081,086 | 0 | 10/12 | 25.816 |

No counterexample was found in these tested domains. This remains computational evidence, not a proof.
