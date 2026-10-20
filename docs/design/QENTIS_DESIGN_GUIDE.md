# Qentis prototype design guide

Status: initial direction based on the founder's supplied logo, October 17, 2026. This guide prepares the first prototype; it does not imply the application has been built.

## Purpose and scope

Create a credible, visually memorable scientific proof of concept that the founder can present from a laptop over screen sharing. The interface is in English. The first version demonstrates one simulated qubit under dephasing noise, model training, adaptive selection of simulation points, and measured comparison with random selection. Include saved results and a short live experiment. Keep the assistant and broader research workspace for a later version.

## Visual direction

**A quiet, precise research instrument with a luminous violet identity.** Use near-black backgrounds, restrained violet accents, legible scientific plots, and generous separation between controls and evidence. The ribbon-shaped Q is the identity anchor. Its dimensional curve can inspire the Bloch-sphere treatment and selection highlights, without adding decorative orbit graphics to every panel.

The main impression should be scientific clarity. Concentrate the logo's glow around the brand or a single focal visualization; keep charts, labels, and controls sharp. Avoid neon overload, translucent panels over busy backgrounds, giant marketing headlines, and endless grids of identical metric cards.

## Logo asset

Original reference: `../../assets/brand/qentis-logo-reference.png` (relative to this guide).

The supplied image is a 952 × 944 PNG containing a violet ribbon Q, a diffuse purple halo, and a near-black background. It is a raster reference, with its background included; it is not a transparent icon or a vector master.

- Preserve the complete Q shape, proportions, color transitions, and tail.
- Display the source image with `object-fit: contain`; never stretch it.
- Give the image a matching near-black surround. Do not apply automatic white-background removal, recolor it, or reconstruct the mark without review.
- For the first prototype, pair a readable “Qentis” text label with the image in a restrained header or presentation introduction. The full image has generous internal margins, so inspect its actual visible size before using it in compact navigation.
- Do not use this full image as a tiny favicon: the mark will become indistinct. A compact variant can be prepared later from an approved source.
- Keep clear space around the visible mark of roughly one quarter of its visible height. This is a proposed usage rule, not a supplied brand standard.
- Use alt text “Qentis” if the image is the sole brand label; use empty alt text when adjacent text already names Qentis.

## Palette

Colors sampled from a compressed, glowing raster are approximate. The five violets below are quantized representative colors from purple pixels; they are not an official brand specification. Supporting UI colors are proposed additions for readability.

| Token | Hex | Origin and role |
| --- | --- | --- |
| `--background` | `#0A0A0A` | Dominant sampled background; app canvas and logo surround |
| `--brand-deep` | `#2E1170` | Sampled violet shadow; decorative depth only |
| `--brand-shadow` | `#3C178A` | Sampled violet; subdued brand gradient |
| `--brand-mid` | `#4A1D9F` | Sampled violet; brand gradient |
| `--brand-violet` | `#5823BD` | Sampled violet; brand graphics |
| `--brand-bright` | `#6E2EDA` | Sampled bright violet; primary button fill |
| `--surface` | `#121218` | Proposed panel surface |
| `--surface-raised` | `#1B1A24` | Proposed elevated controls and menus |
| `--border` | `#34313F` | Proposed decorative separators; not sole control outline |
| `--control-border` | `#777180` | Proposed visible control outline |
| `--text` | `#F4F1FA` | Proposed main text |
| `--text-muted` | `#B9B2C8` | Proposed secondary text and chart labels |
| `--accent` | `#B89AFF` | Proposed light violet; selected text and focus rings |
| `--reference` | `#68D9D1` | Proposed teal; numerical reference curve |
| `--baseline` | `#F0BF69` | Proposed amber; random-selection baseline |
| `--danger` | `#FF909F` | Proposed failures and validation errors |

Use near-black and neutral surfaces for most of the screen. Violet identifies Qentis and adaptive/model behavior. Teal and amber distinguish scientific series; they are functional additions, not changes to the logo.

Use `--text` on `--brand-bright` for primary buttons. Use `--accent`, rather than dark sampled violets, for small colored text on dark surfaces. Verify final combinations: WCAG AA targets are 4.5:1 for normal text and 3:1 for large text and meaningful UI graphics. Evaluate hover, disabled, focus, and chart states in the rendered implementation too.

## Typography and spacing

- Proposed type: locally bundled **IBM Plex Sans** for interface copy and **IBM Plex Mono** for numerical values, parameter settings, and run identifiers. These are implementation recommendations, not fonts extracted from the logo. Include font licenses when bundling.
- Use 16 px for normal text, 14 px for supporting labels, and 24–32 px for page titles. Avoid presentation-critical text below 14 px.
- Use tabular numbers for changing values; show units and precision consistently.
- Use a 4 px spacing foundation: 8, 12, 16, 24, and 32 px. Prefer 24 px panel padding and 16–24 px gaps.
- Use approximately 10 px panel radii, 8 px input/button radii, and subtle borders. Reserve pills for concise statuses.

## First prototype screen

Target a clean laptop layout at 1440 × 900, usable at 1280 × 720 and during screen sharing. At narrower sizes, stack the controls above the scientific output. Do not require a wide sidebar for this single-workflow prototype.

1. **Header:** Qentis, “Adaptive Quantum Discovery,” and a visible “Simulation only” label.
2. **Experiment controls:** initial state, dephasing settings, simulation budget, and seed, with scientifically reviewed defaults. Show advanced parameters in an expandable section.
3. **Main scientific view:** a Bloch-sphere view paired with a time-series plot. The plot remains the quantitative source when the sphere is hard to read.
4. **Learning evidence:** a parameter-space uncertainty map and an error-versus-simulation-count chart comparing adaptive and random selection under equal budgets.
5. **Run summary:** configuration, completed simulations, model version, validation error, and elapsed time. Distinguish reference-simulation time, training time, and prediction time if reporting speed.
6. **Saved results:** a clear way to open a prepared run and save the current run with its configuration. Display the run's provenance and completion state.

Suggested primary actions: **Run experiment**, **Pause after this step**, **Open saved run**, and **Save results**. Only expose actions that actually work. Do not add inactive assistant, training-platform, or report-generator controls to imply broader functionality.

## Scientific visualization rules

| Meaning | Color and additional encoding |
| --- | --- |
| Numerical reference | Teal, solid line |
| Model prediction | Light violet, dashed line |
| Adaptive selection performance | Light violet, solid line with circles |
| Random selection performance | Amber, dashed line with squares |
| Model uncertainty | Violet shaded band with a legend identifying interval type and coverage |
| Selected next point | Light marker with visible outline and a text label |

- Label axes, units, legends, and the displayed metric explicitly. Provide hover values and a readable textual summary.
- Dephasing can reduce coherence without changing computational-basis populations. Ensure the chosen quantitative view shows the relevant behavior; have the scientific implementation define the precise convention and equations.
- Uncertainty and prediction error are different quantities. Give them separate panels and legends; label uncertainty as an estimate.
- Acquisition must use information available at selection time. A dashboard may display held-out reference errors for evaluation, but must not silently use those errors to choose new simulations.
- Use a sequential, perceptually ordered heatmap for nonnegative uncertainty, with low/high labels and a numerical color scale. Do not use a decorative rainbow or suggest that violet brightness is an exact physical quantity without a legend.
- Keep map limits and comparison axes fixed across iterations so visual changes are meaningful. Explain any normalization.
- Compare strategies with the same budget and evaluation protocol. Clearly label single-run results; show variability when repeated seeded runs are available. A favorable result is not guaranteed.
- Never replace scientific output with decorative animation. Always label saved/replayed runs and live runs distinctly.

## States, motion, and presentation

- Explain the loop with plain statuses: **Generating reference data → Training model → Choosing next simulation → Updating comparison → Complete**.
- Show completed steps, elapsed time, and recoverable errors. Do not fabricate progress percentages or an accuracy increase.
- A paused run should state which completed step was saved. Preserve completed results after failures where the implementation supports it.
- Use 150–200 ms interface transitions, with no pulsing charts or constant glow animation. Respect reduced-motion preferences.
- Keep the presentation path simple: open a saved run, explain the two strategies, inspect the result, then start a short live run.
- Avoid unsupported claims such as “quantum advantage,” “validated on hardware,” or “AI always wins.” Describe the current scope as a simulation-based proof of concept.

## Build acceptance checklist

- [ ] Original logo is preserved and displayed without distortion.
- [ ] Brand colors match this reference direction; plots remain easy to read when screen-shared.
- [ ] Core labels and numerical output remain legible at 1280 × 720.
- [ ] Keyboard controls, visible focus, contrast, and reduced motion have been checked.
- [ ] All series can be distinguished without color alone.
- [ ] Live and saved results are clearly labeled.
- [ ] Model estimates, numerical reference, and uncertainty are explicitly distinguished.
- [ ] Adaptive and random strategies use a fair, documented comparison.
- [ ] Saved runs retain enough configuration and provenance to reproduce the result.
- [ ] The founder can complete the walkthrough without terminal commands during the meeting.
