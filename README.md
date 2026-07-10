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

The refined optimality-gap bound is currently a candidate result. Do not remove the candidate label until exhaustive small-instance verification has found no counterexample and the proof checks listed in `notes/proof_development.tex` have been resolved.

## Recommended workflow

1. Update research notes during proof development.
2. Promote only verified results into `sections/`.
3. Compile `main.tex` after every meaningful edit.
4. Use Overleaf history or Git for version control.
