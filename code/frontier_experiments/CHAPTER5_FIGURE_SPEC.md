# Chapter 5 Figure Specification

Do not change axes, plot type, visual encodings, or aggregation rules without explicit approval from the project lead.

This file is the source of truth for Chapter 5 figures.

## Data Status

Current completed formal results:

- `N=20` for all total `lambda={0.5,1.0,1.5,2.0,2.5}`
- `N=40` for all total `lambda={0.5,1.0,1.5,2.0,2.5}`; 176 PP rows from 11 instances have exact NP references
- `N=60` for all total `lambda={0.5,1.0,1.5,2.0,2.5}`; 128 PP rows from 8 instances have exact NP references
- `N=80` for all total `lambda={0.5,1.0,1.5,2.0,2.5}`; 64 PP rows from 4 instances have exact NP references
- the `N=20`, total `lambda=1.5` rows reused from old `arrival_rate=0.4`
- the `N=20`, total `lambda=2.5` rows reused from old `arrival_rate=0.7`

The reuse and relabeling of these two rates is an approved project decision. Figures should treat them as the completed `lambda={1.5,2.5}` cases.

Not yet completed:

- none; the four-scale paper-facing grid is complete

`lambda` now means total vehicle arrival rate into the entire conflict area. With `L=4`, the per-approach Poisson rate is `lambda/4`. Old `arrival_rate=1.0` rows are deleted and must not be plotted. Figures must use only rows in the uniform 600-second result set and leave unfinished scales empty. Figures requiring exact actual gaps can use only rows where NP and PP are both proven optimal.

## Audit Before Correction

### Figure 6: Bound Validation

- Approved form: 3D plot.
- Current difference before correction: the existing figure was a two-panel 2D plot, with actual `G` against `Ghat` and bound utilization. This did not match the approved 3D axes.
- Current data sufficiency: the exact-gap-checkable rows for all four scales constitute the final approved dataset.
- Need for additional scales: none.
- `Pmax` handling: all `Pmax` values are shown on the y-axis.
- Updated plotting decision: `Ghat` is shown as one semi-transparent surface, not as scatter points. Marker shape distinguishes total arrival rate `lambda`; `N` is not visually encoded, and completed rows are pooled in one 3D axes.
- Representative callback instance: not applicable.

### Figure 7: Complexity-Gap Trade-Off

- Approved form: scatter plot.
- Current difference before correction: the existing figure used the correct conceptual axes but aggregated across all `N`, which could silently mix scale-dependent solve-time behavior.
- Current data sufficiency: the exact-gap-checkable rows for all four scales constitute the final approved dataset.
- Need for additional scales: none.
- `Pmax` handling: all `Pmax` values are retained as marker shapes; no PP averaging across `Pmax`.
- Representative callback instance: not applicable.

### Figure 8: Delay Versus Threshold and Total Arrival Rate

- Approved form: two-panel line figure with delay versus `delta` and delay versus total arrival rate `lambda`.
- Current difference before correction: the existing figure stratified by `N` but placed plot titles over panels and used dense legends; it needed explicit approved aggregation and no top titles.
- Current data sufficiency: completed `N={20,40,60}` rows are sufficient for a form-correct provisional figure.
- Need for additional scales: none.
- `Pmax` handling: all `Pmax` values are retained in PP marker encoding; no PP averaging across `Pmax`.
- Representative callback instance: not applicable.

### Figure 9: Complexity-Reduction Mechanism

- Approved form: line figure showing solution time and number of scheduling units as functions of `delta` and total arrival rate `lambda`.
- Current difference before correction: the existing file name used `platoon_count`, and labels referred to platoons rather than the approved number of scheduling units. Panel titles were also present.
- Current data sufficiency: completed `N={20,40,60}` rows are sufficient for a form-correct provisional figure.
- Need for additional scales: none.
- `Pmax` handling: all `Pmax` values are retained in PP marker encoding; no PP averaging across `Pmax`.
- Representative callback instance: not applicable.

### Figure 10: Gurobi Solution Quality Over Time

- Approved form: line plot of Gurobi wall-clock time versus best incumbent average vehicle delay.
- Current difference before correction: the existing plot used real callbacks and a shared instance but included top title text and CHP. The final available data support NP and one representative PP setting.
- Current data sufficiency: available callback rows are sufficient for a provisional or representative shared-instance figure if a complete N=40 instance exists.
- Need for larger `N`: none; the representative trajectory remains an informative shared `N=40` instance.
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
- Content: one shared traffic instance; NP and representative PP with `delta=4` and `Pmax=4`.
- Data source: real Gurobi callback trajectories only.
