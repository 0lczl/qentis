# Qentis

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Python, Streamlit, Plotly, QuTiP, and scikit-learn, as specified in
`.specs/qentis-proof-of-concept/spec.md`. Local application, no hosted service.

## Users

The founder and teammate presenting simulated quantum experiments to a scientist
and potential funder from a laptop during an online meeting.

## Product Purpose

Make a reproducible, numerically computed qubit experiment understandable.
Phases one through three deliver simulation, inspection, durable saved results, and a
single-seed adaptive/random learning comparison with reloadable surrogate models.
Paired-step pause/resume, interruption recovery, and revision-specific JSON/CSV
exports are implemented. The fixed ten-seed benchmark, saved presentation opening, measured short run, and founder walkthrough complete phase four.

## Capabilities and Constraints

English interface; one qubit, fixed |+⟩ state, pure dephasing; genuine numerical
reference. No hardware, accounts, external API, assistant, or fabricated outcomes.
Core operation must work offline after setup and be usable at 1280 × 720 with
keyboard controls. Saved results must survive process restarts.

## Brand Commitments

Preserve the supplied Qentis PNG and follow `docs/design/QENTIS_DESIGN_GUIDE.md`.
The user explicitly requested light and dark modes. Both preserve the incumbent
identity, locally bundled IBM Plex fonts, and scientific color meanings.

## Evidence on Hand

The source specification, phase plan, design guide, original logo, and verified
numerical and learning workflows. The short seed-0 run has 24 acquired labels per
strategy and separately evaluated RMSE; it is single-seed evidence, not a
benchmark or a guarantee of adaptive superiority. Verification records live in
`docs/phase-one-verification.md`, `docs/phase-two-verification.md`, and
`docs/phase-three-verification.md`, and `docs/phase-four-verification.md`.

## Product Principles

- Make physical conventions and data sources visible.
- Validate computation before presenting it as successful.
- Preserve historical configuration and scientific results.
- Report limitations and failures plainly.

These facts are carried from the approved phase/specification, under the user's
instruction to proceed; no new product or aesthetic assumptions are introduced.
