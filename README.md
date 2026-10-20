# Qentis · qubit dephasing

A local, English-language dashboard for numerically simulated qubit behavior
and a real adaptive-versus-random learning comparison. **Phases one through four**
are implemented, with light and dark modes, persistent models, pause/resume,
interruption recovery, and JSON/CSV evidence downloads. The fixed ten-seed benchmark, saved presentation opening, and founder walkthrough are ready.

## Setup and launch

Requires **Python 3.11**, available on the presentation laptop as `python3.11`.
Run these commands from this directory:

```sh
./setup.sh
./run.sh
```

Open [Qentis locally](http://localhost:8501). Stop with **Ctrl+C** in the terminal;
relaunch with `./run.sh`. Setup needs internet access to install packages. After
setup, computation, logo, fonts, charts, and saved results work locally without
network access, accounts, or API keys. Telemetry is disabled and the server binds
to the loopback address. The launcher can be run from any directory.

If Python has a different executable path:

```sh
QENTIS_PYTHON=/path/to/python3.11 ./setup.sh
```

`requirements.txt` declares direct scientific/UI dependencies;
`requirements.lock` pins the full verified environment. `setup.sh` installs that
lock. Avoid upgrading dependencies for an existing saved demonstration.

## Run a learning comparison

1. Open **Experiment → Learning comparison**. The short preset uses seed 0,
   γ ∈ [0, 2], t ∈ [0, 5], a 21 × 21 candidate grid, eight shared initial points,
   and 16 additional acquisitions per strategy (24 labels each).
2. Select **Run experiment**. Actual stages include reference preparation,
   initial observations/fit, selection, simulation, fitting/evaluation, and atomic
   checkpointing. Completed paired steps update the measured learning curves.
   Computation runs independently of view changes; one learning writer owns the
   results library at a time.
3. Use **Learning curves** for equal-budget RMSE; **Selection and error** for
   model-estimated uncertainty and the separate evaluation-only error map.
   Expand **Inspect model revisions** to see an earlier completed step and its
   next adaptive choice. The final revision schedules no additional query.
4. Under **Qubit trajectory**, choose a stored rate and time. The Bloch sphere
   shows the numerical reference; the curves and readout compare actual model
   estimates with it. Shaded intervals are mean ± 1.96σ estimates, not guaranteed
   physical bounds. Means and intervals are never clipped.
5. **Record and diagnostics** exposes errors, interval coverage/width, physical
   excursions, observations, kernels, warnings, separate counters and provenance.
6. Restart and open **Saved runs → Open selected run**. Models and preprocessing
   reload without retraining or numerical acquisition. Slider changes use these
   models and stored visualization states.
7. Switch **Dark mode** off for light mode, or on for dark mode. The choice stays
   within the current browser session, including navigation and computations.

The fixed model policy is constant × Matérn-5/2 with two length scales. Inputs
are divided by their domain upper bounds; target normalization is off; numerical
regularizer α = 1e−10; L-BFGS-B has zero optimizer restarts. Both strategies use
identical settings and deterministic model seeds. Adaptive selection maximizes
predictive standard deviation among unqueried candidates, with stable first-max
ties. Random selection is seeded uniform without replacement. Independent initial,
random and model seed streams are recorded. There are no evaluation-based tuning
choices. Changed domains, grids or budgets are labeled exploratory; hard caps are
31 candidates per axis and 64 total labels per strategy.

A fixed-seed set of 400 interior coordinates is numerically evaluated separately
and is disjoint from the candidates. Its labels enter only evaluation. Training
labels are one numerical query each (or the exact zero-time initial condition).
Shared cached values still count toward each strategy's learning budget. Costs
for numerical validation, evaluation, visualization, training and cache reuse are
recorded separately. Wall-clock time is not sample efficiency. Outcomes from one
seed do not establish superiority; this response intentionally depends simply on
γt. The prepared benchmark retains all seeds, including the two outcomes favoring random selection.

## Pause, recover, and download evidence

- During a live run, select **Pause after this step**. Both strategies finish and
  save the current whole pair before stopping. Even an immediate request waits
  for the first shared fit to be saved. The displayed paused budget is confirmed
  on disk. A short run can finish before a late pause request arrives.
- Select **Resume experiment** to continue the same run ID. It restores saved
  models, observations, cached acquired values, and random state. Current form
  settings describe a new run; they never change a resumed protocol.
- After a server restart, use **Saved runs → Open selected run**. Deliberately
  paused runs stay Paused. An unfinished active run becomes Interrupted and
  offers Resume at its latest complete paired checkpoint. A run interrupted
  before the first checkpoint offers **Restart as new run** instead; its original
  intent remains preserved.
- A numerical or fitting failure retains the last complete pair and its reason.
  Resume retries from that saved state once the underlying problem is resolved.
  Unfinished work does not enter learning curves or confirmed-step budgets.
- Missing, corrupt, unknown-schema, or incompatible artifacts block opening and
  continuation with an explicit message. Restore the complete original folder
  from a backup or restore its recorded pinned environment. Intact configuration
  and date remain visible when available. The app never silently repairs or
  erases the original record.
- Open **Download evidence** on a saved or completed/paused result. The completed
  revision selector controls all three downloads: configuration/provenance JSON,
  observations CSV for both strategies, and metric-history CSV through that
  revision. Filenames include run ID and revision; numerical units, label counts,
  interval diagnostics, and source meanings are explicit. Downloads do not
  retrain, solve, or advance a run.

Changing settings and selecting Run experiment creates another run. Redrawing,
changing themes, inspecting a model, or switching views does not launch another
worker. Conflicting learning starts are rejected; the OS writer lock is released
when a worker stops or its process exits. Browser closure alone does not pause a
running server; use Pause or reopen Saved runs to inspect the resulting status.

## Inspect a numerical simulation

1. Open **Experiment → Qubit simulation**. Defaults are γ = 1, maximum time = 5, 201 time samples.
   The initial state stays fixed at |+⟩. γ is in inverse dimensionless time units.
2. Select **Run simulation**. The app validates the reference, solves the
   trajectory, checks its states, and commits the result to disk. A save failure
   is shown as a failure, and the previous displayed result is retained.
3. Move **Inspect time** with the mouse or arrow keys. The Bloch vector, trajectory
   marker, selected time, and numerical readout all use the same stored state.
   Inspecting does not repeat the solver or create another run.
4. Inspect **Physical assumptions and solver convention** and **Saved record and
   numerical validation** for the model, tolerances, run ID, and provenance.
5. Stop and relaunch the app. Open **Saved runs**, choose the run ID, and select
   **Open selected run**. The original numerical states reopen with a **Saved
   result** label. Reopening performs validation but never reruns the solver.
6. For the no-noise boundary, run γ = 0. Coherence stays at 1 and populations
   stay at 0.5. This is a separate saved result.

The settings describe the next simulation; each visible result is labeled with
its own original configuration. Changing settings never rewrites past results.
The controls constrain γ to [0, 2], time to (0, 5], and time samples to [2, 1001].
Time samples are visualization outputs, not acquired learning observations.

## Scientific contract

With ℏ = 1, H = 0, initial state |+⟩, and L = √(γ/2) σz, the numerical solver
evolves density matrices using QuTiP `mesolve`. The plotted observable is
**x = 2 Re(ρ₀₁)**. y = −2 Im(ρ₀₁), z = ρ₀₀ − ρ₁₁, and purity = Tr(ρ²).
The analytical x = exp(−γt) is used only for validation. Reference data comes from numerical evolution, except the exact initial state
for a zero-time query. Learned means and uncertainty come from the fitted Gaussian process.

Solver settings: Adams, absolute tolerance 1e−10, relative tolerance 1e−8,
10,000 internal steps maximum, output normalization off. The independent
reference gate checks γ = 0, 1, 2 on t = [0, 1e−8, 0.1, 1, 5], plus a standalone
zero-time query, before preparing each saved result. The actual trajectory is
also validated. Maximum analytical discrepancy must be ≤1e−6; trace-one,
Hermiticity, eigenvalues, Bloch radius, fixed populations, and y/z use 1e−8.
Failed validation blocks saved presentation data. No analytical fallback is used.

This is a simulation workflow proof of concept. The scalar response depends on
γt, and does not demonstrate new physics, quantum advantage, or hardware results.

## Results and integrity

By default results are written to `runs/` beside the application (Git-ignored).
To choose another local folder, including an empty QA library:

```sh
QENTIS_RUNS_DIR=/absolute/path/to/results ./run.sh
```

Phase-one simulation folders `qentis-<unique-id>/` contain:

- `run.json`: schema version, immutable configuration, timestamps, physical
  convention, solver settings, boundary validation, trajectory diagnostics,
  warnings, separate computation counters, timing, and provenance.
- `trajectory.npz`: times and complex 2 × 2 density matrices. Loading explicitly
  disables pickle. Observables are derived from these numerical states.
- `manifest.json`: SHA-256 checksums and byte lengths for the two artifacts.

All artifacts are flushed to disk in a hidden staging directory before a single
atomic directory rename commits the result. Existing run IDs cannot be
overwritten. Abandoned staging directories are ignored. Missing, changed,
unsupported-schema, and dependency-incompatible artifacts get explicit errors
and are preserved. Files are never silently migrated or repaired. The manifest
detects accidental corruption; it is not a cryptographic signature.

To back up or move results, copy the complete run directory. To reproduce the
environment, use its recorded dependency versions and Python 3.11. Phase one
numerical results remain compatible. Phase-two model artifacts are also non-executable JSON; there is no model upload.

New learning folders use **schema 3**:

- `run.json` and `manifest.json`: immutable intent, settings, seeds, model policy,
  physical convention and provenance, written before expensive preparation.
- `prepared/`: immutable numerical evaluation and visualization artifacts plus
  reference validation and their checksum manifest.
- `iteration-000/` through the confirmed pair: observations, selections,
  prediction snapshots, metrics, counters, RNG state and both JSON model artifacts
  with preprocessing, plus a checksum manifest.
- `latest.json`: atomically confirmed revision and lifecycle status, or −1 before
  any complete checkpoint. Failed status also includes a diagnostic.

Models store input scaling, scaled training coordinates, fitted kernel, Cholesky
factor and dual coefficients. Reload checks means and standard deviations against
saved candidate/evaluation snapshots at absolute tolerance 1e−8. No solver or fit
is needed to inspect saved predictions. Existing schema-two learning records and
schema-one numerical simulations remain readable; their original layouts are
preserved when a legacy learning run continues.

A failed write never advances the confirmed budget. If a crash leaves a revision
beyond the pointer, a retry preserves it under a hidden `.unconfirmed-…` name and
writes a newly confirmed revision. Already confirmed history is not rewritten.
Configuration remains immutable. Copy the whole folder when backing up a run;
checksum manifests detect accidental corruption, rather than authenticate it.
There is no arbitrary model-upload feature.

Schema-three elapsed computation includes preparation and numerical/model work;
it excludes checkpoint writes, idle pause time and rendering. Legacy records
retain their original timing meaning, shown explicitly. Counts describe confirmed
paired steps; retried unfinished work does not become acquired learning labels.
Wall-clock time is not sample efficiency.

## Verification

```sh
.venv/bin/python -m pytest -q
```

Tests exercise the public physics/storage interfaces and Streamlit's application
testing interface, including a separate-process reload. Test output uses
temporary results folders and does not seed the user's library. See
`docs/phase-one-verification.md`, `docs/phase-two-verification.md`,
`docs/phase-three-verification.md`, and `docs/phase-four-verification.md` for measured results and browser QA evidence.

The implementation is organized as immutable configuration, physics reference,
run creation, provenance, repository, charts, and dashboard modules. Scientific
modules do not import Streamlit or depend on a browser session.


## Presentation and benchmark

The default library includes a dated seed-0 short result. On Experiment, choose
**Open saved run** to inspect it; **Run experiment** starts a new live comparison.
The **Benchmark** view lists all ten fixed seeds, mean RMSE curves with variability
bands, wins/ties/losses, and JSON/CSV downloads. Open any seed, including 6 or 7
where random selection had lower final RMSE. The benchmark uses 32 labels per
strategy, while the short live preset uses 24.

To prepare a new library on a different laptop, before the meeting:

```sh
.venv/bin/python -m qentis.benchmark --root runs
```

This measures the unchanged short preset, records hardware/provenance, and then
computes all seeds 0–9. Preparation is restartable; terminal failures are retained
and never replaced. It takes the same writer lease as live learning. Keep the
whole `runs/` folder, not only `benchmark.json`: every result depends on its model
and numerical artifacts. The configured `QENTIS_RUNS_DIR` library must match the
explicit `--root` supplied here. Default results are local and Git-ignored.

On this MacBook Air (Apple M3, 8 cores, 16 GB), the short computation took 0.60 s
through the final save; a browser launch-to-visible-completion rehearsal took
1.28 s including automation overhead. These timings do not equate sample budget
with compute cost. See [the founder walkthrough](docs/founder-walkthrough.md)
for a 3–5 minute meeting script and [phase-four verification](docs/phase-four-verification.md)
for full results, conditions and limitations.
