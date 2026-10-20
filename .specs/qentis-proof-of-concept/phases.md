# Phases: Qentis Adaptive Quantum Discovery Proof of Concept

> Source spec: .specs/qentis-proof-of-concept/spec.md
> Status: approved to proceed on 2026-10-18. Phases 1–4 implemented and verified. See phase-four verification for measured results and rehearsal limits.

## Architectural Decisions

- **Scope:** a local English-language dashboard for a laptop presentation, using genuinely computed simulated data. No cloud services, hardware connection, accounts, or assistant.
- **Application:** Python, Streamlit, Plotly, QuTiP, and scikit-learn with compatible pinned versions. Keep scientific work independent of dashboard redraws. No separate HTTP API.
- **Navigation:** one local application root, `/`, with named views for Experiment, Saved runs, and Benchmark. These are dashboard views, not separate web routes. Use the same views as functionality grows; do not build a new application per phase.
- **Physics:** one qubit initially in |+⟩, H = 0, L = √(γ/2)σz. Learn x = 2 Re(ρ01) as a function of γ and t. Keep analytical validation separate from numerical training labels.
- **Model:** Gaussian-process regression with the fit policy from the spec. Adaptive selection maximizes model standard deviation; random selection is uniform without replacement. Keep their inputs and budgets comparable.
- **Evaluation boundary:** acquisition never receives held-out labels or measured error maps. Evaluation, visualization, and acquired-label costs have separate counters. Display model estimates and numerical reference distinctly.
- **Key models:** ExperimentConfig, Run, StrategyState, Observation, IterationCheckpoint, ModelRevision, EvaluationSet, and BenchmarkSummary. Preserve these concepts across phases without prematurely building a generic research platform.
- **Storage:** local versioned run records, immutable configuration, trusted model artifacts with preprocessing, provenance, checksums, and atomic checkpoints. Loading a run never silently changes its protocol.
- **Design:** follow the saved Qentis design guide and supplied logo. Light and dark modes, restrained violet identity, teal reference curves, amber random baseline, and legible labels at 1280 × 720.
- **Completion:** each phase connects real computation, stored state, and usable interface behavior. No decorative data or placeholder controls. The source spec remains authoritative for numerical tolerances, safety caps, budgets, metrics, and scientific limitations.

## Phase 1: Simulate and save a qubit experiment

**User stories:** #3, #4, #5, #12, #14, #18 (initial simulation and persistence scope).
**Depends on:** none.

**Status:** implemented. See [phase-one verification](../../docs/phase-one-verification.md) for scientific results, test coverage, browser checks, and relaunch instructions.

### What to build

Deliver a branded local dashboard where the presenter can choose a dephasing rate, run the numerical simulation, inspect a synchronized Bloch sphere and coherence trajectory, and reopen the saved numerical result after restarting. Show the fixed initial state, units, physical assumptions, solver convention, and numerical validation status. Establish the real run record and configuration boundary that subsequent phases extend.

### Acceptance criteria

- [x] The application opens locally with the actual Qentis logo, clear default settings, and a Simulation only label.
- [x] Running a valid configuration produces numerical reference states and observables, with a time slider connecting the Bloch sphere to the trajectory plot.
- [x] The solver meets the source spec's analytical agreement and physical-invariant criteria, including no-noise and zero-time cases; failed validation is visible and blocks presentation-data preparation.
- [x] The run is saved with configuration, solver settings, schema version, provenance, and integrity metadata; it can be reopened after a fresh application launch.
- [x] Invalid settings and numerical failures produce clear messages and never appear as successful results.
- [x] The layout, scientific labels, keyboard controls, and core visualizations are usable at 1280 × 720.

### Manual QA plan

1. **Normal trajectory:** Open `/` → Experiment, choose γ = 1 and maximum time = 5, then select Run simulation. **Expected:** a decaying x trajectory, fixed populations of 0.5, a Bloch vector shrinking along its original direction, and a visible numerical-reference label. Move the time slider to see both views update consistently.
2. **No-noise boundary:** Open `/` → Experiment, choose γ = 0 and maximum time = 5, then run. **Expected:** x stays at 1 and the Bloch vector stays at its initial position; the interface does not show dephasing that was not simulated.
3. **Invalid input:** Open `/` → Experiment and attempt a negative rate or nonpositive maximum time. **Expected:** the control prevents the value or explains the error before computation, preserving any previous valid result.
4. **Saved numerical result:** Run γ = 1 and maximum time = 5, note its run ID, restart using the documented launcher, then open `/` → Saved runs and select that ID. **Expected:** the same configuration and trajectory return with a Saved result label.
5. **Screen sharing:** Open `/` → Experiment at 1280 × 720, inspect the full chart labels, then use keyboard navigation through controls. **Expected:** readable values, visible focus, no overlapping logo or chart controls, and no horizontal page scrolling.

## Phase 2: Watch the model learn and compare experiment choices

**User stories:** #2, #3, #6, #7, #8, #9, #13, #14, #17, #18 (single-seed learning loop).
**Depends on:** Phase 1.

**Status:** implemented. See [phase-two verification](../../docs/phase-two-verification.md) for measured single-seed results, model reload and failure checks, and light/dark browser evidence.

### What to build

Extend the real experiment into a complete short live comparison. Generate the isolated evaluation reference set and shared initial observations, fit both models, and repeatedly acquire points using adaptive and random selection. Show the next adaptive point, estimated uncertainty, measured evaluation errors, and learning curves. Store each completed paired iteration and its model revision so the model can actually be reloaded and used to predict.

### Acceptance criteria

- [x] The short preset uses the spec's common eight initial samples and 16 additional acquired points per strategy, with visible seed, domain, budget, and actual stage.
- [x] Both strategies use the same model policy, starting data, candidate coordinates, and isolated evaluation set; acquired observations come from the numerical reference module.
- [x] Adaptive selection uses predictive standard deviation, excludes acquired points, and cannot access held-out labels. Random selection is seeded and without replacement.
- [x] The dashboard explains the loop in plain language and displays reference-versus-prediction trajectories, uncertainty, the next selection, a separate held-out error map, and equal-budget learning curves.
- [x] Counts distinguish acquired labels, evaluation preparation, visualization calls, and cache reuse; wall-clock timing is not presented as equivalent to sample efficiency.
- [x] Each completed paired iteration stores observations, selected points, predictions, metrics, and model artifacts with preprocessing. Reloaded predictions meet the spec's 1e-8 tolerance in the pinned environment.
- [x] Single-seed outcomes, estimated intervals, and predictions outside the physical range are labeled honestly; unfavorable results remain visible.
- [x] Model or solver failure stops the affected paired iteration, preserves the latest complete checkpoint, and does not advance its recorded budget.

### Manual QA plan

1. **Complete live loop:** Open `/` → Experiment, select the short preset and seed 0, then Run experiment. **Expected:** visible reference preparation and learning stages, increasing completed acquisition counts, and two real strategy curves ending at 24 acquired labels each. The initial eight labels are shared, not counted as eight extra acquisitions per step.
2. **Explain a selection:** During the same run, inspect the uncertainty map and the next-point label. **Expected:** a clearly marked coordinate and an explanation that uncertainty guides the choice; the separate error map is labeled evaluation-only.
3. **Read model limits:** After completion, inspect the prediction trajectory and interval legend. **Expected:** numerical reference and model estimates are distinguishable without color alone; uncertainty is described as estimated. If any prediction leaves [−1, 1], the value remains inspectable and is flagged rather than silently clipped.
4. **Reopen a trained run:** Note the completed run ID, restart the app, and open `/` → Saved runs → that ID. **Expected:** stored learning curves and model revision appear; selecting trajectory coordinates produces predictions from the reloaded model without silently retraining it.
5. **Budget validation:** Open `/` → Experiment → advanced controls and attempt a total budget above 64. **Expected:** the value is prevented or rejected clearly; no run starts with an unsupported budget.
6. **Presentation readability:** Open the completed result at 1280 × 720 and inspect chart tooltips and legends. **Expected:** uncertainty, error, adaptive strategy, random strategy, and numerical reference can be identified unambiguously.

## Phase 3: Pause, recover, reproduce, and export

**User stories:** #11, #12, #13, #14, #15, #16.
**Depends on:** Phase 2.

**Status:** implemented and verified. See [phase-three verification](../../docs/phase-three-verification.md) for recovery, reproducibility, export, and browser evidence.

### What to build

Make the complete learning experiment reliable across interruptions. Connect pause/resume controls to atomic paired-iteration checkpoints, preserve random-generator and model state, recover interrupted runs, and provide inspectable exports. Handle incompatible or incomplete saved artifacts through the same saved-run interface. This phase delivers a usable recovery and evidence-sharing workflow, rather than a storage-only task.

### Acceptance criteria

- [x] Pause takes effect after a whole paired iteration is committed, with the saved iteration clearly identified. Resume continues both strategies without duplicate observations or changed configuration.
- [x] A dashboard redraw does not restart a run or repeat an iteration; only one live experiment is active at a time.
- [x] Restarting during a run marks it interrupted and offers the last complete checkpoint; runs without a checkpoint offer restart instead of misleading resume.
- [x] Interrupted writes retain a valid previous checkpoint. A failed save is never reported as successful.
- [x] Resumed selection order and metrics agree with an uninterrupted equivalent under the source spec's tolerances; fresh-process model reload retains preprocessing and predictions.
- [x] Missing, corrupt, unknown-schema, and incompatible artifacts produce specific recoverable messages without erasing the original run or executing arbitrary uploaded models.
- [x] Working downloads include configuration/provenance JSON and observation/metric CSV; values and counts match the selected run.
- [x] Editing settings creates a new run rather than rewriting historical results.

### Manual QA plan

1. **Pause and continue:** Open `/` → Experiment, start the short preset with seed 0, and select Pause after this step while it is active. **Expected:** both strategies stop at the same completed budget, the saved iteration is visible, and Resume continues from it.
2. **Interrupted session:** Start another short run with seed 1, close the application after at least one completed paired iteration, and relaunch it. Open `/` → Saved runs and select the interrupted ID. **Expected:** an Interrupted label and a clear resume choice; previously completed observations remain visible.
3. **Export evidence:** Open a completed run in `/` → Saved runs and download its JSON and both CSV outputs. Open them in a text viewer or spreadsheet. **Expected:** the displayed run ID, seed, observations, and final metrics match the files; units and metric names are understandable.
4. **Preserve history:** Open a completed seed-0 result, change the next experiment's seed to 2, and run. Return to Saved runs. **Expected:** both run IDs remain available, and the old configuration is unchanged.
5. **Damaged result:** Using a disposable copy of a saved run, remove one model artifact through the local file manager, then open that copy in `/` → Saved runs. **Expected:** an explicit missing-artifact message and access to intact metadata where possible; the original result remains usable.
6. **Empty library:** Launch with a new empty local results location using the documented setup option, then open `/` → Saved runs. **Expected:** a clear empty state with a route back to Run experiment, not an exception or a fabricated example.

## Phase 4: Prepare the benchmark and meeting-ready demonstration

**User stories:** #1, #2, #4, #8, #9, #10, #16, #17, #18.
**Depends on:** Phase 3.

**Status:** implemented and verified. See [phase-four verification](../../docs/phase-four-verification.md) and [founder walkthrough](../../docs/founder-walkthrough.md). Network isolation was verified through blocked external requests; physical Wi-Fi disconnection remains a presenter rehearsal step.

### What to build

Deliver the final presentation experience using the working experiment engine. Run the fixed ten-seed benchmark, save every outcome, aggregate results, and make them inspectable in the dashboard. Provide a clearly labeled saved presentation run, a short live preset, and a concise founder walkthrough. Measure the default run on the actual laptop and finish the offline presentation path.

### Acceptance criteria

- [x] The fixed benchmark uses seeds 0–9 and the spec's eight initial plus 24 additional acquired labels per strategy; protocol, model policy, and evaluation identity are recorded.
- [x] The Benchmark view shows all seeds, failures, mean error curves, standard-deviation bands labeled as variability, final RMSE differences, and wins/ties/losses with the declared tie tolerance.
- [x] All outcomes are retained without seed cherry-picking or repeated protocol tuning against the final evaluation set. Any pre-benchmark protocol adjustment is disclosed.
- [x] The opening view offers a real saved presentation result, clearly labeled and dated, plus a short live experiment. Saved data is not animated or described as live computation.
- [x] The scientific assumptions and simple γt response are accessible; presentation copy explains that this is a workflow proof of concept rather than new quantum physics or guaranteed superiority.
- [x] The short run is measured on the presentation laptop against the spec's 60-second target. If needed, permitted symmetric tuning is settled before generating the final benchmark; the measured timing and hardware are recorded.
- [x] All core presentation functionality works without network access after setup, including fonts, logo, saved runs, model predictions, live computation, and downloads.
- [x] The founder receives setup/relaunch instructions and a three-to-five-minute walkthrough covering saved evidence, interpretation, a live run, and honest limitations.
- [x] The final experience meets the source spec's acceptance criteria; earlier phase completion alone does not imply the complete proof of concept is ready.

### Manual QA plan

1. **Prepared evidence:** Open `/` → Benchmark and select the prepared benchmark. **Expected:** seeds 0–9 are individually inspectable, failures remain listed, variability bands have an explicit meaning, and the summary does not claim an adaptive win unless the recorded results support it.
2. **Saved opening:** Relaunch the app, open `/`, and choose Open saved run. **Expected:** a genuinely computed result opens promptly with its date, seed, protocol, source labels, and readable learning curves.
3. **Offline rehearsal:** Disconnect the laptop from the network after setup, relaunch the app, open the saved result, run the short seed-0 preset, and download its results. **Expected:** every step works locally, with no missing fonts, external requests required for operation, or account prompts.
4. **Meeting timing:** On the actual presentation laptop, open `/` → Experiment, run the short preset, and time it from launch to complete. **Expected:** real progress is visible, measured time is documented, and the saved result remains a clear fallback if live computation is slower than expected.
5. **Founder walkthrough:** At 1280 × 720, follow the supplied walkthrough without using terminal commands during the demonstration. Explain the trajectory, uncertainty, equal-budget comparison, and observed outcome. **Expected:** the story is understandable within three to five minutes, including a candid explanation of the model's limits.
6. **Do not hide outcomes:** Open each prepared seed from Benchmark, including any where adaptive selection loses or a run fails. **Expected:** accessible results and clear status; there is no filter that silently removes inconvenient seeds from the summary.

## Coverage and Execution Order

| Spec stories | Delivered by |
| --- | --- |
| #1 | Phase 4 |
| #2 | Phases 2 and 4 |
| #3 | Phases 1 and 2 |
| #4 | Phases 1 and 4 |
| #5 | Phase 1 |
| #6, #7 | Phase 2 |
| #8, #9 | Phases 2 and 4 |
| #10 | Phase 4 |
| #11 | Phase 3 |
| #12 | Phases 1 and 3 |
| #13 | Phases 2 and 3 |
| #14 | Phases 1, 2, and 3 |
| #15 | Phase 3 |
| #16 | Phases 3 and 4 |
| #17 | Phases 2 and 4 |
| #18 | Phases 1, 2, and 4 |

All 18 stories are covered. The original spec's deferred capabilities remain out of scope.

Build in order: **1 → 2 → 3 → 4**. Each phase has a complete demoable outcome. Verify its acceptance criteria and record any limitations before proceeding. Tests are written separately using the test-write skill after each phase's implementation, following the source spec's testing decisions; no automated-test design is added here.

The core phases depend on shared run and scientific contracts, so sequential execution is recommended for this deadline. Presentation copy and a rehearsal outline can be drafted while Phase 3 is being completed, but the final benchmark and meeting rehearsal require the finished recovery flow. This plan does not dispatch agents or begin implementation.

## AI Implementation Handoff

For each phase, read the source spec, the design guide at `docs/design/QENTIS_DESIGN_GUIDE.md`, and the existing implementation before making changes. Implement the complete phase using real computation and persisted results. Reuse the application and scientific contracts established by earlier phases. Keep later-phase features out of the current work unless required to make its acceptance criteria work.

At the end of each phase, report the usable outcome, verification performed, outstanding limitations, and completion status against its acceptance criteria. Update this plan with actual progress; leave unfinished criteria unchecked. Do not claim completion based on interface appearance alone.

Suggested task prompts:

1. **Phase 1:** Implement Phase 1 of this plan: a branded local qubit simulation with validated numerical results, synchronized visualizations, and saved-run reopening. Follow the source spec and design guide. Verify the complete user flow and record progress.
2. **Phase 2:** Implement Phase 2 on top of the completed simulation: the genuine adaptive-versus-random learning loop, isolated evaluation, model reload, and clearly labeled visual evidence. Verify equal budgets and prevent evaluation leakage. Record progress.
3. **Phase 3:** Implement Phase 3 on top of the working learning loop: pause, resume, interruption recovery, reproducible continuation, artifact error handling, and downloadable evidence. Verify that saved history survives these workflows. Record progress.
4. **Phase 4:** Implement Phase 4 using the finished engine: the fixed ten-seed benchmark, saved presentation result, offline live demonstration, measured runtime, and founder walkthrough. Retain every outcome and verify presentation readiness. Record progress.
