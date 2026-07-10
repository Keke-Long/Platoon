# Staged Exhaustive Verification Runs

All runs used `hF = 1`, `hS in {2, 3, 4}`, exact integer delay arithmetic, all FIFO interleavings, and all contiguous partitions in the stated domain. No local repair violation or global candidate-bound violation was found in these tested domains.

| Run | Traffic instances | Partitions | Vehicle seq evals | Platoon seq evals | Local repairs | Max gap/bound |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| L=2, max_n=2, N<=4, r=0..3 | 588 | 1,728 | 2,616 | 5,496 | 2,040 | 4/6 |
| L=2, max_n=3, N<=6, r=0..4 | 9,075 | 91,875 | 114,750 | 530,550 | 197,700 | 6/8 |
| L=3, max_n=2, N<=6, r=0..3 | 8,232 | 41,472 | 396,432 | 909,072 | 678,240 | 7/10 |
| L=3, max_n=3, N<=7, r=0..3 | 57,912 | 686,592 | 7,114,032 | 25,439,472 | 16,492,320 | 9/12 |
| L=2, max_n=5, N<=9, r=0..3 | 37,467 | 2,506,752 | 2,417,190 | 38,059,002 | 7,526,706 | 8/10 |

This is numerical verification only. It does not prove the candidate theorem.

