# Phase-two implementation and verification

Completed October 18, 2026 (Asia/Riyadh). This covers the single-seed learning
comparison and the user's light/dark-mode request. Recovery, exports, and the
ten-seed benchmark remain phases three and four.

## Delivered workflow

Experiment opens the short learning comparison: eight shared initial observations
and 16 additional acquisitions per strategy, ending at 24 labels each. The
dashboard reports actual preparation, acquisition, fitting, evaluation, and
checkpoint stages. It displays equal-budget learning curves, estimated adaptive
uncertainty and next selection, a separate evaluation-only error map, numerical
and model trajectories, interval diagnostics, counters, and provenance.

Both strategies use numerical observations from the existing validated QuTiP
reference, the same candidate grid and model policy, and the same isolated
evaluation set. Initial, random, and model seed streams are recorded. Adaptive
selection maximizes predictive standard deviation over unqueried candidates;
ties use candidate order. Random selection is seeded uniform without replacement.
Neither selection interface receives held-out labels or error maps.

Dark mode is on by default. Its switch also updates controls, tables, chart
surfaces, labels, focus, and hover colors. The choice persists through navigation
and computations within the browser session. The original logo, locally bundled
fonts, numerical simulation, and phase-one saved results remain available.

## Protocol and measured evidence

The short preset uses seed 0, γ ∈ [0, 2], t ∈ [0, 5], and a 21 × 21 candidate
grid. The 400 fixed-seed interior evaluation coordinates are disjoint from that
grid and have independently computed numerical labels. Twenty-one saved numerical
rate slices, each with 201 time samples, serve trajectory inspection only.

The Gaussian process uses Constant × Matérn-5/2 with two fitted length scales.
Inputs are divided by their domain upper bounds. Target normalization is off;
α = 1e−10; L-BFGS-B has zero optimizer restarts. Both strategies share this
versioned policy and deterministic fitting seed. Means and estimated intervals
are not clipped to physical bounds.

The actual default run produced:

| Final metric, 24 labels each | Adaptive | Random |
| --- | ---: | ---: |
| Held-out RMSE | 0.0538601652272759 | 0.0556468597828022 |
| MAE | 0.0325396093390719 | 0.0226665017794802 |
| Maximum absolute error | 0.220005800435251 | 0.309443214491121 |
| Fraction of means outside [−1, 1] | 0 | 0.01 |
| Empirical estimated-95% interval coverage | 0.8025 | 0.8975 |
| Mean interval width | 0.0925090445365407 | 0.0764521700309399 |

Adaptive-minus-random RMSE was −0.00178669455552625 at the final budget.
The entire nonmonotonic history remains visible. One seed does not establish a
general advantage; intervals are estimated and are not calibrated confidence
guarantees. At γ = 1, t = 0, the adaptive mean is approximately 1.005038;
this physical excursion remains visible and is counted rather than clipped.

Final cost counters were validation 3 solver calls, evaluation 400, visualization
21, training 36, exact zero-time labels 4, and cache hits 8. Each strategy still
pays 24 acquired labels, including shared and cached observations. Evaluation
and visualization labels never enter training. A warm engine run including
checkpoint writes took about 0.511 seconds; this excludes browser rendering and
is not the phase-four laptop presentation timing or a sample-efficiency claim.

## Persistence and failure behavior

The run stores 17 immutable paired revisions (the shared initial fit plus 16
acquisitions). Each contains observations, selections, predictions, metrics,
counters, random-generator state, and two JSON model artifacts. Models include
input scaling, fitted kernel parameters, scaled training coordinates, Cholesky
factor, and dual coefficients. No pickle or executable model upload is used.

Atomic revision writes advance `latest.json` only after the complete pair is
committed. Solver/model failures discard the unfinished pair. A failed pointer
write retains the previously confirmed revision and budget. The failure is shown
explicitly and recorded separately when storage permits. Incomplete results can
be inspected; continuation is phase-three work.

Reload verifies checksums, versions, policy, configuration, numerical invariants,
evaluation identity, and prediction snapshots. Reloaded means and standard
deviations agreed exactly (maximum difference 0.0), within the required 1e−8
absolute tolerance in the pinned environment. A fresh Python process reopened
and predicted with both external numerical solving and model fitting forbidden.
Fresh dashboard sessions likewise reopened models without recomputation.

## Automated verification

`.venv/bin/python -m pytest -q` → **87 passed**.

`.venv/bin/python -m compileall -q app.py qentis tests` passed;
`pip check` reported no broken requirements. The environment remains Python
3.11.16 with the pinned dependencies documented in phase-one verification.

The suite retains the 58 phase-one cases and adds learning/dashboard coverage:
real numerical labels; equal budgets and shared starting data; unique queries;
adaptive ties; seeded random choices; deterministic runs; evaluation isolation
including changed held-out labels; errors, coverage and excursions; invalid
settings; model/solver failures; failed atomic writes; fresh-process model reload;
corrupt, missing and unknown-schema artifacts; complete dashboard computation;
theme and revision/trajectory changes without solving, fitting, or saving again;
and fresh dashboard reopening. Fault injection targets external solver, sklearn,
and filesystem boundaries, rather than replacing the scientific implementation.

## Browser and visual evidence

The actual local application completed the default run and displayed its saved
result immediately. After stopping and relaunching the server, Saved runs
reopened the same run ID with a Saved result · complete label. Dark and light
modes were inspected at 1280 × 720 and
390 × 844, with an additional 1440 × 900 desktop capture. Tabs show real learning
curves, uncertainty and error maps, and reference/model trajectories. Vertical
scrolling exposes the lower evidence and diagnostics on small viewports.
There was no horizontal page overflow in the inspected layouts.

The final captures include readable plot axes and legends in both themes;
adaptive and random curves also differ by line/marker style, while the numerical
reference is named explicitly. Plotly uses the selected palette rather than a
Streamlit template override. Native control contrast and plot margins were
corrected during the bounded visual pass.

The finish review requested a dash-dot adaptive trajectory (alongside dashed
random and solid numerical reference) and a contrasting light-mode select
chevron. Both were applied, affected captures refreshed, and all 87 tests passed
again. The design documentation is updated for both themes and phase two.
The reviewer scored all three fixes resolved with a **ship** disposition at
that scope. Token/palette parity and the schema-2 design sidecar were validated.

Evidence is under `.impeccable/review/phase-two/` (Git-ignored), including
`dark-1280.png`, `light-1280.png`, `dark-desktop.png`, both `*-learning.png` and
`*-maps.png`, `light-trajectory.png`, both `*-mobile.png`,
`dark-mobile-learning.png`, `dark-mobile-trajectory.png`, and
`light-mobile-science.png`.

The complete operating-system offline rehearsal, pause/resume/recovery workflow,
downloads, fixed ten-seed benchmark, and founder meeting walkthrough have not
been claimed as part of this phase.

## Relaunch

Run `./run.sh` and open <http://localhost:8501>. Use Experiment → Learning
comparison for a new run, or Saved runs → Open selected run for stored models.
Experiment → Qubit simulation retains the phase-one numerical workflow.
