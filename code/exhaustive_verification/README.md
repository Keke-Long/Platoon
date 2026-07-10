# Exhaustive Verification

This package contains the exact verifier for the FIFO-indexed platoon-induced scheduling loss bound. It also retains the archived index-free bound for dominance comparisons.

Run commands from this directory:

```bash
cd /home/klong23/Platoon/code/exhaustive_verification
python tests/run_tests.py
python -m compileall .
python verify_bound.py --L 2 --max-n 3 --max-total-vehicles 6 --max-release 4 --hS 2,3,4
python random_verify.py --seed 20260710 --samples 1000 --max-n 5 --max-total-vehicles 10 --max-release 8 --partitions-per-instance 16
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

Results are written under:

```text
/home/klong23/Platoon/results/exhaustive_verification/indexed/
```

If an indexed global violation is found, the driver stops by default and writes `indexed_counterexample.json` and `indexed_counterexample.md`. If a local repair or global repair invariant violation is found, it writes `indexed_local_repair_violation.json`.

`random_verify.py` samples traffic instances and partitions reproducibly, without replacement within each sampled traffic instance. It still computes exact optima by enumerating all FIFO sequences for each sampled instance.

`global_repair.py` implements the theorem's left-to-right repair algorithm and checks the repair trace invariants used by the proof.
