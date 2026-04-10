# P79 Operator Surface Consolidation Note

## Scope

This note reviews which recent operator surfaces are now redundant versus high-value after the latest bundle refresh, and recommends the next consolidation-safe cleanup or grouping step.

Grounding inputs:

- [runs/real_data_benchmark/full_results/operator_dashboard.json](/D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/operator_dashboard.json)
- [artifacts/status/lightweight_bundle_manifest.json](/D:/documents/ProteoSphereV2/artifacts/status/lightweight_bundle_manifest.json)
- [artifacts/status/live_bundle_manifest_validation.json](/D:/documents/ProteoSphereV2/artifacts/status/live_bundle_manifest_validation.json)
- [artifacts/status/ligand_stage1_operator_queue_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/ligand_stage1_operator_queue_preview.json)
- [artifacts/status/structure_followup_single_accession_validation_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/structure_followup_single_accession_validation_preview.json)

## Current State

The current bundle is still a `debug_bundle` with `compressed_sqlite` packaging and class `A` size. The refresh added two validated bundle-backed preview families:

- `structure_followup_payloads`
- `ligand_support_readiness`

Those are now confirmed in:

- [lightweight_bundle_manifest.json](/D:/documents/ProteoSphereV2/artifacts/status/lightweight_bundle_manifest.json)
- [live_bundle_manifest_validation.json](/D:/documents/ProteoSphereV2/artifacts/status/live_bundle_manifest_validation.json)

At the same time, the operator dashboard now also carries narrower operator-only steering cards:

- `ligand_identity_pilot_preview`
- `ligand_stage1_operator_queue_preview`
- `structure_followup_single_accession_preview`
- `structure_followup_single_accession_validation_preview`

## High-Value Surfaces

### 1. `ligand_stage1_operator_queue_preview`

This is the best operator-facing ligand stage-1 surface now.

Why:

- it exposes ordered rows directly
- it includes operator labels
- it includes blockers and next truthful stages
- it includes the explicit deferred `Q9UCM0` row
- it keeps the right boundaries:
  - `report_only = true`
  - `ligand_rows_materialized = false`
  - `bundle_ligands_included = false`

### 2. `structure_followup_single_accession_validation_preview`

This is the best operator-facing structure follow-up steering surface now.

Why:

- it adds validation state on top of the single-accession preview
- it confirms alignment with anchor validation
- it preserves candidate-only truth
- it keeps `direct_structure_backed_join_certified = false`

### 3. `ligand_support_readiness_preview`

This remains high-value because it is bundle-backed and validated. It is the stable operator truth surface for support-state readiness before any ligand family exists.

### 4. `structure_followup_payload_preview`

This remains high-value because it is bundle-backed and validated. It is the broader truth surface behind the narrower one-accession structure steering view.

## Redundant Or Near-Redundant Surfaces

### 1. `ligand_identity_pilot_preview`

This is now near-redundant relative to [ligand_stage1_operator_queue_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/ligand_stage1_operator_queue_preview.json).

Why:

- both describe the same four-row ligand stage-1 ordering
- the queue preview is more operator-usable
- the dashboard already exposes ordered accessions

This surface is still safe. It is just lower-value as a separate top-level operator card.

### 2. `structure_followup_single_accession_preview`

This is now near-redundant relative to [structure_followup_single_accession_validation_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/structure_followup_single_accession_validation_preview.json).

Why:

- the validation preview preserves the key steering facts
- the validation preview adds the alignment and anchor checks that operators actually need

This surface is also still safe. It is better treated as payload detail behind the validation card.

## Recommended Next Consolidation-Safe Step

Group the operator-only steering and validation surfaces into two grouped cards, while leaving the bundle-backed summary surfaces separate at top level.

### Group 1. Ligand Stage-1 Operator Group

Primary:

- `ligand_stage1_operator_queue_preview`

Demote from top-level emphasis:

- `ligand_identity_pilot_preview`

Result:

- one operator ligand-stage1 card with the ordered queue rows and explicit deferred row

### Group 2. Structure Follow-Up Single-Accession Group

Primary:

- `structure_followup_single_accession_validation_preview`

Demote from top-level emphasis:

- `structure_followup_single_accession_preview`

Result:

- one operator structure follow-up card with validation-first summary and optional payload detail

### Keep Separate At Top Level

Do not merge away these bundle-backed truth surfaces:

- `ligand_support_readiness_preview`
- `structure_followup_payload_preview`

## Truth Boundaries To Preserve

Any consolidation must keep these explicit:

- `ligand_stage1_operator_queue_preview` is not a bundled ligand family
- `structure_followup_single_accession_validation_preview` does not certify a direct structure-backed join
- bundle-backed surfaces must remain distinguishable from operator-only steering cards
- the grouped summaries must keep:
  - `report_only = true`
  - `ligand_rows_materialized = false`
  - `bundle_ligands_included = false`
  - `candidate_only_no_variant_anchor = true`
  - `direct_structure_backed_join_certified = false`

## Bottom Line

The high-value operator surfaces after the refresh are:

- `ligand_support_readiness_preview`
- `structure_followup_payload_preview`
- `ligand_stage1_operator_queue_preview`
- `structure_followup_single_accession_validation_preview`

The lowest-risk consolidation step is to group the operator-only pilot surfaces and demote:

- `ligand_identity_pilot_preview`
- `structure_followup_single_accession_preview`

from top-level emphasis. That reduces overlap without weakening any truth boundary.
