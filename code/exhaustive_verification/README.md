# Exhaustive Verification

This package contains the archived exact verifier for the index-free platoon-induced scheduling loss bound. The manuscript now states the sharper FIFO-indexed bound; this verifier has not yet been updated for that refinement.

Run commands from this directory:

```bash
cd /home/klong23/Platoon/code/exhaustive_verification
python tests/run_tests.py
python verify_bound.py --L 2 --max-n 3 --max-total-vehicles 6 --max-release 4 --hS 2,3,4
python random_verify.py --seed 20260710 --samples 1000 --max-n 5 --max-total-vehicles 10 --max-release 8 --partitions-per-instance 16
```

The archived scaled comparison is:

```text
J*_Pi - J* <= N * B(Pi)
```

where `J = N D`, so the implementation avoids floating-point tolerances.

Results are written under:

```text
/home/klong23/Platoon/results/exhaustive_verification/
```

If a global violation is found, the driver stops by default and writes `counterexample.json` and `counterexample.md`. If a local repair violation is found, it writes `local_repair_violation.json`.

`random_verify.py` samples traffic instances and partitions reproducibly, but still computes exact optima by enumerating all FIFO sequences for each sampled instance.
