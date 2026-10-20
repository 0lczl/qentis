# Phase-three implementation and verification

Completed October 18, 2026 (Asia/Riyadh). Phase three adds pause, recovery,
reproducible continuation and evidence downloads to the existing scientific
comparison. The fixed benchmark and meeting rehearsal remain phase four.

## Compact handoff

Before starting this phase, `docs/phase-two-handoff.md` captured the completed
phase-two scope, contracts, verification, files and remaining work. This is a
durable compact handoff; automatic conversation compaction is controlled by the
app and was not claimed as an agent-triggered operation.

## Delivered behavior

One background learning worker owns the results library using an OS writer lock.
Streamlit polls actual stage and confirmed progress while it is active; it does
not call scientific work from redraws or add artificial computation delays.
Pausing finishes a whole pair and saves it before stopping. Resume reloads under
the writer lock and restores observations, preprocessing/models, RNG state and
acquired-value cache from the confirmed checkpoint. A new settings form starts a
new run; it cannot change a resumed protocol or old history.

New schema-three records save immutable intent before expensive reference
preparation. Prepared reference artifacts and complete pairs are immutable and
checksummed. An atomic pointer records the confirmed pair and lifecycle status.
After process exit, an unfinished active record is Interrupted; a deliberately
paused record stays Paused. Before the first checkpoint, the UI offers Restart as
new run and retains the original intent rather than inventing a resume state.

Solver/model failures preserve the latest complete pair. A failed pointer write
does not increase its budget. A complete but unconfirmed revision is retained
separately on retry instead of blocking continuation or overwriting history.
Missing, corrupt, unknown-schema and incompatible artifacts block continuation
with specific errors. The original files remain in place; intact configuration
and date are available where possible. No uploaded executable models are loaded.

The selected completed revision controls three working downloads: configuration
and provenance JSON; both strategies' observations CSV; and metrics-history CSV
through that revision. Run ID, revision, settings, units, counts, evaluation
identity, model warnings and scientific limits accompany the evidence.

## Automated verification

`.venv/bin/python -m pytest -q` → **108 passed**.

`compileall` passed for `app.py`, `qentis`, and `tests`; `pip check` reported no
broken requirements in the existing Python 3.11.16 pinned environment.

The 87 prior cases remain passing. Twenty-one additional cases cover:

- Pause/reload/resume versus uninterrupted runs for seeds 0 and 2: exact
  observations, selections, RNG state and cost counts; metric agreement at
  absolute tolerance 1e−8. Tested grid 7 × 7, total budget 16, pause after paired
  step 3 (11 labels each).
- A fresh process exiting after two confirmed revisions, followed by same-ID
  continuation and agreement with the uninterrupted protocol.
- A killed worker process: its OS lock releases, checkpoint zero is retained,
  another worker reopens it as Interrupted and completes it.
- A pause requested while the external sklearn fit is in flight: both strategies
  finish, stop at nine labels each, and a second writer is rejected.
- Interrupted pre-checkpoint intent: no false model is offered; restarting creates
  another ID while preserving the old settings and record.
- A failed write after a revision is stored but before pointer confirmation:
  previous bytes remain unchanged, the unconfirmed artifact is preserved, and
  retry completes with the uninterrupted observations and metrics.
- JSON and both CSVs for revisions zero and two: exact IDs, coordinates,
  observations, metrics, budgets and revision-scoped history.
- Legacy schema-two learning continuation, preparation failure without a false
  checkpoint, and successful resume after an external fit failure recovers.
- Missing/invalid pointers, missing model and unknown schema: resume fails without
  modifying the original artifacts.
- Dashboard pause through a theme redraw, saved paused-run resume, restart-only
  pre-checkpoint state, missing-model guidance without stale charts, and new
  settings creating a new ID without rewriting historical bytes.

Fault injection is confined to external numerical, fitting, filesystem and
process boundaries. The actual public scientific implementation runs in tests.
The implementation has no test-only delay, fake model, analytical fallback, or
synthetic learning curve.

## Browser verification

The real default seed-zero run `qentis-16417174aca84474bffa841ea9cf73eb` was paused
using its visible button at paired step zero (eight shared labels each). After
stopping/relaunching the server, Saved runs reopened it as Paused. Resume completed
the same ID at 24 labels each with 17 paired revisions. Final RMSE remained
0.0538601652272759 adaptive and 0.0556468597828022 random, consistent with phase
two. This is a single-seed workflow check, not a benchmark result.

All three files were downloaded through the actual browser buttons. Their bytes
exactly match exports from the persisted paused revision zero. Disposable genuine
numerical records in a separate `/tmp` QA library exercised Interrupted at nine
labels, interruption before a checkpoint, and a deliberately missing model. No
user-library artifact was damaged for error testing.

Reviewed desktop at 1440 × 900, laptop at 1280 × 720, and mobile at 390 × 844 in
both themes. Controls wrap and export buttons stack on mobile. Normal vertical
scrolling reveals lower scientific evidence. Inspected page widths had no
horizontal overflow. The bounded visual pass corrected the native JSON viewer's
inline dark background in light mode; its measured background/text now match
#eeebf3/#20182d. Labels retain simulation-only, single-seed and estimated-interval
limits. The mechanical detector returned no findings on the changed app/UI
targets; no repeated detector loop was used.

Screenshots are in `.impeccable/review/phase-three/` (Git-ignored): both paused
1280 captures, dark desktop, both mobile captures, both desktop export captures,
mobile exports, completed result, Interrupted, before-checkpoint, and both
missing-model captures. Fresh finish review found no material rendered correction in the 13 captures.
Its sole requested fix was stale design documentation; DESIGN.md and its paired
sidecar now describe the implemented phase-three states and downloads. The final
reviewer verdict is **ship**, with no remaining findings. The documenter agent
hit its account usage limit, so the documented degraded in-thread role replaced
that handoff; the independent finish reviewer verified the resulting correction.
Token references, palette metadata, narrative parity and the eight completed
phase-three plan criteria were checked. The original visual system is preserved.

## Use and limits

Run `./run.sh`, open <http://localhost:8501>, then Run experiment → Pause after
this step → Resume experiment. Reopen through Saved runs after restart; use
Download evidence and the revision selector for inspectable artifacts.

Schema-one simulations and schema-two learning records remain compatible.
There is no silent schema migration. Browser closure alone does not pause the
server worker. Schema-three timing excludes checkpoint writes, idle pauses and
rendering; counts apply to confirmed paired steps. Restoring damaged artifacts
requires an intact backup or the recorded environment, not automatic repair.

The ten-seed benchmark, prepared presentation opening, complete disconnected-OS
rehearsal, meeting runtime measurement and founder walkthrough remain unverified
phase-four work.
