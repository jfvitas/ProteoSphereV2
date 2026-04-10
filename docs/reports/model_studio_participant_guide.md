# Model Studio Participant Guide

## What This Beta Is

Model Studio is currently a controlled external beta for structure-backed protein-protein studies plus one narrow protein-ligand pilot. The safest path is the guided flow.

## Recommended Path

1. Start at `Training Set Request`.
2. Pick a launchable dataset pool.
3. Preview the candidate dataset and inspect the diagnostics.
4. Build the study dataset and confirm the split.
5. Configure the representation and model.
6. Launch the run.
7. Review metrics, analysis, compare, and export outputs.

## Launchable Lanes In This Beta

- PPI benchmark and governed-subset pools remain the primary beta lane.
- `governed_pl_bridge_pilot_subset_v1` is the launchable protein-ligand pilot for structure-backed `delta_G` studies.
- The ligand pilot currently supports only `graphsage` and `multimodal_fusion`.

## What The States Mean

- `Launchable now`: safe to use in the current beta lane.
- `Review pending`: visible for audit or planning, but not safe for routine study launches.
- `Inactive`: out of scope or not ready in the current beta.

## Reporting An Issue

Use `Need help / report issue` when:

- the status language feels contradictory
- a control appears blocked without a clear reason
- the analysis or compare output feels misleading
- a run result seems inconsistent with the selected settings

Helpful report details:

- selected dataset
- selected model family
- current step in the flow
- screenshot or export artifact if available

## Current Beta Truth Notes

- The atom-native lane is a real beta lane, but it still has current limits and should be treated as a beta surface.
- The sequence-embedding lane is a Studio-local deterministic materialization path and should not be interpreted as a broader standalone embedding backend.
- The protein-ligand pilot is intentionally narrow and should not be treated as a general ligand platform.
