# Exhaustive Verification

This package contains the exact verifier for the FIFO-indexed platoon-induced scheduling loss bound. It also retains the archived index-free bound for dominance comparisons.

Run commands from this directory:

```bash
cd /home/klong23/Platoon/code/exhaustive_verification
python tests/run_tests.py
python -m compileall .
python verify_bound.py --L 2 --max-n 3 --max-total-vehicles 6 --max-release 4 --hS 2,3,4
python random_verify.py --seed 20260710 --samples 1000 --max-n 5 --max-total-vehicles 10 --max-release 8 --partitions-per-instance 16
python verify_bound.py --counts 3,2,1 --max-total-vehicles 6 --max-release 5 --hF 1 --hS 2,3,4 --keep-one-optimum --skip-repair --save-partition-rows --output-dir ../../results/exhaustive_verification/indexed/tightness_L3_counts_3_2_1_r5
python plot_bound_tightness.py --partition-rows ../../results/exhaustive_verification/indexed/tightness_L3_counts_3_2_1_r5/indexed_partition_rows.csv --output-dir ../../results/exhaustive_verification/indexed/tightness_L3_counts_3_2_1_r5 --figure-name indexed_bound_tightness
```

The primary scaled comparison is:

```text
J*_Pi - J* <= N * B_idx(Pi)
```

where `J = N D`, so the implementation avoids floating-point tolerances.

The exact integer bounds are:

```text
N * B_idx(Pi) = sum_e max((N - i_e) * max(d_e - hF, 0) - 2 * (hS - hF), 0)
N * B_0(Pi)   = sum_e max(N * max(d_e - hF, 0) - 2 * (hS - hF), 0)
```

The verifier checks `scaled_gap <= scaled_indexed_bound <= scaled_index_free_bound`.
It reports positive equality cases (`scaled_gap = scaled_indexed_bound > 0`) separately from zero equality cases (`scaled_gap = scaled_indexed_bound = 0`) so that zero-loss cases are not counted as tight positive-loss examples.

Results are written under:

```text
/home/klong23/Platoon/results/exhaustive_verification/indexed/
```

If an indexed global violation is found, the driver stops by default and writes `indexed_counterexample.json` and `indexed_counterexample.md`. If a local repair or global repair invariant violation is found, it writes `indexed_local_repair_violation.json`.

`random_verify.py` samples traffic instances and partitions reproducibly, without replacement within each sampled traffic instance. It still computes exact optima by enumerating all FIFO sequences for each sampled instance.

`global_repair.py` implements the theorem's left-to-right repair algorithm and checks the repair trace invariants used by the proof.

For the manuscript's practical-tightness figure, `verify_bound.py` can also save one row per evaluated partition via `--save-partition-rows`. The resulting CSV includes `instance_id`, `dimension_budget`, `partition`, `scaled_gap`, `scaled_indexed_bound`, and exact average-delay labels. `plot_bound_tightness.py` then compares, for each common budget, the partition selected by minimizing `B_idx(Pi)` against the actual-gap oracle under the same constraint `C(Pi) <= C_bar`, with deterministic tie-breaking by smaller `C(Pi)` and then by the enumeration order of `enumerate_partitions.py`.
