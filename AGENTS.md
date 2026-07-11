# Codex Instructions for the Platoon Scheduling Project

## Project objective

This repository develops a performance-guaranteed dimension-reduction framework for vehicle scheduling at general conflict areas. Platooning is a preprocessing operation that reduces the dimension of a downstream scheduling MILP. Gurobi remains responsible for solving the partition-selection and scheduling models. This project does not aim to develop a new MILP solver.

## Repository structure and source of truth

The only official manuscript entry point is `paper/main.tex`. All formal paper sources must remain under `paper/`; do not create duplicate manuscript files at the repository root.

Before theoretical or computational work, read these files in order:

1. `paper/sections/formulation.tex`
2. `paper/sections/theoretical_analysis.tex`
3. `notes/proof_development.tex`
4. `notes/formal_proof_audit.md`
5. `notes/indexed_bound_derivation.md`
6. `notes/rejected_results.tex`
7. `notes/research_log.tex`
8. the relevant README under `code/`

The FIFO-indexed optimality-gap bound is the only loss bound used in the manuscript. Its analytical proof and indexed verification results are current. Historical precursor materials may remain in research notes and archived code, but must not be reintroduced into the manuscript.

## Branch policy

`main` is the only official stable version. Keep at most one active working branch. Merge a completed and validated task promptly, then delete its branch. Merged pull requests and Git history preserve the purpose and implementation record.

## Mathematical implementation requirements

- Every passing sequence must preserve FIFO order within each approach.
- Every platoon partition must consist of contiguous vehicles from the same approach.
- Use the actual passing time of the preceding vehicle in the completion-time recursion.
- Distinguish release times, passing times, total delay, and average delay.
- Use exact rational arithmetic for exhaustive small-instance checks whenever possible.
- Do not infer global validity from random tests alone.
- Actively search for counterexamples and minimize any counterexample found.

## Coding requirements

- Keep verification code under `code/exhaustive_verification/`.
- Use Python 3.11 or later.
- Do not include emoji in code, logs, or generated reports.
- Keep exact model implementation separate from experiment drivers.
- Record random seeds and parameter ranges.
- Save machine-readable results under `results/`.
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

Preserve rejected arguments and counterexamples in `notes/rejected_results.tex`. Do not change the theorem's assumptions or formula without a new proof audit. Compile `paper/main.tex` after every meaningful manuscript edit and run the relevant test suite before reporting completion.
