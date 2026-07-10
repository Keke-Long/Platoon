# Codex Instructions for the Platoon Scheduling Project

## Project objective

This repository develops a performance-guaranteed dimension-reduction framework for vehicle scheduling at general conflict areas. Platooning is a preprocessing operation that reduces the dimension of a downstream scheduling MILP. Gurobi remains responsible for solving the partition-selection and scheduling models. This project does not aim to develop a new MILP solver.

## Source of truth

Before performing theoretical or computational work, read these files in order:

1. `EXPERIMENT_HANDOFF.md`
2. `sections/formulation.tex`
3. `sections/theoretical_analysis.tex`
4. `notes/proof_development.tex`
5. `notes/rejected_results.tex`
6. `notes/research_log.tex`

The current refined optimality-gap bound is a candidate result. Never assume it is correct merely because it appears in a LaTeX theorem or equation.

## Current task boundary

The immediate task is exhaustive verification of the candidate bound. Do not proceed to the partition-selection MILP, large-scale Gurobi experiments, literature review, or manuscript expansion until the candidate bound has been tested and the user has approved the next stage.

## Mathematical implementation requirements

- Every passing sequence must preserve FIFO order within each approach.
- Every platoon partition must consist of contiguous vehicles from the same approach.
- Use the actual passing time of the preceding vehicle in the completion-time recursion.
- Distinguish release times, passing times, total delay, and average delay.
- Use exact rational arithmetic for exhaustive small-instance checks whenever possible.
- Do not infer global validity from random tests alone.
- Actively search for counterexamples and minimize any counterexample found.

## Coding requirements

- Place verification code under `code/exhaustive_verification/`.
- Use Python 3.11 or later.
- Do not include emoji in code, logs, or generated reports.
- Keep the exact model implementation separate from experiment drivers.
- Add unit tests for sequence enumeration, partition enumeration, completion-time recursion, objective calculation, and bound calculation.
- Record random seeds and parameter ranges.
- Save machine-readable results under `results/exhaustive_verification/`.
- Do not commit virtual environments, caches, LaTeX build files, or large temporary enumerations.

## Stop conditions

If a counterexample is found:

1. stop expanding the search;
2. minimize the number of approaches, vehicles, and release-time values;
3. independently recompute the instance;
4. report the original optimum, platoon optimum, actual gap, candidate bound, optimal sequences, and partition;
5. identify which proof step fails;
6. do not silently replace the theorem with a new formula.

If no counterexample is found, report only that the tested domain passed. Numerical verification is not a proof.

## Manuscript protection

Do not promote candidate results to established theorems or remove status warnings from the LaTeX manuscript without explicit user approval. Preserve rejected arguments and counterexamples in `notes/rejected_results.tex`.

## Verification commands

Once the verification package exists, document reproducible commands in `code/exhaustive_verification/README.md`. Run the full test suite before reporting completion.
