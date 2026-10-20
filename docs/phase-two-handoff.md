# Compact handoff · phase two → phase three

Phase two and light/dark modes are complete. The user authorized phase three on
2026-10-18 after asking for a compaction. This file is the durable compact handoff;
automatic conversation compaction is controlled by the app.

- Source of scope: `.specs/qentis-proof-of-concept/phases.md`, phase three, and
  `spec.md`. Phase four remains pending.
- Implementation: Python 3.11.16, pinned Streamlit/Plotly/QuTiP/sklearn; use
  `.venv/bin/python`, `./run.sh`, and `QENTIS_RUNS_DIR` for isolated libraries.
- Public science: `qentis/learning.py` runs eight shared initial observations plus
  paired adaptive/random acquisitions. Isolated evaluation labels never enter
  selection. Model/preprocessing artifacts are non-executable JSON.
- Persistence: schema-two immutable run/preparation artifacts and paired revision
  directories; `latest.json` advances atomically. Failure leaves last confirmed
  pair. Models reopen without solver calls or fitting, within 1e−8.
- Existing scientific outcome, seed 0 / 24 labels each: RMSE adaptive
  0.0538601652272759, random 0.0556468597828022. Single-seed evidence only.
- Verification: 87 tests passed, compile check passed. Actual browser run, server
  restart, saved reopening, both themes at 1280×720 and390×844. Finish reviewer
  scored all three final fixes resolved with ship disposition at that scope.
- Preserve the supplied logo, local IBM Plex fonts, theme palettes, native
  controls, scientific source labels, and unclipped estimates. Adaptive trajectory
  is dash-dot, random dashed, numerical reference solid.
- `PRODUCT.md`, `DESIGN.md`, `.impeccable/design.json`, phase plan, README, and
  `docs/phase-two-verification.md` reflect phase two.
- Phase-three work: true pause/resume at complete-pair boundaries, restart
  recovery, continuation equivalence, explicit artifact recovery, working JSON/CSV
  exports, and immutable history. Preserve phase-one and phase-two records.
- No AGENTS.md found. No commit/push requested. The current repository files are
  untracked; avoid deleting unrelated files. The local server may be running on
  port8501; its file watcher is off, so restart after source changes.
- Apply test-write for tests one at a time, real public interfaces and external
  boundary fault injection. Impeccable requires fresh finish reviewer and final
  documenter for UI changes; only those skill-mandated subagents are authorized.
