# Exhaustive Verification Handoff

> **Status update.** The index-free bound documented below has passed the archived deterministic and random-exact checks and has been proved under the stated assumptions. The manuscript now uses the strictly sharper FIFO-indexed bound
> \[
> B_{\mathrm{idx}}(\Pi)=
> \sum_{e\in\mathcal E_\Pi}
> \left[
> \frac{N-i_e}{N}(d_e-h^F)_+
> -\frac{2(h^S-h^F)}{N}
> \right]_+.
> \]
> Here \(i_e\) is the one-based FIFO index of the predecessor vehicle in internal link \(e\). See `sections/theoretical_analysis.tex` and `notes/indexed_bound_derivation.md`. The verification code has not yet been updated for this refinement; the remainder of this handoff describes the archived index-free verification stage.

## 1. Immediate goal

Determine whether the current candidate upper bound on platoon-induced scheduling loss is valid for arbitrary numbers of approaches, arbitrary vehicle counts, and arbitrary contiguous platoon partitions under the stated model.

The task is adversarial verification. Search for counterexamples rather than trying to confirm the desired conclusion.

## 2. Scheduling model

Let the mutually conflicting approaches be

\[
\mathcal{L}=\{1,\ldots,L\}.
\]

Approach \(l\) has \(n_l\) vehicles indexed in FIFO order by \((l,i)\). The total number of vehicles is

\[
N=\sum_{l\in\mathcal{L}}n_l.
\]

Vehicle \(v=(l,i)\) has release time \(r_v\), and release times are nondecreasing within each approach.

A feasible vehicle-level passing sequence is an interleaving of all approach queues that preserves FIFO order within each approach.

For consecutive scheduled vehicles \(u,v\), the required separation is

\[
h(u,v)=
\begin{cases}
h^F, & l_u=l_v,\\
h^S, & l_u\neq l_v,
\end{cases}
\qquad 0<h^F<h^S.
\]

For a passing sequence \(s=(s_1,\ldots,s_N)\), passing times are

\[
C_{s_1}=r_{s_1},
\]

\[
C_{s_k}=\max\{r_{s_k},C_{s_{k-1}}+h(s_{k-1},s_k)\},
\qquad k=2,\ldots,N.
\]

The average vehicle delay is

\[
D(s)=\frac{1}{N}\sum_v(C_v(s)-r_v).
\]

The vehicle-level optimum is

\[
D^*=\min_{s\in\mathcal{S}}D(s).
\]

## 3. Platoon-constrained problem

A partition \(\Pi\) divides each approach queue into contiguous platoons. A platoon-constrained passing sequence must preserve approach FIFO order and must place all vehicles belonging to each platoon consecutively.

Let

\[
D^*_{\Pi}=\min_{s\in\mathcal{S}_{\Pi}}D(s)
\]

and define the actual optimality gap

\[
G(\Pi)=D^*_{\Pi}-D^*.
\]

For every internal link \(e=(a,a')\) between consecutive vehicles in the same platoon, define

\[
d_e=r_{a'}-r_a.
\]

The positive-part operator is \([x]_+=\max\{x,0\}\).

## 4. Candidate bound under test

The primary candidate partition-specific bound is

\[
B(\Pi)=
\sum_{e\in\mathcal{E}_{\Pi}}
\left[
(d_e-h^F)_+
-\frac{2(h^S-h^F)}{N}
\right]_+.
\]

The claim to test is

\[
0\leq G(\Pi)\leq B(\Pi).
\]

This claim is not established. The derivation is recorded in `notes/proof_development.tex`.

## 5. Candidate local repair claim

The proof begins with a FIFO-feasible sequence

\[
s=[P,a,B,a',R],
\]

where \(a,a'\) are consecutive vehicles from the same approach and proposed platoon, while \(B\) is nonempty and contains no vehicle from that approach. The repaired sequence is

\[
s'=[P,a,a',B,R].
\]

Let \(d=r_{a'}-r_a\), let \(M\) be the number of vehicles whose passing times may change, and let \(J(s)=ND(s)\). The candidate local claim is

\[
J(s')-J(s)
\leq
M(d-h^F)_+-2(h^S-h^F).
\]

Test this local claim independently from the global bound. If the global bound fails, determine whether the failure comes from:

1. the local repair inequality;
2. the order used to repair multiple internal links;
3. preservation of previously repaired platoon adjacencies;
4. the telescoping argument; or
5. replacement of sequence-specific \(M_e\) values by \(N\).

## 6. Required exhaustive search

Begin with:

- \(L\in\{2,3\}\);
- \(n_l\in\{1,2,3,4,5\}\), with at least two total vehicles;
- \(h^F=1\);
- \(h^S\in\{2,3,4\}\);
- integer release times from a small grid, nondecreasing within each approach;
- every FIFO interleaving;
- every contiguous partition of every approach.

Control combinatorial growth. Start from the smallest cases and increase one dimension at a time. Add reproducible random tests only after deterministic enumeration is working.

Use exact rational arithmetic where possible. Do not use an arbitrary floating-point tolerance to hide a small violation.

## 7. Required unit tests

At minimum, test:

1. all-singleton partitions, for which \(G(\Pi)=0\);
2. one platoon per approach;
3. one vehicle per approach;
4. identical release times;
5. large release-time slack;
6. no release-time slack;
7. highly unbalanced approach vehicle counts;
8. candidate zero-loss cases with internal gaps no greater than \(h^F\);
9. the known counterexample showing that an internal gap below \(h^S\) is not generally zero-loss.

The known counterexample uses \(h^F=1\), \(h^S=3\), approach A release times \((0,2)\), and approach B release times \((3,4,\ldots,12)\). Forcing the two A vehicles into one platoon produces a positive gap.

## 8. Counterexample report

If a violation \(G(\Pi)>B(\Pi)\) is found, save a machine-readable and human-readable report containing:

- \(L\), all \(n_l\), \(h^F\), and \(h^S\);
- release times by approach;
- the complete partition;
- \(D^*\), \(D^*_{\Pi}\), \(G(\Pi)\), and \(B(\Pi)\);
- every optimal vehicle-level sequence, when feasible;
- every optimal platoon-constrained sequence, when feasible;
- the smallest equivalent counterexample found;
- the proof step contradicted by the instance.

Stop broader enumeration after a counterexample is independently confirmed and minimized.

## 9. No-counterexample report

If the tested search domain produces no violation, report:

- exact parameter ranges;
- number of traffic instances;
- number of partitions;
- number of sequence evaluations;
- maximum \(G(\Pi)/B(\Pi)\) for \(B(\Pi)>0\);
- minimum and maximum bound excess;
- cases with \(B(\Pi)=0\);
- runtime and hardware information.

State only that no counterexample was found in the tested domain. Do not declare the theorem proved from computation.

## 10. Deliverables

Create:

```text
code/exhaustive_verification/
  README.md
  model.py
  enumerate_sequences.py
  enumerate_partitions.py
  verify_bound.py
  search_counterexamples.py
  tests/

results/exhaustive_verification/
  summary.json
  summary.csv
  counterexample.json        # only if one is found
  counterexample.md          # only if one is found
```

File names may be adjusted if a clearer modular design is used, but preserve separation between model logic, enumeration logic, tests, and experiment drivers.

## 11. First response required from Codex

Before implementing the full program, Codex should summarize:

1. its understanding of the scheduling model;
2. the exact bound it will test;
3. its enumeration strategy;
4. anticipated combinatorial bottlenecks;
5. ambiguities or possible proof defects already visible.

Wait for user confirmation after this summary before launching the full exhaustive search.
