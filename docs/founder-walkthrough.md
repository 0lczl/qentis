# Qentis founder walkthrough · 3–5 minutes

## Before the meeting

From this project folder, run `./setup.sh` once (requires internet), then `./run.sh`.
Open http://127.0.0.1:8501. Stop with Ctrl+C and relaunch with `./run.sh`.
The local server must remain running. No terminal commands are needed during the demonstration.

The prepared evidence already exists in `runs/`. Back up this **whole folder** together with this project and its pinned environment. If preparing on another laptop, run
`.venv/bin/python -m qentis.benchmark --root runs` before the meeting. This measures
the default short run first, then computes the fixed benchmark. Repeating the
command preserves terminal seed outcomes and resumes interrupted preparation;
it never substitutes a more favorable seed. A failed seed stays failed. Do not
delete evidence or tune the policy based on this benchmark.

After setup, disconnect external networking, relaunch, and check the saved opening,
a short live run, and downloads. Browser verification here blocked external HTTPS;
a separate automated check denied external Python connections. Physically switching
off the laptop's Wi-Fi was not automated. Use either theme for the room and share
at 1280 × 720 or larger. Charts and lower controls use normal vertical scrolling.

## The meeting

**0:00–0:40 · Start with evidence.** On Experiment, choose **Open saved run**.
Say: “Qentis learns from simulated qubit behavior and chooses where to simulate
next. This is a real saved result, dated and labeled; no computation is being
replayed.” Point out the seed, acquired-label budget, and numerical reference.

**0:40–1:30 · Explain the loop.** Choose **Selection and error**. One model selects
the unqueried point with the highest estimated uncertainty; the baseline chooses
uniformly at random. Both start from the same eight observations and use the same
model. The error map uses separate held-out numerical labels and never guides
selection. Uncertainty is a model estimate, not measured error or a guarantee.

**1:30–2:10 · Show the physics.** Choose **Qubit trajectory** and move the time
slider. The numerical Bloch vector shrinks along x; populations remain one half.
The learned output is coherence x, not a reconstructed quantum state. Open
**Physical assumptions and solver convention** if asked. The response is simply
exp(−γt); that formula validates the numerical solver and never supplies training
labels. This intentionally simple problem demonstrates a workflow, not new physics.

**2:10–3:00 · Show repeated outcomes.** Choose **Benchmark**. All seeds 0–9 appear,
with 32 labels each (8 initial +24 acquisitions). Here adaptive wins 8, ties 0,
and loses 2 at the declared 1e−8 RMSE tolerance. Seeds 6 and 7 favor random.
Mean final adaptive-minus-random RMSE is −0.013826. The shaded bands are across-seed
standard-deviation variability, not confidence intervals or statistical significance.
Choose seed 6 and **Open seed evidence** to demonstrate an unfavorable outcome.
Download benchmark JSON/CSV from its protocol expander if requested.

**3:00–4:00 · Run live.** Return to **Experiment**, keep the short defaults and seed
0, then choose **Run experiment**. The engine now computes and saves a new run,
with actual stages and a Live computation label. The short protocol ends at
24 labels each, whereas the benchmark ends at 32. Pause after this step is
available if useful; this laptop's short run is usually too fast to narrate every
stage. Use the completed revision selector to explain a point rather than adding
artificial delays. Saved evidence is the fallback if the live run fails.

**4:00–4:30 · Close honestly.** Expand **Download evidence** and export the selected
revision. Say: “This is a reproducible simulation workflow proof of concept.
It does not establish quantum advantage, hardware performance, calibrated
uncertainty, or a general adaptive advantage. The two-coordinate response depends
on γt, so scientific novelty is deliberately limited.”

## Recovery

If the app stops, relaunch and use Saved runs. A paused or interrupted learning
run offers resume from its last complete paired checkpoint; before the first
checkpoint it offers a new restart. A missing/corrupt artifact needs its original
backup, not silent retraining. Benchmark seed inspection is read-only and retains
terminal failures. Keep the saved opening ready if a live computation fails.
