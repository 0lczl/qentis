# Spec: Qentis Adaptive Quantum Discovery Proof of Concept

## Problem Statement

The founder needs to show a scientist and a potential funder a working, understandable example of Qentis within one to two days. The founder and teammate will present from a laptop during an online meeting. They need credible scientific output, an engaging explanation of the idea, and a reliable presentation that does not depend on a long live computation.

The central question is whether a model can learn a simple simulated quantum response and use estimated uncertainty to choose useful simulation points. The prototype must make that loop visible and compare it fairly with random selection. An adaptive win is a research outcome to measure, not a delivery requirement.

## Solution

Build a local, English-language research dashboard demonstrating a single qubit under pure dephasing. It numerically generates reference observations, trains a small regression model, selects another point based on predictive uncertainty, and repeats. The dashboard shows a Bloch sphere, coherence trajectories, uncertainty and error maps, and learning curves for adaptive and random selection.

Provide a genuinely computed saved experiment for the presentation and a short live run. Save completed iteration checkpoints, model artifacts, configuration, and results on disk. The founder can open a saved run, explain the experiment, inspect results, and start a live run without entering commands during the meeting.

This is a simulation-based workflow demonstration. It does not establish quantum advantage, hardware performance, a new physical discovery, or a general advantage of adaptive sampling.

## User Stories

1. As the presenter, I want a prepared experiment that opens immediately, so that I can explain the idea before running anything live.
2. As the presenter, I want a short explanation of the learning loop, so that a non-specialist can follow the demonstration.
3. As the presenter, I want clear default settings, so that I can start a live experiment confidently.
4. As a technical viewer, I want to inspect the physical assumptions, rate convention, and numerical method, so that I can assess what is actually simulated.
5. As a viewer, I want to inspect a qubit trajectory and time-series values, so that I can see what dephasing changes.
6. As a viewer, I want numerical reference and model prediction shown separately, so that I can judge approximation error.
7. As a viewer, I want to see model uncertainty and the next selected point, so that I can understand the selection decision.
8. As a technical viewer, I want a separate error map and held-out metrics, so that estimated uncertainty is not mistaken for measured error.
9. As a viewer, I want adaptive and random strategies compared with equal budgets, so that the comparison is meaningful.
10. As a technical viewer, I want repeated seeded results, so that one favorable run is not presented as a general result.
11. As the presenter, I want to pause at a completed iteration and resume, so that I can explain intermediate results.
12. As the presenter, I want saved runs to survive application restarts, so that my presentation does not rely on browser memory.
13. As a technical viewer, I want a saved model to reproduce its predictions, so that model persistence is real.
14. As the presenter, I want invalid settings and computation failures explained clearly, so that I can recover without losing completed work.
15. As a user, I want an interrupted run identified and recoverable from its last complete checkpoint, so that partial output is not mistaken for completion.
16. As a technical viewer, I want raw results and configuration exported, so that I can inspect and reproduce the experiment.
17. As a viewer, I want negative or inconclusive findings reported honestly, so that scientific limitations remain visible.
18. As the presenter, I want readable charts and controls during screen sharing, so that the audience can understand the evidence.

## Acceptance Criteria

- [x] Runs locally after documented setup, with no account, external API, cloud dependency, or network requirement during the meeting.
- [x] Uses English, the supplied Qentis logo, and the agreed near-black/violet design direction; core content remains usable at 1280 × 720.
- [x] Provides a saved presentation run and a working live-run flow, visibly distinguished.
- [x] Implements the defined numerical dephasing model and passes analytical and physical-invariant checks before generating the presentation dataset.
- [x] Actually fits a regression model to acquired numerical observations; predicted curves are not analytical results relabeled as AI output.
- [x] Adaptive selection uses only training information and model uncertainty. Evaluation labels never enter training, acquisition, or live hyperparameter decisions.
- [x] Both strategies share the same initial dataset, candidate pool, budget, model policy, and evaluation set within each comparison.
- [x] Every completed iteration records actual predictions, metrics, selection decisions, and simulation counts.
- [x] Shows a Bloch sphere, coherence trajectory, uncertainty map, separate error map, and error-versus-acquired-points comparison with labeled axes and legends.
- [x] A prepared benchmark includes ten predeclared seeds with all outcomes retained; live single-seed results are labeled as such.
- [x] At least one live run completes on the presentation laptop. Target duration is at most 60 seconds for the default short preset; record measured hardware and timing. Reduce candidate-grid size or fit restarts if needed, symmetrically and before fixing the benchmark protocol.
- [x] Saving, restarting, reloading, and resuming preserve completed scientific results. Reloaded model predictions agree with stored predictions within absolute tolerance 1e-8 in the pinned environment.
- [x] Invalid input, numerical failures, interrupted writes, incompatible artifacts, and model-fit failures have tested handling; no fabricated replacement output.
- [x] Exports configuration and provenance in JSON and observations/metrics in CSV through working download controls.
- [x] A short presenter walkthrough and setup instructions have been exercised from a clean application launch.
- [x] Scientific correctness, benchmark fairness, persistence, and the full presentation flow pass the tests described below.

## Implementation Decisions

The audience, deadline, local presentation, English interface, simulated-only scope, saved-plus-live demonstration, and honest reporting were agreed with the founder. The stack, mathematical conventions, model, budgets, and test thresholds below are engineering defaults chosen to make that scope concrete; they are not claims that the founder selected particular libraries.

### Architecture & Schema

**Local architecture.** Use Python with Streamlit for the dashboard, Plotly for interactive charts, QuTiP for numerical evolution, and scikit-learn for Gaussian-process regression. Pin compatible dependency versions during implementation and record them with each run. Keep scientific logic independent of dashboard reruns. Use local filesystem storage with atomic checkpoint writes; no service provisioning is needed.

**Deep modules and responsibilities:**

| Module | Encapsulated responsibility |
| --- | --- |
| Physics reference | Rate conventions, numerical solver, analytical checks, state observables, and solver failures |
| Surrogate model | Input scaling, deterministic fit policy, prediction mean/standard deviation, model artifacts, and compatibility |
| Experiment engine | Candidate pools, seeded selection, budgets, iteration transitions, pause/resume, and leakage prevention |
| Evaluation | Isolated reference labels, error metrics, repeated-seed summaries, and uncertainty diagnostics |
| Run repository | Atomic saves, checkpoint integrity, schema versions, exports, and reload validation |
| Dashboard | Controls, charts, provenance, accessible states, and presentation workflow |

All five computational/storage modules receive meaningful automated tests. Dashboard behavior receives integration and presentation-flow checks.

**Physical convention.** Set ℏ = 1, Hamiltonian H = 0, initial state |+⟩, and collapse operator L = √(γ/2) σz. The Lindblad equation then gives dρ/dt = (γ/2)(σzρσz − ρ). Define t in dimensionless time units and γ in inverse time units. The analytical check is x(t) = exp(−γt), y(t) = 0, z(t) = 0; diagonal populations remain 1/2. Coherence shown in the interface is x = 2 Re(ρ01), not population or purity. Purity, if shown, is (1 + x²)/2. Use the analytical expression only for solver validation, never as a substitute for numerically acquired training labels.

**Learning task.** Learn the scalar observable x as a function of the pair (γ, t), initially on γ ∈ [0, 2] and t ∈ [0, 5]. Each acquired sample is one requested parameter pair with one numerically evaluated observable. One query means one solver call for that pair, with t = 0 handled as the exact initial condition. A selected point does not grant extra trajectory labels to training. A trajectory generated solely for visualization is accounted for separately.

**Model and selection.** Use a Gaussian process with a constant-times-Matérn-5/2 kernel with separate length scales for scaled γ and t, deterministic optimization seeds, a small fixed numerical diagonal regularizer, and predictive standard deviation as the acquisition score. Fit the same policy for both strategies. Select the highest-standard-deviation unqueried candidate; break ties by stable candidate order. Random selection is uniform without replacement. Predictions are unconstrained estimates: do not silently clip values or confidence bands into the physical domain. Flag excursions and report their rate.

**Data separation and budgets.** Start with eight common, seeded, unique random candidate pairs. Use a fixed 21 × 21 candidate grid; the short preset acquires 16 additional points per strategy, and the prepared benchmark acquires 24 additional points per strategy. A separate fixed evaluation set contains 400 reproducibly generated interior points, disjoint from candidates, with labels numerically generated before evaluation. Its labels remain private to evaluation. Numerical-reference preparation, diagnostic visualization calls, and counted training queries have separate counters. Shared cache hits are disclosed and count as acquired labels for learning-budget purposes; do not equate unique-label budget with wall-clock compute cost.

**Evaluation.** Primary metric is RMSE of x over the fixed evaluation set. Also record MAE, maximum absolute error, and fraction of predictions outside [−1, 1]. Record metrics after the initial fit and every acquisition. Evaluate estimated intervals using mean ± 1.96 predictive standard deviations, reporting empirical coverage and mean interval width as diagnostics, not guaranteed calibration. Benchmark seeds are 0–9; show mean curves and across-seed standard-deviation bands, explicitly labeled as variability rather than confidence intervals. Retain per-seed outcomes, including losses. Summarize final RMSE difference and wins/ties/losses using a declared numerical tie tolerance of 1e-8. Do not promise statistical significance or monotonic improvement.

**Persistence schema.** A run stores a unique ID, schema version, timestamps, status, immutable configuration, seed streams, physical convention, solver settings, dependency versions, code revision or source digest, and artifact checksums. Each strategy stores ordered acquired point IDs and values, iteration metrics, candidate selections/scores, fitted kernel settings, numerical warnings, model revision, model artifact, and prediction snapshots. Persist evaluation-set identity and labels separately from acquisition inputs. Include latest complete iteration and failure details. Prepared benchmark metadata records every seed, failed seed, and protocol configuration. A changed configuration creates a new run; it does not rewrite an old result.

### Interfaces & Contracts

- Physics accepts validated physical configuration and parameter pairs, and returns numerical observables, optional density matrices, solver settings, and diagnostics.
- The surrogate accepts acquired observations and a versioned fit policy; it returns a model revision that predicts mean and standard deviation for parameter pairs.
- Selection accepts a fitted model, candidate coordinates, already acquired IDs, and its own RNG state. It never accepts evaluation labels or a reference error map.
- The engine supports create, advance one complete paired comparison iteration, request pause, resume, and inspect status. Only one live experiment runs at a time; completed results remain inspectable.
- Evaluation receives model predictions and its isolated reference set and returns versioned metrics. The engine stores metrics without feeding reference labels back into selection.
- Storage supports list, save checkpoint, load run, load model, validate integrity, and export. Dashboard reruns must not recreate an experiment or repeat an acquired iteration.
- Model artifacts include the preprocessing state. Load only locally generated trusted artifacts; no arbitrary model-upload feature. Fail clearly on missing files, checksum failure, unknown schema, or incompatible dependency versions.
- Public application surface is the local dashboard. A separate HTTP API is unnecessary for this proof of concept.

### Behavior & Interactions

**Presentation path.** The landing view explains: “Qentis learns from simulated qubit behavior and chooses where to simulate next.” Offer Open saved run and Run experiment. The saved view shows its date, seed, scope, and Saved result label. Live runs show Live computation and actual stage/iteration. Start with a brief walkthrough of the uncertainty map and equal-budget comparison; then offer a short live run.

**Controls.** Keep |+⟩ fixed and visible in this version. Expose positive finite rate/time upper bounds, simulation budget, and integer seed in advanced controls, with safe caps: grid at most 31 × 31, total acquired points at most 64, and all coordinates within the configured nonnegative domain. Require positive domain extents, at least eight available initial points, and sufficient unique candidates for the budget. The agreed scientific preset is the presentation default; changed domains are exploratory and labeled accordingly.

**Run state.** New → validating → preparing reference → initial fit → selecting/simulating/fitting/evaluating/checkpointing → complete. Pause requests take effect after a whole paired iteration is committed. Resume restores both strategies, fitted artifacts, selection order, and RNG state from that checkpoint. A failed iteration is not included in a learning curve. On restart, an active run becomes interrupted and offers resume from its last complete checkpoint. Before the first checkpoint, offer restart. Do not advance budgets on failed solver calls.

**Charts.** Follow the existing Qentis design guide. Use teal solid reference curves, light-violet model curves, and amber dashed random-baseline curves with distinct markers. The Bloch sphere uses the reference state by default and labels its source; a time slider synchronizes it with the trajectory. Clearly label the Gaussian-process output as a learned observable, not full quantum-state tomography. Show the uncertainty map over candidate coordinates, with acquired points and the next selection. Show a separately labeled evaluation-error map over the fixed held-out coordinates. Hold color ranges fixed within a run, explicitly mark overflow, and avoid rescaling that makes improvement appear larger.

**Failures and safeguards.** Reject invalid settings before work begins. Keep the latest complete checkpoint after numerical or fitting failure, show the reason, and provide retry/resume where valid. Numerical failures stop the affected paired iteration. An artifact write failure must not display a successful save. Decreasing error is never an artificial animation. If fitting produces non-finite output or severely unstable covariance, report failure rather than changing models or deleting difficult points silently.

**Scientific validation.** Use solver tolerances initially set to absolute 1e-10 and relative 1e-8. Across boundary and interior cases, require maximum absolute discrepancy from the analytical x to be at most 1e-6. Require trace-one, Hermiticity, nonnegative eigenvalues, and Bloch radius at most one within tolerance 1e-8; check no-noise and zero-time limits and unchanged populations. Record tolerance changes explicitly. Failed reference validation blocks preparation of a presentation run.

## Testing Decisions

- **Physics unit tests:** analytical agreement, physical invariants, γ = 0, t = 0, large γt, invalid domains, and solver failure propagation. Test through the reference interface.
- **Model unit/integration tests:** training on actual numerical samples, finite predictions, nonnegative uncertainty, persisted preprocessing, and prediction agreement after model reload. Do not require the model to beat the analytical solution or random selection.
- **Engine tests:** no repeated candidates, no budget overruns, paired initial data, uniform seeded random selection, stable adaptive ties, and selection independence from evaluation labels. Verify changing held-out labels cannot change the next acquisition for an otherwise identical state.
- **Evaluation tests:** known metric examples, honest negative differences, correct aggregation across seeds, coverage calculations, and explicit distinction between variability and confidence intervals.
- **Storage integration tests:** fresh-process reload, interrupted checkpoint writes, corrupted/missing artifacts, unsupported schemas, and uninterrupted versus paused/restarted runs producing equivalent selection sequences and metrics within declared tolerance.
- **End-to-end tests:** run a tiny genuine experiment, save, restart, open, resume, and export; inspect a prepared benchmark; validate bad input and recoverable failure. Verify exported counts and values against displayed results.
- **Presentation QA:** on the actual laptop, exercise the short run, disconnected-network operation, screen-share-sized layout, keyboard focus, plot legends, loading/error states, and the saved-result fallback. Measure timing without introducing artificial delays.
- There is no application code or existing test convention to reuse. Prefer pytest for scientific/storage tests and the dashboard framework's supported application-testing interface for control/state checks, supplemented by rendered browser inspection.

## Out of Scope

- **Real quantum hardware:** explicitly deferred; all data is simulated.
- **Integrated chat assistant:** deferred to preserve the one-to-two-day proof-of-concept scope.
- **Multiple qubits, noise types, control pulses, and hardware calibration:** later scientific extensions after this small workflow works.
- **General research platform:** project workspaces, broad experiment management, dataset uploads, and a model registry are deferred. This version has local runs and model revisions only.
- **Hosted website and collaboration:** laptop presentation was chosen; cloud deployment, accounts, sharing, and multi-user concurrency are deferred.
- **Scientific PDF reports:** JSON/CSV downloads provide inspectable evidence first; polished report generation is deferred.
- **General training workbench:** no model-family chooser, architecture editor, continuous training service, or arbitrary model import. Training and reloading apply to this experiment's fixed surrogate.
- **Full-state learning and uncertainty guarantees:** the model learns one observable under a fixed physical setting. Its uncertainty is a model estimate, not a certified physical bound.
- **Guaranteed adaptive improvement or speedup:** neither is a condition for completion; report actual results and costs.

## Open Questions

No unanswered product question blocks implementation. Confirm during build:

- Actual laptop runtime and the largest short preset that remains comfortable to present.
- Whether measured interval coverage and adaptive behavior are useful enough to explain clearly; unfavorable results remain part of the presentation.
- Installed compatible dependency versions and model-artifact compatibility constraints.

Any adjustment to the benchmark protocol must happen before producing its final results and be recorded. Further scientific directions can be decided after the demonstration.

## Further Notes

The first release succeeds when the founder can clearly show a real, reproducible learning loop and explain its limitations to a scientist and funder. A concise three-to-five-minute walkthrough is a proposed presentation target.

The scalar response depends on the product γt, making this an intentionally simple and redundant two-coordinate learning problem. That limits scientific novelty but provides an independently checkable starting point. Do not conceal that structure or describe model interpolation as discovery of unknown physics. More difficult systems belong to later work.

The original long-term master plan is strategic context; the narrowed scope agreed in this conversation governs this build. The supplied logo and saved design guide govern visual direction. This specification is a build target, not evidence that implementation or validation has already occurred.

Primary implementation references: QuTiP documents numerical evolution through the Lindblad master-equation solver and collapse operators in its [master-equation guide](https://qutip.readthedocs.io/en/latest/guide/dynamics/dynamics-master.html). Scikit-learn documents predictive means and standard deviations in its [GaussianProcessRegressor reference](https://scikit-learn.org/stable/modules/generated/sklearn.gaussian_process.GaussianProcessRegressor.html). Verify exact calls against the pinned installed versions when building.
