# Phase 1 revision map for Sections 3 to 6

This document identifies which material is retained, withdrawn, or rewritten after restoring the original rule-based research direction.

## Section 3: Theoretical Analysis

Retain provisionally: feasible-space restriction, the nonnegative optimality gap, internal platoon links, release-time gaps, the FIFO-preserving repair argument, and the current upper-bound derivation.

Review in Phase 2: connect the bound explicitly to the critical-headway threshold and maximum platoon size; derive rule-level interpretations or corollaries; compare NP, CHP, and PP under a common threshold; verify that every claimed monotonic relationship is mathematically justified.

Do not claim yet that the current indexed bound is sufficiently tight for parameter selection or that it directly proves monotonicity in maximum platoon size.

## Section 4: Performance-Guaranteed Dimension Reduction

Withdraw the optimization-based partition-selection framework, including binary cut variables, product-variable linearization, partition MILP, loss-budget formulation, computation-size formulation, optimized dimension-loss frontiers, and Gurobi-based platoon formation.

Replace the section with `Theory-Guided Rule-Based Platooning`, organized as:

1. Existing Critical-Headway Platooning
2. Proposed Threshold-and-Size Platooning
3. Online Platoon-Formation Algorithm
4. Computational Complexity

The active method must define NP as singleton vehicles, CHP as threshold-only grouping, and PP as threshold grouping with a maximum platoon-size cap. Formation must be deterministic, sequential, interpretable, and independent of an optimization solver.

## Section 5: Numerical Experiments

Remove or invalidate: bound-selected versus oracle comparisons, selection regret, common dimension-budget optimized-partition comparisons, and all figures and tables generated from optimized partition selection. Old numerical results must not be relabeled as results of the rule-based PP method.

Retain as infrastructure only: vehicle-level and platoon-level downstream scheduling solvers, compatible instance generators, runtime/status/MIP-gap/node logging, small-instance verification utilities, and generic plotting utilities.

Regenerate experiments for NP, CHP, and PP. Primary evidence should include actual optimality gap when the NP optimum is known, theoretical-bound validation, gap versus threshold under different maximum platoon sizes, scheduling-unit or ordering-variable reduction, solution time, optimality rate, and the performance-computation trade-off.

## Section 6: Conclusion

Withdraw claims that a bound-aware partition optimizer is the practical contribution and remove numerical percentages obtained from the optimized-partition experiments.

Rewrite after the restored theory and experiments are finalized. The final conclusion should state that platooning creates a quantifiable optimality gap, theoretical analysis identifies headway and platoon size as controllable factors, those factors motivate a simple threshold-and-size rule, and PP is intended to improve the performance-computation balance relative to threshold-only CHP. NP remains the reference optimum, while CHP may produce the smallest scheduling model.
