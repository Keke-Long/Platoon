# Formal Proof Audit of the Candidate Platoon Bound

This audit is purely analytical. The deterministic and random-exact verification results are not used as proof.

## Final Judgment

**Judgment: conditionally proved.**

The candidate global bound is provable under the model in `sections/formulation.tex`, provided the theorem statement explicitly includes the assumptions and the repair algorithm specified below. The manuscript draft contains a valid proof skeleton, but it is incomplete as written because it does not yet specify the repair order or prove that repairs preserve previously established platoon adjacencies.

No counterexample or conceptual failure is identified in the audited proof steps. The missing pieces are proof-exposition gaps, not formula failures.

## Exact Theorem Statement

Let there be a finite set of approaches
\[
\mathcal L=\{1,\ldots,L\}.
\]
Approach \(l\) has \(n_l\ge 1\) vehicles indexed in FIFO order by \((l,i)\), \(i=1,\ldots,n_l\). Let
\[
N=\sum_l n_l.
\]
Vehicle release times satisfy
\[
r_{l,i}\le r_{l,i+1}.
\]

A feasible vehicle sequence is any interleaving of the approach queues that preserves FIFO order within each approach. For two consecutive scheduled vehicles \(u,v\), the required separation is
\[
h(u,v)=
\begin{cases}
h^F, & l_u=l_v,\\
h^S, & l_u\ne l_v,
\end{cases}
\qquad 0<h^F<h^S.
\]

For a sequence \(s=(s_1,\ldots,s_N)\), completion times are the earliest feasible passing times under the recursion
\[
C_{s_1}(s)=r_{s_1},
\]
\[
C_{s_k}(s)=\max\{r_{s_k},C_{s_{k-1}}(s)+h(s_{k-1},s_k)\},
\qquad k=2,\ldots,N.
\]
Let
\[
J(s)=\sum_v(C_v(s)-r_v),
\qquad
D(s)=J(s)/N.
\]

Let \(\Pi\) be a partition of each approach queue into contiguous platoons. Let \(\mathcal S_\Pi\) be the set of FIFO-feasible sequences in which every platoon appears as a consecutive block. Let
\[
D^*=\min_{s\in\mathcal S}D(s),
\qquad
D^*_\Pi=\min_{s\in\mathcal S_\Pi}D(s),
\qquad
G(\Pi)=D^*_\Pi-D^*.
\]

For every internal platoon link \(e=(a,a')\), where \(a'\) is the immediate FIFO successor of \(a\) on the same approach and both are in the same platoon, define
\[
d_e=r_{a'}-r_a.
\]

Then
\[
0\le G(\Pi)\le
B(\Pi),
\]
where
\[
B(\Pi)=
\sum_{e\in\mathcal E_\Pi}
\left[
(d_e-h^F)_+
-\frac{2(h^S-h^F)}{N}
\right]_+.
\]

The zero-loss corollary follows: if
\[
d_e\le h^F+\frac{2(h^S-h^F)}{N}
\quad\text{for all }e\in\mathcal E_\Pi,
\]
then \(G(\Pi)=0\). In particular, \(d_e\le h^F\) for all internal links is sufficient. The rejected threshold \(d_e<h^S\) is not implied.

## Definitions and Required Assumptions

The proof requires the following assumptions.

1. The number of approaches and vehicles is finite.
2. Every approach queue is FIFO-ordered and feasible sequences preserve this FIFO order.
3. Release times are nondecreasing within each approach.
4. Each platoon consists of contiguous vehicles from one approach.
5. Each internal platoon link connects immediate FIFO successors on the same approach.
6. Headways depend only on whether two consecutive vehicles are from the same approach or different approaches, with constants \(0<h^F<h^S\).
7. Completion times are earliest feasible times from the max recursion using the actual completion time of the preceding vehicle.
8. The objective is total delay \(J(s)\), or equivalently average delay \(D(s)=J(s)/N\).
9. The repair algorithm processes links from left to right within each platoon, as specified below.

## Step 1: FIFO Feasibility of the Local Repair

Consider a FIFO-feasible sequence
\[
s=[P,a,B,a',R],
\]
where \(a\) and \(a'\) are immediate FIFO successors on the same approach and in the same platoon, and \(B\) is nonempty. Since \(a'\) is the immediate FIFO successor of \(a\), FIFO feasibility implies that no vehicle in \(B\) belongs to the approach of \(a\) and \(a'\). Otherwise a same-approach vehicle would have to lie between an immediate predecessor-successor pair.

The repaired sequence is
\[
s'=[P,a,a',B,R].
\]

For the approach of \(a\), the order of vehicles remains FIFO because \(a'\) is moved left only until it immediately follows its FIFO predecessor \(a\). No same-approach vehicle is crossed. For every other approach, the relative order of its vehicles is unchanged because all vehicles in \(B\) retain their internal order and are shifted as a block relative to \(a'\), which is from a different approach.

Therefore \(s'\in\mathcal S\). This holds for arbitrary numbers of approaches.

**Status: proved.**

## Step 2: Completion-Time Changes from the Max Recursion

Let
\[
T=C_a(s)=C_a(s'),
\qquad
d=r_{a'}-r_a,
\qquad
q=\max\{d,h^F\},
\qquad
B=(b_1,\ldots,b_m),
\qquad
r=|R|.
\]
Let
\[
\Delta=h^S-h^F>0.
\]

### Moved Vehicle \(a'\)

Since \(T\ge r_a\),
\[
r_{a'}=r_a+d\le T+d.
\]
Thus the recursion gives
\[
C_{a'}(s')
=\max\{r_{a'},T+h^F\}
\le T+\max\{d,h^F\}
=T+q.
\]

In the original sequence, the transition \(a\to b_1\) is cross-approach, and every transition inside \(B\) has headway at least \(h^F\). Hence
\[
C_{b_m}(s)\ge T+h^S+(m-1)h^F.
\]
Since \(b_m\) is not on the approach of \(a'\),
\[
C_{a'}(s)\ge C_{b_m}(s)+h^S
\ge T+2h^S+(m-1)h^F.
\]
Therefore
\[
C_{a'}(s')-C_{a'}(s)
\le q-2h^S-(m-1)h^F.
\]

This does not assume any release or headway term is active; it uses only upper and lower bounds from the max recursion.

### Vehicles in \(B\)

For \(b_1\),
\[
C_{b_1}(s')
=\max\{r_{b_1},C_{a'}(s')+h^S\}
\le \max\{r_{b_1},T+q+h^S\}.
\]
Since
\[
C_{b_1}(s)=\max\{r_{b_1},T+h^S\},
\]
and \(q\ge0\),
\[
\max\{r_{b_1},T+h^S+q\}
\le
\max\{r_{b_1},T+h^S\}+q.
\]
Hence
\[
C_{b_1}(s')-C_{b_1}(s)\le q.
\]

For \(j>1\), the predecessor of \(b_j\) remains \(b_{j-1}\), and the same pairwise headway is used in both sequences. If
\[
C_{b_{j-1}}(s')\le C_{b_{j-1}}(s)+q,
\]
then
\[
C_{b_j}(s')
=\max\{r_{b_j},C_{b_{j-1}}(s')+h(b_{j-1},b_j)\}
\le C_{b_j}(s)+q.
\]
By induction,
\[
C_{b_j}(s')-C_{b_j}(s)\le q,
\qquad j=1,\ldots,m.
\]

### Vehicles in \(R\)

Let \(x\) be the first vehicle in \(R\), if \(R\) is nonempty. The predecessor of \(x\) changes from \(a'\) to \(b_m\). From the bound on \(B\),
\[
C_{b_m}(s')\le C_{b_m}(s)+q.
\]
Also,
\[
C_{a'}(s)\ge C_{b_m}(s)+h^S.
\]
Therefore
\[
C_{b_m}(s')+h(b_m,x)
\le
C_{a'}(s)+q-h^S+h(b_m,x).
\]
Subtracting the old predecessor-side term \(C_{a'}(s)+h(a',x)\),
\[
C_{b_m}(s')+h(b_m,x)
-[C_{a'}(s)+h(a',x)]
\le
q-h^S+h(b_m,x)-h(a',x).
\]
Because
\[
h(b_m,x)\le h^S,
\qquad
h(a',x)\ge h^F,
\]
we obtain
\[
C_{b_m}(s')+h(b_m,x)
\le
C_{a'}(s)+h(a',x)+(q-h^F).
\]
Let
\[
\delta=q-h^F=(d-h^F)_+\ge0.
\]
Using the elementary max-recursion monotonicity
\[
A'\le A+\delta,\ \delta\ge0
\quad\Rightarrow\quad
\max\{r,A'\}\le \max\{r,A\}+\delta,
\]
we get
\[
C_x(s')-C_x(s)\le \delta.
\]

For later vehicles in \(R\), the predecessor pairs and headways are unchanged. The same induction gives
\[
C_v(s')-C_v(s)\le \delta=q-h^F,
\qquad v\in R.
\]

**Status: proved.**

## Step 3: Candidate Local Total-Delay Bound

Only \(a'\), the vehicles in \(B\), and the vehicles in \(R\) may change completion time. Vehicles in \(P\) and \(a\) retain their completion times.

Adding the bounds above,
\[
J(s')-J(s)
\le
[q-2h^S-(m-1)h^F]
+mq
+r(q-h^F).
\]
Rearranging,
\[
J(s')-J(s)
\le
(m+r+1)(q-h^F)-2(h^S-h^F).
\]
Since
\[
q-h^F=(d-h^F)_+,
\qquad
M=m+r+1,
\]
we obtain
\[
J(s')-J(s)
\le
M(d-h^F)_+-2(h^S-h^F).
\]

The right-hand side may be negative when \(d\le h^F\). This is not a problem; the proof above directly establishes the negative upper bound.

**Status: proved.**

## Step 4: Explicit Repair Algorithm

For each platoon \(P_{\ell,k}\), write its vehicles in FIFO order as
\[
P_{\ell,k}=(v_1,\ldots,v_p).
\]
Its internal links are
\[
(v_1,v_2),(v_2,v_3),\ldots,(v_{p-1},v_p).
\]

Fix any order of the platoons. Within each platoon, process internal links from left to right:

1. For \(j=1,\ldots,p-1\), locate \(v_j\) and \(v_{j+1}\) in the current sequence.
2. If \(v_{j+1}\) immediately follows \(v_j\), do nothing.
3. Otherwise the current sequence has the form
   \[
   [P,v_j,B,v_{j+1},R],
   \]
   where \(B\) is nonempty and contains no vehicle from approach \(\ell\). Apply the local repair
   \[
   [P,v_j,B,v_{j+1},R]\mapsto [P,v_j,v_{j+1},B,R].
   \]

This algorithm is defined for every FIFO-feasible starting sequence because FIFO order always keeps \(v_j\) before \(v_{j+1}\).

**Status: proved, with required repair order specified.**

## Step 5: Termination and Production of a Sequence in \(\mathcal S_\Pi\)

There are finitely many platoons and finitely many internal links. The algorithm visits each internal link exactly once. Each visit either performs one local repair or skips an already adjacent link. Hence the algorithm terminates after at most
\[
|\mathcal E_\Pi|=N-K
\]
local repairs.

After all links in a platoon have been processed left to right, every consecutive pair in that platoon is adjacent. Therefore the entire platoon appears as one consecutive block. After all platoons have been processed, every platoon is consecutive. Since every local repair preserves FIFO feasibility, the final sequence lies in \(\mathcal S_\Pi\).

**Status: proved.**

## Step 6: Previously Established Platoon Adjacencies Are Not Invalidated

Consider a local repair
\[
[P,a,B,a',R]\mapsto[P,a,a',B,R].
\]
The internal order and adjacency structure inside \(P\), inside \(B\), and inside \(R\) are unchanged. The only vehicle removed from its old position is \(a'\), and the only new insertion is immediately after \(a\).

The possible broken old adjacency involving \(a'\) is between \(a'\) and the first vehicle of \(R\). If this were a previously established platoon adjacency, that first vehicle would have to be the immediate FIFO successor of \(a'\) in the same platoon. The left-to-right repair order within each platoon prevents this: the link from \(a'\) to its successor is not processed before the link from \(a\) to \(a'\).

Previously established adjacencies in other platoons are not broken. If such an adjacency lies inside \(B\), it remains inside \(B\). If it lies inside \(P\) or \(R\), it remains there. A local repair cannot split an already contiguous block from another approach; it only moves \(a'\), which is not part of that other approach.

Thus, under the specified left-to-right order within each platoon, every established internal platoon adjacency remains established.

**Status: proved, conditional on left-to-right processing within each platoon.**

## Step 7: Telescoping Sequence-Specific Bound

Let \(s^0\) be an unrestricted optimal sequence, so
\[
D(s^0)=D^*.
\]
Apply the repair algorithm to obtain
\[
s^0,s^1,\ldots,s^T,
\]
where \(s^T\in\mathcal S_\Pi\). Since \(D^*_\Pi\) is the minimum over \(\mathcal S_\Pi\),
\[
D^*_\Pi\le D(s^T).
\]
Therefore
\[
G(\Pi)=D^*_\Pi-D^*
\le D(s^T)-D(s^0)
=\frac{1}{N}\sum_{t=1}^T[J(s^t)-J(s^{t-1})].
\]

For each actual repair \(t\), let \(e_t\) be the internal link repaired, let \(M_t\) be the corresponding value \(m+|R|+1\) at that repair step, and let \(d_{e_t}\) be its release-time gap. The local bound gives
\[
J(s^t)-J(s^{t-1})
\le
M_t(d_{e_t}-h^F)_+-2(h^S-h^F).
\]
Since
\[
x\le [x]_+
\]
for every real \(x\),
\[
J(s^t)-J(s^{t-1})
\le
\left[
M_t(d_{e_t}-h^F)_+-2(h^S-h^F)
\right]_+.
\]

Thus
\[
G(\Pi)
\le
\frac{1}{N}
\sum_{t=1}^T
\left[
M_t(d_{e_t}-h^F)_+-2(h^S-h^F)
\right]_+.
\]

Equivalently, if \(\mathcal Q\) denotes the set of internal links that actually required repair under this algorithm,
\[
G(\Pi)
\le
\frac{1}{N}
\sum_{e\in\mathcal Q}
\left[
M_e(d_e-h^F)_+-2(h^S-h^F)
\right]_+.
\]

**Status: proved.**

## Step 8: Transition to the Partition-Specific Bound

For every repair, \(M_e\le N\). Let
\[
x_e=(d_e-h^F)_+\ge0,
\qquad
\Delta=h^S-h^F.
\]
Then
\[
M_ex_e-2\Delta\le Nx_e-2\Delta.
\]
By monotonicity of the positive-part operator,
\[
[M_ex_e-2\Delta]_+
\le
[Nx_e-2\Delta]_+.
\]
Dividing by \(N\),
\[
\frac{1}{N}[M_ex_e-2\Delta]_+
\le
\left[x_e-\frac{2\Delta}{N}\right]_+.
\]
Therefore
\[
G(\Pi)
\le
\sum_{e\in\mathcal Q}
\left[
(d_e-h^F)_+
-\frac{2(h^S-h^F)}{N}
\right]_+.
\]
Since \(\mathcal Q\subseteq\mathcal E_\Pi\) and every added term is nonnegative,
\[
G(\Pi)
\le
\sum_{e\in\mathcal E_\Pi}
\left[
(d_e-h^F)_+
-\frac{2(h^S-h^F)}{N}
\right]_+
=B(\Pi).
\]

**Status: proved.**

## Step 9: Zero-Loss Corollary

If every internal link satisfies
\[
d_e\le h^F+\frac{2(h^S-h^F)}{N},
\]
then
\[
(d_e-h^F)_+\le \frac{2(h^S-h^F)}{N}
\]
for every internal link, so every term in \(B(\Pi)\) is zero. Hence
\[
B(\Pi)=0.
\]
Because feasible-space restriction gives \(G(\Pi)\ge0\) and the theorem gives \(G(\Pi)\le0\), it follows that
\[
G(\Pi)=0.
\]

This corollary is genuinely implied by the theorem. The stronger rejected statement using \(h^S\) as a zero-loss threshold is not implied and remains false.

**Status: proved, conditional on the theorem.**

## Step 10: Required Final Theorem Assumptions

The final theorem statement should include:

1. \(L<\infty\), \(n_l\ge1\), \(N=\sum_l n_l\).
2. Release times are nondecreasing within each approach.
3. Vehicle sequences preserve FIFO order within each approach.
4. Headways are exactly \(h^F\) for same-approach consecutive vehicles and \(h^S\) for different-approach consecutive vehicles, with \(0<h^F<h^S\).
5. Completion times are generated by the actual-predecessor max recursion.
6. The objective is average delay \(D=J/N\).
7. Platoon partitions are contiguous within each approach.
8. Internal platoon links connect immediate FIFO successors.
9. The repair proof uses a left-to-right order within each platoon.

## Missing or Previously Unproven Steps

The following steps were missing or under-specified in the draft proof:

1. The repair algorithm was not explicitly defined.
2. The left-to-right order within each platoon was not stated.
3. Preservation of previously repaired adjacencies was not proved.
4. The suffix max-recursion inequality needed the explicit observation that \(\delta=q-h^F\ge0\). Without \(\delta\ge0\), the max-recursion perturbation step would be false in general.
5. The transition from sequence-specific \(M_e\) to the partition-specific bound needed the monotonicity argument for \([\cdot]_+\).

These are fixable proof gaps. They do not invalidate the candidate bound under the stated assumptions.

## Invalid or Unproven Step

No invalid step remains after adding the explicit repair order and the missing max-recursion details above.

The theorem should still not be promoted in the manuscript until the user approves updating the paper text. This file is an audit record, not a manuscript revision.

