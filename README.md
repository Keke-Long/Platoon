# Performance-Guaranteed Platoon Scheduling

This repository contains the manuscript, verification code, experiment code, results, and research notes for the platoon-scheduling project.

## Official manuscript

The only official paper source is under `paper/`.

```bash
cd paper
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
```

The manuscript entry point is `paper/main.tex`. Its sections, bibliography, preamble, and figures are all stored inside `paper/`. Do not create a second manuscript copy at the repository root.

## Research notes

Compile `notes.tex` from the repository root to obtain the separate proof-development record. It reuses the current formal formulation and theorem from `paper/sections/`, then adds the historical files under `notes/`.

Files under `notes/` are intentionally excluded from the formal manuscript.

## Verification and experiments

For Codex-based work, begin with `AGENTS.md` and the relevant README under `code/`. Machine-readable outputs are stored under `results/`.

## Branch policy

`main` is the only official stable version. Use at most one short-lived working branch for an active task. After validation, merge it into `main` and delete the branch. Do not retain completed `agent/...` branches as permanent records because Git history and merged pull requests already preserve that context.
