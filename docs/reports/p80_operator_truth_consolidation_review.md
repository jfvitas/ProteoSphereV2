# P80 Operator Truth Consolidation Review

## Scope

This note reviews whether the new consolidated operator action surface remains truthful and whether older operator summaries are now redundant.

Grounding inputs:

- [artifacts/status/operator_next_actions_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/operator_next_actions_preview.json)
- [runs/real_data_benchmark/full_results/operator_dashboard.json](/D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/operator_dashboard.json)
- [artifacts/status/p78_operator_preview_truth_post_refresh.json](/D:/documents/ProteoSphereV2/artifacts/status/p78_operator_preview_truth_post_refresh.json)
- [artifacts/status/live_bundle_manifest_validation.json](/D:/documents/ProteoSphereV2/artifacts/status/live_bundle_manifest_validation.json)

## Current Consolidated Action Surface

The dashboard projection of `operator_next_actions_preview` currently exposes:

- `row_count = 4`
- `lanes = [ligand, structure, split, duplicate_cleanup]`
- `first_ligand_accession = P00387`
- `structure_accession = P31749`
- `split_status = blocked_report_emitted`
- `duplicate_cleanup_status = not_yet_executable_today`
- `report_only = true`
- `ready_for_operator_preview = true`

The underlying source artifact is a prioritized four-row action list with explicit `next_truthful_stage` values and `blocked_for_release = true` on every row.

## Truth Review

This consolidated surface is still truthful.

Why:

- it remains explicitly `report_only`
- it does not claim any new bundle family
- it does not claim bundle validation for itself
- it summarizes next truthful stages instead of implying completed promotion
- it stays aligned with the already-reviewed ligand and structure operator truth boundaries from [p78_operator_preview_truth_post_refresh.json](/D:/documents/ProteoSphereV2/artifacts/status/p78_operator_preview_truth_post_refresh.json)

The explicit truth boundary is still sound:

- it does not certify structure joins
- it does not materialize ligand rows
- it does not unlock fold export
- it does not authorize duplicate cleanup mutation

## Important Limit

This is an operator triage card, not a bundle-backed validation surface.

That distinction matters because [live_bundle_manifest_validation.json](/D:/documents/ProteoSphereV2/artifacts/status/live_bundle_manifest_validation.json) validates bundle-backed preview slices such as:

- `structure_followup_payload`
- `ligand_support_readiness`

But it does not validate `operator_next_actions_preview` itself.

## Low-Risk Summarization Risks

### S1. `first_ligand_accession` Compresses Queue Detail

Low risk. The dashboard only exposes the first ligand accession, while the underlying queue preview is four rows deep. That is safe, but it can hide that the card is summarizing an ordered lane rather than representing the full ligand queue.

### S2. `structure_accession` Compresses Candidate-Only Context

Low risk. The consolidated card names `P31749`, but it does not repeat the deeper structure detail that it remains candidate-only and not certified.

### S3. Bundle-Validation Adjacency Can Be Overread

Low risk. Because the dashboard also exposes live bundle validation, a reader could wrongly assume `operator_next_actions_preview` is bundle-validated too. It is not.

## Older Operator Summaries Now Redundant At Top Level

### Top-Level Redundant

- `ligand_identity_pilot_preview`
  - now superseded at top level by `operator_next_actions_preview` plus the richer ligand queue detail surface
- `structure_followup_single_accession_preview`
  - now superseded at top level by `operator_next_actions_preview` plus the stronger validation-first structure detail surface

### Keep As Detail Surfaces

- `ligand_stage1_operator_queue_preview`
  - still needed as the backing detail surface for the ligand lane
- `structure_followup_single_accession_validation_preview`
  - still needed as the backing detail surface for the structure lane

## Recommended Next Consolidation Step

Promote `operator_next_actions_preview` as the primary top-level operator action card.

Keep top-level:

- `operator_next_actions_preview`
- `ligand_support_readiness_preview`
- `structure_followup_payload_preview`
- live bundle manifest validation summary

Demote to drill-down detail:

- `ligand_identity_pilot_preview`
- `structure_followup_single_accession_preview`
- `ligand_stage1_operator_queue_preview`
- `structure_followup_single_accession_validation_preview`

## Safety Rule

Any consolidation should preserve these rules:

- do not delete the detail artifacts
- keep `report_only` visible on the consolidated action card
- keep candidate-only and non-materialized boundaries visible on the detail cards
- do not imply that the consolidated next-actions card is bundle-validated

## Bottom Line

The consolidated `operator_next_actions_preview` surface remains truthful. It is a good top-level operator triage surface. The main remaining issue is only low-risk summarization drift: it compresses lane detail, so several older operator previews are now redundant at top-level but should remain as drill-down detail surfaces.
