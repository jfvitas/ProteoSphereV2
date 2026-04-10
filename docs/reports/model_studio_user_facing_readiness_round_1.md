# Model Studio User-Facing Readiness Round 1

## Scope

This wave focused on making the Studio meaningfully user-facing for internal
expert testing:

- guided stepper as the primary navigation flow
- explicit response/feedback for visible controls
- registry-backed finite-option selectors
- inactive-option visibility with explanations
- run heartbeat, stage-state, and failure visibility
- hardware discovery surfaced in the UI
- browser-based screenshot and user-simulation evidence

## What Landed

### Guided flow and control behavior

- Added the top-level guided stepper with step-state cards for:
  - Training Set Request
  - Dataset Preview
  - Build & Split
  - Representation & Features
  - Pipeline Design
  - Run & Monitor
  - Analysis & Compare
  - Export & Review
- Added a shared action/status rail for:
  - latest UI action
  - current run stage
  - last heartbeat
  - run status
- Added action eligibility handling so visible primary buttons always give a
  response:
  - real action when enabled
  - warning or inactive explanation when not yet available

### Registry-backed options and help content

- Added shared option registries for controlled finite-value selections.
- Added field-help entries and info-button support for:
  - task type
  - split strategy
  - primary dataset
  - structure source policy
  - graph kind
  - include waters
  - include salt bridges
  - include contact shell
  - model family
  - architecture
  - loss function
  - evaluation preset
  - hardware/runtime preset

### Runtime and status hardening

- Fixed the asynchronous run-launch path so manifest failures no longer leave
  ghost `running` runs behind.
- Added lock-protected manifest reads/writes for live-polled run state.
- Kept the UI monitor alive when the user reopens an existing run.
- Made inactive resume behavior explicit in the release UI.

### Visual and interaction evidence

- Desktop and narrow/mobile screenshot set captured successfully.
- End-to-end guided user simulation completed successfully.

## Review Passes

Role-based review inputs were collected for:

- UX / visual flow
- architecture / contract cleanliness
- QA / control behavior
- scientific / runtime semantics

### Resolved in this round

- resume action now reads as inactive rather than pretending to be a normal
  release action
- run monitoring is restarted when selecting a run from history
- button gating and inactive explanations are more explicit
- mobile layout now shows the guided content before the sidebar
- error handling for JSON vs non-JSON responses is more robust

### Deferred but still real

- backend capability enforcement is still stronger for some fields than others;
  the frontend registry is ahead of the full backend contract
- stepper state is still partially recomputed in the browser rather than being
  purely server-authored
- some scientific labels remain broader than the current implementation
  justifies, especially around structure provenance and hydrogen-bond wording

## Evidence

### Visual review

- [visual_review_manifest.json](/D:/documents/ProteoSphereV2/artifacts/reviews/model_studio_internal_alpha/visual_round_user_facing/visual_review_manifest.json)
- [desktop_full.png](/D:/documents/ProteoSphereV2/artifacts/reviews/model_studio_internal_alpha/visual_round_user_facing/desktop_full.png)
- [mobile_full.png](/D:/documents/ProteoSphereV2/artifacts/reviews/model_studio_internal_alpha/visual_round_user_facing/mobile_full.png)

### User simulation

- [user_sim_trace.json](/D:/documents/ProteoSphereV2/artifacts/reviews/model_studio_internal_alpha/user_sim_round_user_facing/user_sim_trace.json)
- [user_sim_after_launch.png](/D:/documents/ProteoSphereV2/artifacts/reviews/model_studio_internal_alpha/user_sim_round_user_facing/user_sim_after_launch.png)

## Validation

- `python -m pytest ...` -> `8 passed`
- `python -m ruff check ...` -> clean
- browser-based screenshot capture -> passed
- browser-based user simulation -> passed

## Current Readiness

The Studio is now much closer to a real internal testing surface:

- the user can follow a visible end-to-end flow
- the main controls provide feedback instead of silently doing nothing
- inactive planned options are visible in-place through registry-backed controls
- stage and run status are observable while work is happening
- metrics, outliers, and comparisons are visible after completion

It is suitable for continued internal expert testing, with the biggest next
hardening areas being:

1. make the stepper fully server-authored and truly gate later actions
2. tighten scientific wording around provenance and feature semantics
3. expand browser/UI regression coverage around failure states
