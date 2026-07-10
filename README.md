# Performance-Guaranteed Platoon Scheduling

This is an Overleaf-ready LaTeX project for the Transportation Research Part B manuscript.

For Codex-based exhaustive verification, begin with `AGENTS.md` and `EXPERIMENT_HANDOFF.md`. These two files provide the complete handoff without requiring access to the original ChatGPT conversation.

## Main manuscript

Compile `main.tex`. Formal paper sections are stored under `sections/`.
Compile `notes.tex` to obtain a separate research record containing the proof audit, candidate derivation, rejected results, and counterexamples.

## Research notes

Files under `notes/` are intentionally excluded from the compiled manuscript:

- `research_log.tex`: research decisions and audit findings.
- `proof_development.tex`: full candidate proof and unresolved checks.
- `rejected_results.tex`: invalid results, counterexamples, and superseded claims.

## Status rule

The FIFO-indexed optimality-gap bound is established analytically in `sections/theoretical_analysis.tex`. The existing verification code and archived runs evaluate the earlier index-free bound. Do not describe the indexed bound as computationally verified until the code has been updated and the deterministic and random-exact suites have been rerun.

## Recommended workflow

1. Update research notes during proof development.
2. Promote only verified results into `sections/`.
3. Compile `main.tex` after every meaningful edit.
4. Use Overleaf history or Git for version control.
