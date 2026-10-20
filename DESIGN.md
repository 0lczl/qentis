---
name: Qentis
description: A quiet, precise instrument for inspecting numerical qubit experiments.
colors:
  background: "#0a0a0a"
  surface: "#121218"
  surface-raised: "#1b1a24"
  border: "#34313f"
  control-border: "#777180"
  text: "#f4f1fa"
  muted: "#b9b2c8"
  accent: "#b89aff"
  reference: "#68d9d1"
  random: "#f0bd69"
  on-primary: "#ffffff"
  light-background: "#f7f6fa"
  light-surface: "#ffffff"
  light-surface-raised: "#eeebf3"
  light-border: "#d5cedf"
  light-control-border: "#80758f"
  light-text: "#20182d"
  light-muted: "#60566e"
  light-accent: "#6735af"
  light-reference: "#087870"
  light-random: "#946009"
  brand-bright: "#6e2eda"
  brand-hover: "#5823bd"
  selection: "#4a1d9f"
typography:
  equation:
    fontFamily: "IBM Plex Sans, sans-serif"
    fontSize: "3rem"
    lineHeight: 1.3
  brand:
    fontFamily: "IBM Plex Sans, sans-serif"
    fontSize: "1.65rem"
    lineHeight: 1.2
    letterSpacing: "-0.025em"
  empty-title:
    fontFamily: "IBM Plex Sans, sans-serif"
    fontSize: "1.5rem"
    fontWeight: 500
  chart-tick:
    fontFamily: "IBM Plex Sans, sans-serif"
    fontSize: "13px"
  headline:
    fontFamily: "IBM Plex Sans, sans-serif"
    fontSize: "1.8rem"
    fontWeight: 500
    letterSpacing: "-0.025em"
  title:
    fontFamily: "IBM Plex Sans, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 500
  section:
    fontFamily: "IBM Plex Sans, sans-serif"
    fontSize: "1rem"
    fontWeight: 500
  body:
    fontFamily: "IBM Plex Sans, sans-serif"
    fontSize: "16px"
    lineHeight: 1.55
  label:
    fontFamily: "IBM Plex Sans, sans-serif"
    fontSize: "14px"
  data:
    fontFamily: "IBM Plex Mono, monospace"
    fontSize: "14px"
    fontWeight: 400
rounded:
  control: "8px"
  pill: "999px"
spacing:
  xs: "0.5rem"
  sm: "0.75rem"
  md: "1rem"
  lg: "1.5rem"
  xl: "2rem"
  page-inline: "2.5rem"
components:
  button-primary:
    backgroundColor: "{colors.brand-bright}"
    textColor: "{colors.on-primary}"
    rounded: "{rounded.control}"
  button-primary-hover:
    backgroundColor: "{colors.brand-hover}"
    textColor: "{colors.on-primary}"
    rounded: "{rounded.control}"
  button-secondary:
    backgroundColor: "{colors.surface-raised}"
    textColor: "{colors.text}"
    rounded: "{rounded.control}"
  input-number:
    backgroundColor: "{colors.surface-raised}"
    textColor: "{colors.text}"
    rounded: "{rounded.control}"
  scope-chip:
    backgroundColor: "{colors.background}"
    textColor: "{colors.accent}"
    typography: "{typography.label}"
    rounded: "{rounded.pill}"
    padding: "0.35rem 0.8rem"
  chart-surface:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    height: "360px"
  reference-chart-surface:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    height: "300px"
  numerical-readout:
    textColor: "{colors.muted}"
    typography: "{typography.label}"
    padding: "0.8rem 0"
  expander:
    textColor: "{colors.text}"
    rounded: "{rounded.control}"
---

# Design System: Qentis

## Overview

**Creative North Star: "The Quiet Research Instrument"**

Qentis gives numerical evidence the visual authority. Near-black and quiet pale-paper canvases, locally bundled IBM Plex type, and restrained violet controls support careful inspection. The supplied ribbon Q remains the identity anchor; its existing halo supplies the brand atmosphere without spreading glow across scientific evidence.

This document records the implemented phases one through four. The original [design guide](docs/design/QENTIS_DESIGN_GUIDE.md) remains the approved visual authority, and [PRODUCT.md](PRODUCT.md) supplies the simulation-only, offline, reproducibility constraints and explicit light/dark requirement. The shipped sources are `assets/dashboard.css`, `app.py`, `qentis/theme.py`, `qentis/charts.py`, `qentis/learning_charts.py`, `qentis/learning_ui.py`, and `qentis/benchmark_ui.py`. This extension preserves the original logo and guide.

The dashboard includes numerical simulation, saved runs, and a single-seed adaptive/random comparison with stored surrogate models and completed-revision inspection. The same protocol, evidence, and scientific source labels apply in both appearances. Whole-pair pause, same-protocol resume, interruption recovery, and revision-specific downloads are implemented. The Benchmark view retains all ten fixed seeds and exposes repeated-seed variability without claiming a general advantage.

**Key Characteristics:**

- Quiet dark and light surfaces with precise boundaries.
- Violet identity, actions, focus, and adaptive/model estimates.
- Teal numerical reference and amber random baseline, reinforced by geometry and words.
- Readable scientific plots, wrapped numerical readouts, and inspectable model revisions.
- Explicit live/saved provenance, actual computation progress, and explicit paused, interrupted, complete, and failure states.

## Colors

Both appearances preserve semantic roles. Unprefixed color tokens describe Dark; `light-` siblings replace the corresponding semantic variables in Light. Brand action violet, hover violet, white action/selection text, and selection violet stay fixed. `qentis/theme.py` switches controls, plot surfaces, hover labels, menus, tables, text, and evidence together; the frontmatter contains both palettes.

### Primary

- **Luminous Violet** (`brand-bright`): primary action fill; its **Deep Violet** hover sibling (`brand-hover`) darkens the fill while the border becomes main text color.
- **Pale Violet** (`accent`): visible focus, selection controls, the simulation scope label, saved-result status, and the selected-time guide. It is pale in Dark and deeper in Light; model estimates use this same semantic accent.
- **Selection Violet** (`selection`): browser text-selection background, with explicit white `on-primary` text in both appearances. Primary button labels also use this fixed white token.

### Secondary

- **Reference Teal** (`reference`): numerical Bloch vector, solid coherence curve, outlined sample marker, and live-computation completion label. It distinguishes numerical evidence from model estimates in both appearances.
- **Baseline Amber** (`random`, `light-random`): random comparison lines and the measured-error map scale. Labels distinguish series identity from an error magnitude.

### Neutral

- **Instrument Black** (`background`): app canvas and logo surround.
- **Plot Charcoal** (`surface`): flat scientific chart surfaces and the sample marker center.
- **Raised Charcoal** (`surface-raised`): fields, menus, and hover labels.
- **Quiet Divider** (`border`): separators, chart grid, and noninteractive outlines.
- **Control Outline** (`control-border`): meaningful field outlines and supporting sphere geometry.
- **Soft White** (`text`): primary text and values.
- **Lavender Gray** (`muted`): supporting copy, captions, scientific axis labels, and the dashed equal-population reference.
- **Pale Paper / White Plot / Raised Paper** (`light-background`, `light-surface`, `light-surface-raised`): Light canvas, evidence, and controls.
- **Light Divider / Light Control Outline** (`light-border`, `light-control-border`): the same quiet/interactive boundary hierarchy on paper.
- **Ink Violet / Muted Ink** (`light-text`, `light-muted`): primary and supporting Light text.
- **Deep Accent / Reference Teal / Baseline Amber** (`light-accent`, `light-reference`, `light-random`): darker counterparts preserving scientific roles in Light.

**The Evidence Color Rule.** Teal means numerical reference, violet means adaptive/model estimate, and amber means the random comparison. State sources in labels; distinguish estimated uncertainty from measured held-out error. A single-seed result is not a benchmark or a general advantage.

**The Restrained Violet Rule.** Keep the canvas and scientific surfaces neutral. Concentrate violet on the original identity, actionable controls, focus, current selection, and labeled adaptive/model evidence.

## Typography

**Display and Body Font:** IBM Plex Sans, with sans-serif fallback. **Label/Mono Font:** IBM Plex Mono, with monospace fallback for code, identifiers, and numerical readout values.

**Character:** Clear scientific interface type, modest headings, sentence case, and tabular numerals. Both regular font files and their license are bundled under `assets/fonts/`; no network font request is needed. Headings request medium weight in CSS, while the bundled faces contain regular weight only, so browsers may synthesize medium.

### Hierarchy

- **Equation:** the phase-one empty-state expression, using `equation`; it is not a general page heading.
- **Brand:** the preserved text lockup, using `brand`.
- **Empty title:** ready-state headings, using `empty-title`.
- **Headline:** page titles, using the `headline` token.
- **Title:** numerical evidence headings, using `title`.
- **Section:** control groups and plot headings, using `section`.
- **Body:** explanatory paragraphs, using `body`; the empty-state explanation is constrained to a readable measure of 68 characters.
- **Label:** captions, status text, units, and chart labels, using `label`. Captions render at full opacity.
- **Data:** readout values, using `data`; precision is explicit and follows the scientific quantity. The interface applies tabular numerals throughout.
- **Chart tick:** phase-two ticks and horizontal legends use `chart-tick`; axis titles, hover text, and shared Plotly base text use the label scale.

**The Readable Evidence Rule.** Supporting scientific copy and numerical readouts use the label/data scale; phase-two ticks and legends use the chart-tick scale. Do not dim captions through a second opacity layer.

## Layout

The implemented dashboard places settings on the left and evidence on the right, with Streamlit column proportions of 1:3.4. The phase-one evidence area pairs the Bloch sphere with a larger quantitative trajectory plot at 0.9:1.25; learning trajectory uses 0.85:1.3. Selection and error maps use equal columns. The learning result keeps protocol and paired RMSE visible above four evidence tabs. The content container has a maximum width of 1512 pixels; its desktop padding uses the spacing tokens: one `md` above, `page-inline` on each side, and `xl` below. Vertical blocks use `sm` gaps.

The header contains the preserved logo/text lockup and a compact simulation-only label. Its original image uses `object-fit: contain` in a 96 × 88 pixel box. The main page title and introduction precede the controls/evidence split. Readouts, protocol summaries, and result headings wrap instead of clipping.

At the implemented 760-pixel breakpoint, horizontal columns stack in source order: settings, evidence, sphere, then trajectory. The container padding becomes `xs` above, `md` on each side, and `lg` below. Columns occupy the full available width, and the logo box becomes 72 × 80 pixels. Mobile evidence continues vertically with the readout and validation details below the plots. At 1280 × 720, lower evidence can sit below the initial viewport; normal vertical scrolling is part of the layout. Learning controls remain before evidence at 390 pixels. Readouts and protocol strips wrap; diagnostic tables have local horizontal overflow rather than forcing page overflow. Completed-revision inspection lives in an expander to preserve first-viewport space.

Spacing follows the guide's compact four-pixel foundation through the observed scale. Use borders and breathing room to separate evidence from settings; avoid multiplying identical metric cards.

## Elevation & Depth

The dashboard is flat. Tonal surfaces, quiet dividers, and visible control outlines establish hierarchy; the custom implementation adds no box shadows or translucent panels. The supplied logo retains its original embedded halo. Sphere wireframes provide spatial reference, with lower opacity than the teal state vector, without becoming decorative animation.

**The Flat Evidence Rule.** Keep charts, readouts, and containers sharp and still. Do not add glow, shadow, or translucency to numerical evidence.

## Shapes

Controls and expanders have gently curved corners through `rounded.control`. Plot surfaces remain rectangular, and the concise simulation scope badge uses `rounded.pill`. Dividers are thin single-pixel lines. Fields use the stronger control outline; the quieter divider is insufficient as their sole boundary.

Preserve the full supplied Q shape, tail, color transitions, and proportions. The original PNG includes its background and internal margins; never stretch, recolor, remove its background, or reconstruct it as part of interface work. Adjacent Qentis text supplies the accessible name, so the implemented logo image has empty alt text.

## Components

### Buttons

Direct and restrained. The full-width **Run simulation** and **Run experiment** actions use the primary variant, explicit white labels in both appearances, a one-pixel pale-violet border, and a minimum height of 42 pixels. Hover uses `button-primary-hover` and a main-text border. The saved-run opening action uses the same primary treatment. Secondary buttons retain a visible control outline. **Pause after this step** requests a stop after both strategies are committed. **Resume experiment** continues the saved run; **Restart as new run** is reserved for records without a complete checkpoint. Conflicting starts are disabled while the background worker owns the library. Global keyboard focus is a two-pixel pale-violet outline offset by three pixels; the slider offset is five pixels. Do not substitute a glow for this outline.

### Inputs / Fields

Visible and explicit. Number inputs, strategy selection, and saved-run selection use the active raised surface, main text, control outlines, and control corners. Select chevrons inherit theme text through `currentColor`. Radios, checkboxes, sliders, menu options, tooltip text, JSON, and tables follow the same active palette. The native JSON viewer, including its nested viewer background, uses the raised surface and main text in both appearances. Labels retain quantity names and units. Help explains scientific meaning. Sampling options live in an expander; the form batches settings until the user runs the simulation. The caret uses pale violet. Validation and repository failures use the working Streamlit error component with explicit text; no custom danger token is defined in the stylesheet.

### Navigation

Compact horizontal radio navigation switches between **Experiment**, **Saved runs**, and **Benchmark**. Selection uses the theme's pale violet and remains recognizable by its radio mark and text. Preserve the native keyboard and accessible selection behavior. The Experiment view adds horizontal **Learning comparison** / **Qubit simulation** choices; an adjacent **Dark mode** toggle switches the appearance. Learning evidence uses **Learning curves**, **Selection and error**, **Qubit trajectory**, and **Record and diagnostics** tabs. Selected tabs use the semantic accent. Preserve native keyboard controls and selected-state semantics.

### Chips

The **Simulation only** badge is a noninteractive scope label. Use a quiet outline, pale-violet label text, and the pill primitive. Do not turn it into an unexplained status dot.

### Cards / Containers

The implementation avoids a repeated card grid. Scientific surfaces use `chart-surface`, while the readout, fixed initial state, header, and protocol strip use separators. Expanders use quiet borders and the control corner shape. Preserve open space around evidence instead of adding unsupported panel chrome.

### Scientific evidence

The phase-one Plotly views and the reused Bloch sphere remain 300 pixels high. Learning curves, learning trajectory, uncertainty, and measured-error plots are 360 pixels high, with explicit axis margins and horizontal legends below the plot. Both phase-one views inspect the same stored sample. The sphere uses fixed coordinate ranges, cube aspect, an enlarged camera eye at `(0.85, 0.95, 0.5)`, labeled axes, and a substantial teal state vector. The trajectory is the quantitative source: solid teal coherence, dashed muted equal populations, a dotted violet selected-time line, and a teal-outlined sample marker. Legends, units, hover values, and the textual readout supply encodings beyond color. Keep the trajectory's axes and visible scientific conventions explicit.

The readout wraps compactly and reports time, Bloch components, populations, and purity in monospaced values. Validation captions and the saved-record expander expose the numerical checks and provenance. Time inspection reads stored numerical states and does not launch another solve.

Learning curves show the complete recorded history: adaptive is a solid violet line with circle markers; random is dashed amber with diamond markers. Learning trajectory uses dash-dot violet adaptive estimates, dashed amber random estimates, and a solid teal numerical reference. Shaded bands show estimated mean ± 1.96σ at low opacity; they are neither calibrated confidence nor guaranteed physical bounds. Predictions and bands remain unclipped, and the text reports excursions beyond [−1, 1]. A dotted muted guide marks selected time.

The adaptive uncertainty heatmap uses a fixed 0–1 scale from surface to violet; acquired candidates are open circles and next/last acquisition is a teal cross with explicit text. The measured absolute-error map uses separate 400-point held-out evaluation coordinates and a fixed 0–1 surface-to-amber scale. Overflow counts and tooltips retain values above the display scale. Error maps never drive acquisition.

Model revision selection reads completed paired checkpoints without fitting or acquisition. Trajectory sliders predict using stored models and preprocessing against separately saved numerical visualization slices, without solver calls. The sphere remains a numerical state: the model estimates one observable, not a full quantum state. Diagnostics show metrics, coverage, interval width, counts, observations, fitted kernel, warnings, configuration, and provenance. Keep label-budget counts separate from solver/cache work and elapsed time.

### Evidence downloads

The **Download evidence** expander follows the scientific tabs. Its caption names the selected completed revision and label budget. Three native buttons export **Configuration JSON**, **Observations CSV**, and **Metrics CSV**; filenames include the run ID and revision. Observations belong to that revision, while metrics include history through it. Downloads perform no fitting or acquisition. Buttons stack on narrow screens. Historical settings and committed evidence remain immutable; editing the new-run form creates another run rather than changing the record on display.

### Result and empty states

Phase-one **Live computation · complete** uses teal; phase-one **Saved result** uses accent. The learning result currently uses teal for both live and saved headings, with text naming the source and actual stored status. Text carries the distinction alongside original configuration and creation time. Running states show actual validation and paired-step stages/counts; failures state what did not complete and retain the latest complete paired checkpoint when one exists. An active background worker publishes real preparation and paired-step progress; polling redraws do not repeat computation. A requested pause remains pending until the complete pair is saved. Paused records remain Paused after relaunch; unfinished active records reopen as Interrupted. Resume preserves the run ID, original protocol, observations, models, and random state. Before the first checkpoint, Restart as new run preserves the earlier intent under its old ID. Missing or incompatible artifacts show specific restoration guidance and intact configuration/date where available, with stale charts removed. Budget completion explicitly says no further point is scheduled. The initial state explains compute/check/keep and shows no fabricated result. Saved-runs emptiness directs the user to create a real result. Preserve these labels when extending the workflow.

There are no custom transition tokens in the current implementation. Reduced-motion preference disables animation, transitions, and smooth scrolling. The original guide's suggested transition timing remains guidance for future additions, not an implemented motion scale.


### Prepared presentation and benchmark

The learning opening places a dated **Saved presentation result** and **Open saved run**
above the existing short live form. Saved and live sources remain explicitly named;
there is no replay animation. The measured computation time names its scope.
Benchmark leads with the predeclared protocol, complete/failed/unfinished counts,
and wins/ties/losses. Violet solid-circle and amber dashed-diamond mean curves
retain the existing chart grammar. Shaded mean ±1 population SD bands are labeled
across-seed variability before and after the chart, never confidence intervals.
An HTML table uses the current theme and lists every seed with final RMSE and
failure text. Its container scrolls horizontally on narrow screens; the page does
not. The protocol expander contains JSON/CSV exports and provenance. A seed
selector includes every outcome and opens read-only scientific evidence without
retrying or replacing a benchmark outcome. Empty libraries show setup guidance.

## Do's and Don'ts

### Do:

- **Do** preserve the original ribbon Q and its matching near-black surround.
- **Do** use teal reference, violet adaptive/model, and amber random semantics in both appearances, with dash/marker and text support.
- **Do** keep units, scientific conventions, readout precision, and validation visible.
- **Do** retain clear live/saved labels and the original run's configuration and provenance.
- **Do** stack controls above scientific evidence on narrow screens and allow readouts to wrap.
- **Do** keep captions fully opaque, keyboard focus visibly outlined, and primary/selection text explicitly white in both appearances.
- **Do** preserve negative or inconclusive single-seed results, estimated-interval caveats, and separate acquisition/evaluation sources.

### Don't:

- **Don't** claim that single-seed learning or the ten-seed benchmark establishes a general adaptive advantage, statistical significance, or quantum advantage.
- **Don't** add decorative orbit graphics, pulsing charts, neon panels, or glow to scientific evidence.
- **Don't** replace the numerical trajectory with a decorative sphere or encode series by color alone.
- **Don't** invent unimplemented actions, outcomes, progress percentages, or hardware claims.
- **Don't** replace the approved logo, palette, or type direction as an incidental interface refinement.
