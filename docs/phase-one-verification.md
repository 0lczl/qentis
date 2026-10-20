# Phase-one implementation and verification

Completed October 18, 2026 (Asia/Riyadh). This verifies the simulation and saved
result phase. It does not mark the later learning, recovery, or benchmark phases
complete. Saved numerical records retain their actual UTC creation timestamps.

## Delivered workflow

`./run.sh` opens one local Streamlit application with Experiment and Saved runs
views. The original logo, locally bundled IBM Plex fonts, dark research interface,
and Simulation only label are present. The presenter runs numerical dephasing,
inspects synchronized Bloch/trajectory views, then reopens the same states after
a process restart. Configuration, units, physical convention, solver settings,
validation results, provenance, counters, and integrity metadata are inspectable.

Computation is separate from dashboard inspection. A slider redraw does not
rerun a solver or save another run. Completed results use immutable configuration
and atomic directory commits; a failed calculation or save never replaces a
previous valid result. A failed reopen does not display a stale successful load.

## Verified environment

- macOS 27.0.1, Apple Silicon arm64; Python 3.11.16.
- QuTiP 5.2.1, NumPy 2.2.6, SciPy 1.17.1.
- Streamlit 1.50.0, Plotly 6.3.1, scikit-learn 1.7.2.
- Full environment pinned in `requirements.lock`; `pip check` reports no broken
  requirements. `setup.sh` was exercised against this environment and its
  numerical-reference startup gate passed.

The initially attempted SciPy 1.15.3 wheel failed macOS's Mach-O loader checks
before simulation could run. SciPy 1.17.1 loads and passes the scientific tests
here, so that tested version is pinned. No third-party binary was patched.
An analogous loader error is documented in the upstream
[SciPy issue](https://github.com/scipy/scipy/issues/25635).

## Scientific evidence

For γ = 1, maximum time = 5, and 201 samples:

| Check | Measured value | Required bound |
| --- | ---: | ---: |
| Maximum analytical x discrepancy | 1.850981234952087e−8 | ≤ 1e−6 |
| Maximum trace error | 2.220446049250313e−16 | ≤ 1e−8 |
| Maximum Hermiticity error | 0 | ≤ 1e−8 |
| Minimum eigenvalue | 0 | ≥ −1e−8 |
| Maximum Bloch radius | 0.9999999999999998 | ≤ 1 + 1e−8 |
| Maximum population error | 1.1102230246251565e−16 | ≤ 1e−8 |
| Maximum y/z magnitude | 0 | ≤ 1e−8 |

The independent gate covers γ = 0, 1, 2 at t = [0, 1e−8, 0.1, 1, 5], plus a
standalone zero-time state. Its maximum analytical discrepancy in the measured
run was 1.549915945586733e−8. Tests also cover γt = 100, solver exhaustion,
non-finite solver output, and a plausible but incorrect constant reference.
Failed reference validation blocks presentation-run preparation.

A measured warm scientific solve plus reference validation took approximately
0.003 seconds for the default configuration. This excludes imports, provenance,
disk writes, and browser rendering. It is not a measurement of the later learning
loop or its 60-second presentation target.

## Automated verification

Final command: `.venv/bin/python -m pytest -q` → **58 passed**.

| Area | Cases | Behavior covered |
| --- | ---: | --- |
| Configuration | 16 | Finite values, safe bounds, sample limits, immutable settings |
| Physics | 22 | Numerical agreement, physical invariants, boundaries, failures, validation gate |
| Repository | 13 | Exact fresh-process reload, history, missing/corrupt files, schema/dependency mismatch, atomic-save failure, empty library |
| Dashboard | 7 | Run/save, synchronized slider without solver calls, fresh-session reopen, visible failures, retained prior result, empty-state navigation, failed reload |

Tests use real numerical solves and temporary local repositories. Fault injection
is limited to external solver/filesystem boundaries. There is no analytical
replacement for failed numerical data.

## Browser and presentation checks

- Ran the actual local app with γ = 1 and t ≤ 5. Both charts and the readout use
  the same selected stored state. All default numeric inputs pass native browser
  validity checks.
- Ran γ = 0 with external HTTPS requests blocked in the test browser. The
  complete plotted coherence range was [0.9999999999999998,
  0.9999999999999998], with populations 0.5 and purity 1. This browser-level
  check is not a claim that the operating system's network was disconnected;
  the complete offline meeting rehearsal remains a later-phase requirement.
- Stopped and relaunched the server, then reopened the original run ID in Saved
  runs. It displayed the original states and a Saved result label.
- A negative-rate input was rejected by native browser range validation before
  computation. The existing valid trajectory remained available. Backend tests
  separately reject negative/non-finite settings and nonpositive maximum time.
- ArrowRight and PageUp change the time selection. The focused slider has a
  visible 2 px violet outline. Run controls and navigation are keyboard operable.
- Verified no horizontal overflow at 1280 × 720 and 390 px width. At narrow
  widths, settings and scientific plots stack; vertical scrolling exposes the
  full trajectory legend, numerical values, and diagnostics.
- Inspected initial and decayed Bloch states at 1280 × 720. The sphere occupies
  approximately 210 px vertically with unclipped labels. The neighboring
  quantitative trajectory retains its 300 px chart height.
- Font loading and computed styles confirm local IBM Plex Sans. Captions use
  full-opacity muted text. No Plotly deprecation alerts remain in the dashboard.
- The finish reviewer scored the enlarged sphere, caption contrast, and default
  input validity fixes resolved, with a **ship** disposition for those fixes.

Screenshot evidence is in `.impeccable/review/` (Git-ignored):
`desktop.png`, `user-1280-initial.png`, `user-1280.png`, `mobile.png`,
`mobile-science.png`, and `mobile-readout.png`.

## Relaunch and review

Run `./run.sh`, then open <http://localhost:8501>. Use Saved runs to reopen any
genuinely computed local result, or Experiment → Run simulation for a new one.
For a new empty library, set `QENTIS_RUNS_DIR=/absolute/path/to/empty-results`
when launching. Full setup, conventions, storage layout, and presenter steps
are in `README.md`.
