# Performance-Guaranteed Platoon Scheduling

This is an Overleaf-ready LaTeX project for the Transportation Research Part B manuscript.

For Codex-based exhaustive verification, begin with `AGENTS.md` and `EXPERIMENT_HANDOFF.md`. These two files provide the complete handoff without requiring access to the original ChatGPT conversation.

## Main manuscript

Compile `main.tex`. Formal paper sections are stored under `sections/`.
Compile `notes.tex` to obtain a separate research record containing the proof audit, candidate derivation, rejected results, and counterexamples.

## Research notes

Files under `notes/` are intentionally excluded from the compiled manuscript:

- `research_log.tex`: research decisions and audit findings.
- `proof_development.tex`: historical proof-development record.
- `rejected_results.tex`: invalid results, counterexamples, and superseded claims.
- `formal_proof_audit.md`: analytical audit of the repair proof.
- `indexed_bound_derivation.md`: derivation of the FIFO-indexed bound.

## Status rule

The FIFO-indexed optimality-gap bound is established analytically in `sections/theoretical_analysis.tex` and has been checked by the indexed deterministic and random-exact verification suite. It is the only loss bound used in the manuscript.

## Recommended workflow

1. Update research notes during proof development.
2. Promote only verified results into `sections/`.
3. Compile `main.tex` after every meaningful edit.
4. Use Overleaf history or Git for version control.
