# Chapter 5 Figure Specification

Do not change axes, plot type, visual encodings, or aggregation rules without explicit approval from the project lead.

This file is the source of truth for Chapter 5 figures.

## Data Status

Current completed formal results:

- `N=20`
- `N=40`
- total `lambda=1.5`, reused from old `arrival_rate=0.4`
- total `lambda=2.5`, reused from old `arrival_rate=0.7`

Not yet completed:

- `N=60`
- `N=80`
- 600-second NP recovery
- total `lambda=0.5`, `1.0`, and `2.0` for the revised total-arrival-rate grid

`lambda` now means total vehicle arrival rate into the entire conflict area. With `L=4`, the per-approach Poisson rate is `lambda/4`. Old `arrival_rate=1.0` rows are deleted and must not be plotted. Current figures may use only completed `N=20` and `N=40` data at total `lambda=1.5` and `2.5`; they must leave missing total rates empty until those experiments are generated. Figures requiring exact actual gaps can only use rows where NP and PP are both proven optimal; until NP recovery is run, the checked actual-gap subset is currently available for `N=20`.

## Audit Before Correction

### Figure 6: Bound Validation

- Approved form: 3D plot.
- Current difference before correction: the existing figure was a two-panel 2D plot, with actual `G` against `Ghat` and bound utilization. This did not match the approved 3D axes.
- Current data sufficiency: completed checked rows are sufficient to create the approved 3D form, but the checked subset currently contains `N=20` because `N=40` lacks exact NP references before NP recovery.
- Need for `N=60,80`: needed only for final full-grid polish. NP recovery is also needed before larger `N` rows can enter exact-gap bound validation.
- `Pmax` handling: all `Pmax` values are shown on the y-axis.
- Updated plotting decision: `Ghat` is shown as one semi-transparent surface, not as scatter points. Marker shape distinguishes total arrival rate `lambda`; `N` is not visually encoded, and completed rows are pooled in one 3D axes.
- Representative callback instance: not applicable.

### Figure 7: Complexity-Gap Trade-Off

- Approved form: scatter plot.
- Current difference before correction: the existing figure used the correct conceptual axes but aggregated across all `N`, which could silently mix scale-dependent solve-time behavior.
- Current data sufficiency: completed checked rows are sufficient for the approved scatter form, but the checked actual-gap subset currently contains `N=20` because `N=40` lacks exact NP references before NP recovery.
- Need for `N=60,80`: needed only for final full-grid polish. NP recovery is also needed before larger `N` rows can enter exact-gap trade-off plots.
- `Pmax` handling: all `Pmax` values are retained as marker shapes; no PP averaging across `Pmax`.
- Representative callback instance: not applicable.

### Figure 8: Delay Versus Threshold and Total Arrival Rate

- Approved form: two-panel line figure with delay versus `delta` and delay versus total arrival rate `lambda`.
- Current difference before correction: the existing figure stratified by `N` but placed plot titles over panels and used dense legends; it needed explicit approved aggregation and no top titles.
- Current data sufficiency: completed `N=20` and `N=40` are sufficient for a form-correct provisional figure.
- Need for `N=60,80`: needed only for final full-grid polish.
- `Pmax` handling: all `Pmax` values are retained in PP marker encoding; no PP averaging across `Pmax`.
- Representative callback instance: not applicable.

### Figure 9: Complexity-Reduction Mechanism

- Approved form: line figure showing solution time and number of scheduling units as functions of `delta` and total arrival rate `lambda`.
- Current difference before correction: the existing file name used `platoon_count`, and labels referred to platoons rather than the approved number of scheduling units. Panel titles were also present.
- Current data sufficiency: completed `N=20` and `N=40` are sufficient for a form-correct provisional figure.
- Need for `N=60,80`: needed only for final full-grid polish.
- `Pmax` handling: all `Pmax` values are retained in PP marker encoding; no PP averaging across `Pmax`.
- Representative callback instance: not applicable.

### Figure 10: Gurobi Solution Quality Over Time

- Approved form: line plot of Gurobi wall-clock time versus best incumbent average vehicle delay.
- Current difference before correction: the existing plot used real callbacks and a shared instance, but included top title text and included CHP although the approved comparison is NP and PP under different `delta`.
- Current data sufficiency: available callback rows are sufficient for a provisional or representative shared-instance figure if a complete N=40 instance exists.
- Need for `N=60,80`: not required for the approved form, but may improve final representativeness.
- `Pmax` handling: use one representative `Pmax=4`, stated in metadata and manuscript caption.
- Representative callback instance: the plotting script must prefer an informative `N=40` shared instance when available; otherwise it marks the selected instance provisional.

## Approved Figure Definitions

### Figure 6: `bound_validation_actual_vs_upper.pdf`

- Plot type: 3D plot.
- Purpose: validate that the rule-level upper bound is above the actual platooning-induced optimality gap.
- x-axis: platooning threshold `delta`.
- y-axis: maximum platoon size `Pmax`.
- z-axis: `G` and `Ghat`.
- Marker shape: total arrival rate `lambda`.
- `N`: not visually encoded; completed rows are pooled in the same 3D axes.
- Content: only checked rows where NP and PP are both proven optimal; show both actual `G` and theoretical `Ghat`.
  The `Ghat` values may be shown for completed rows even when exact actual `G` is not yet available, but actual `G` points must use only checked rows.

### Figure 7: `experimental_tradeoff_solve_time_gap.pdf`

- Plot type: scatter plot.
- Purpose: show the experimental complexity-gap trade-off.
- x-axis: solve time.
- y-axis: actual optimality gap `G`.
- Color: `delta`, sampled from the `gist_earth` colormap in reversed order.
- Marker shape: `Pmax`.
- Aggregation: none. Each point is one bound-checkable case row with exact actual `G`.
- Legend placement: inside the upper-right plotting area, with separate `delta` color and `Pmax` marker labels placed side by side.

### Figure 8: `pp_delay_vs_threshold_density.pdf`

- Plot type: line figure with two scientific panels: delay versus `delta` and delay versus total arrival rate `lambda`.
- Purpose: show that average vehicle delay increases with larger threshold or higher total arrival rate.
- Compare: NP, CHP, PP.
- `Pmax`: averaged within PP for this presentation figure.
- Aggregation: method-level means over delay-order-checkable rows, stratified by `N`; light shaded bands show the interquartile range behind each method-level mean.
- Layout: compact two-panel row; panel labels are centered above each plotting frame and the method legend is a single top row.

### Figure 9: `pp_time_and_scheduling_units.pdf`

- Plot type: line figure.
- Purpose: show the mechanism behind complexity reduction.
- Required panels: solution time vs `delta`, solution time vs total `lambda`, number of scheduling units vs `delta`, number of scheduling units vs total `lambda`.
- Scheduling units: NP equals number of vehicles; CHP and PP equal number of platoons.
- `Pmax`: averaged within PP for this presentation figure.
- Aggregation: method-level means over completed rows, stratified by `N`; light shaded bands show the interquartile range behind each method-level mean.

### Figure 10: `gurobi_solution_quality_over_time.pdf`

- Plot type: line plot.
- Purpose: show Gurobi solution quality as a function of wall-clock solution time.
- x-axis: Gurobi wall-clock solution time.
- y-axis: best incumbent average vehicle delay.
- Content: one shared traffic instance; NP and PP under different `delta`; fixed representative `Pmax=4`.
- Data source: real Gurobi callback trajectories only.
