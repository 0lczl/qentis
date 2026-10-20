# Phase four verification · 18 October 2026

The local proof of concept now includes the fixed benchmark, prepared opening,
short live path, timing evidence, and founder walkthrough. No scientific policy
was tuned for benchmark outcomes. This is simulation evidence for a workflow,
not quantum advantage, a new discovery, or guaranteed adaptive superiority.

## Fixed evidence

`runs/benchmark.json` declares seeds 0–9, the unchanged Matérn-5/2 fit policy,
solver settings, 21 × 21 candidates, domain [0,2] × [0,5], 8 initial +24 additional
labels per strategy, and tie tolerance 1e−8. All ten completed. There were no
failed or replaced seeds and no protocol adjustments. Every seed stores its
immutable intent, all 25 paired checkpoints, preprocessing/models, numerical
reference, selection sequence, counters, metrics, and provenance. Their shared
400-point numerical evaluation identity is
`ab3a0461d37d1b5e249149e502e65f9c75b80739342e84894bebe7acf0ece6aa`.

| Seed | Adaptive final RMSE | Random final RMSE | Adaptive − random |
| --- | ---: | ---: | ---: |
| 0 | 0.024999 | 0.045556 | −0.020557 |
| 1 | 0.030174 | 0.035638 | −0.005464 |
| 2 | 0.022083 | 0.057421 | −0.035338 |
| 3 | 0.018778 | 0.056877 | −0.038098 |
| 4 | 0.022037 | 0.023639 | −0.001602 |
| 5 | 0.021024 | 0.029462 | −0.008437 |
| 6 | 0.026832 | 0.016565 | +0.010267 |
| 7 | 0.023095 | 0.019178 | +0.003917 |
| 8 | 0.015290 | 0.047276 | −0.031985 |
| 9 | 0.027709 | 0.038676 | −0.010967 |

Wins/ties/losses for adaptive: **8 / 0 / 2**. Mean final difference:
**−0.013826477649086863**. No significance claim. Bands use population standard
deviation (ddof=0) over complete seeds, explicitly variability rather than
confidence. Failed and unfinished counts remain visible and are excluded from
means with an explicit denominator. None occurred in the final benchmark; tests
exercise those cases. [Full metrics CSV](phase-four-benchmark-metrics.csv) and
[summary JSON](phase-four-benchmark-summary.json) accompany this record.

## Prepared opening and laptop timing

The fixed saved opening is `qentis-2cc5271d545042ceb1c8d09b25918ade`, created
2026-10-18T19:48:46.001682+00:00, seed 0, short 24-label protocol. Both analytical
and physical solver validation passed before data preparation. It is a distinct
computed run, chosen in advance by seed 0 rather than by a favorable score.
`runs/presentation.json` records **0.599 seconds** from launch through the final
durable checkpoint, including numerical preparation, fitting, and writes;
rendering is excluded. The browser action through the visible complete state
measured **1.282 seconds**, including automation overhead; its new live run is
`qentis-3f7bf15159e845d9a7419dbf2151516e`. Both meet the 60-second target.

[Browser timing and hardware](phase-four-browser-timing.json): MacBook Air,
Mac15,12, Apple M3, 8 logical cores, 16 GB RAM, macOS 27.0.1 arm64,
Python 3.11.16. Device identifiers are not retained. Measurements are observed
single runs under the current laptop workload, not controlled performance claims.
Source digests in individual runs identify their exact code at creation. Subsequent
changes hardened summary validation and display; they did not change physics,
acquisition, fit policy, candidates, budgets, or evaluation.

## Verification

Phase-four tests use public preparation, aggregation, repository, export, and
Streamlit interfaces. Scientific work runs for real; only external optimizer,
filesystem replacement, and network boundaries receive fault injection.
Checks cover fixed seeds and equal budgets, shared evaluation, precise mean/SD
and tie examples, losing and failed outcomes, immutable repeated preparation,
interrupted summary writes recovering an already-complete seed without new IDs,
JSON/CSV evidence, original-checkpoint/summary consistency, saved opening,
seed-6 inspection in both themes, empty libraries, corrupt/unknown artifacts,
and live prediction/export with external Python connections denied.

The browser rehearsal reopened the app, opened the saved result, ran the short
preset live, downloaded JSON and both CSV files, and inspected the benchmark.
Configuration, observation and metric values matched the selected durable
revision exactly (CSV column order can differ between live and sorted JSON reload).
Both browser benchmark downloads also matched the persisted benchmark JSON and metrics CSV. Seed 6 was opened in the browser and displayed Random lower at this budget. External HTTPS requests were aborted during this rehearsal. The captured HTTP request log contained 201 requests and only the loopback origin `127.0.0.1:8501`. Fonts and logo are
embedded locally; plotting, prediction, computation, and downloads needed no
external request. Physical Wi-Fi disconnection was not automated; the walkthrough
includes that final presenter check. Existing recovery/restart tests remain in
the full regression suite.

Batched rendered inspection covers dark/light at 1280 × 720 and 390 × 844,
plus lower evidence/table captures under `.impeccable/review/phase-four/`.
Document and main widths were both 390 at mobile size; normal vertical scrolling
and an internal table scroll are intentional. The first pass found a dark canvas
table in light mode; the confirmation uses a themed HTML table. Logo, palettes,
local typography, keyboard semantics, reference/estimate labels, and distinct
line/marker styles remain intact. No decorative replay or artificial delays.

Final regression: **121 tests pass in 38.65 seconds**. Compilation passes and pip reports no broken requirements. The one mechanical detector invocation on the three changed UI sources returned an empty finding list. The independent finish reviewer returned **disposition: ship**, with all ten required captures valid and no material fixes. The separate documenter verified the extension, updated the source inventory and three-choice navigation preview, and kept all design tokens unchanged. Valid JSON and exact Overview narrative parity were checked after the handoff.

## Rehearsal and limitations

[Founder walkthrough](founder-walkthrough.md) supplies setup/relaunch, a timed
3–5 minute script, saved evidence, unfavorable seed inspection, live run,
downloads, and recovery. The app was exercised through that route without terminal
commands during the browser demonstration. Presenter delivery time was not measured
as a human speaking rehearsal. Preserve the whole local `runs/` folder and pinned
environment: the Git-ignored results are not replaced by the compact documentation
exports. The response depends on γt, one observable is learned, intervals are
uncalibrated estimates, and hardware experiments are out of scope.
