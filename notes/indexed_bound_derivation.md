# Derivation of the FIFO-Indexed Platoon Loss Bound

## Status

This note records the refinement approved for inclusion as a formal theorem in `sections/theoretical_analysis.tex`. It sharpens the previously audited index-free bound without changing the local repair inequality.

## Affected-vehicle count

For an internal link

\[
e=((l,i),(l,i+1)),
\]

consider a repairable FIFO sequence

\[
s=[P,a,B,a',R],
\]

with \(a=(l,i)\) and \(a'=(l,i+1)\). The local proof defines

\[
M_e=|B|+|R|+1.
\]

Because

\[
N=|P|+1+|B|+1+|R|,
\]

we have

\[
M_e=N-|P|-1.
\]

FIFO feasibility requires all \(i-1\) predecessors of \(a\) on approach \(l\) to appear in \(P\). Hence

\[
|P|\ge i-1
\]

and therefore

\[
M_e\le N-i.
\]

This is strictly stronger than the earlier substitution \(M_e\le N\).

## Indexed partition-specific bound

Let

\[
x_e=(d_e-h^F)_+,
\qquad
\Delta_h=h^S-h^F.
\]

The audited local repair result is

\[
J(s')-J(s)\le M_ex_e-2\Delta_h.
\]

After taking a positive part, dividing by \(N\), and applying \(M_e\le N-i_e\),

\[
\frac{1}{N}[M_ex_e-2\Delta_h]_+
\le
\left[
\frac{N-i_e}{N}x_e-rac{2\Delta_h}{N}
\right]_+.
\]

The same left-to-right global repair and telescoping argument therefore gives

\[
G(\Pi)\le B_{\mathrm{idx}}(\Pi),
\]

where

\[
B_{\mathrm{idx}}(\Pi)
=
\sum_{e\in\mathcal E_\Pi}
\left[
\frac{N-i_e}{N}(d_e-h^F)_+
-\frac{2(h^S-h^F)}{N}
\right]_+.
\]

Because \((N-i_e)/N<1\), this bound is no larger than the earlier index-free bound term by term.

## Zero-loss condition

Every term is zero if

\[
d_e\le h^F+\frac{2(h^S-h^F)}{N-i_e}.
\]

Thus this condition for every internal link implies \(G(\Pi)=0\). It is less restrictive for links later in an approach queue.

## Tight example

Let \(h^F=1\), \(h^S=2\), let approach A have one vehicle released at time 1, and let approach B have two vehicles released at times 0 and 3. Force the two B vehicles into one platoon.

The unrestricted optimum is the sequence \(B_1,A_1,B_2\), with total delay 2. The platoon-constrained optimum has total delay 4, so the average optimality gap is \(2/3\). The indexed bound is also \(2/3\), while the earlier index-free bound is \(4/3\).

This example proves that the indexed bound can be attained exactly.
