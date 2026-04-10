# P79 Bundle Iteration Four Candidate Order

This is a report-only reassessment of the safest bundle-iteration-four candidate order after the refreshed bundle and operator queue surfaces, grounded in [lightweight_bundle_manifest.json](D:/documents/ProteoSphereV2/artifacts/status/lightweight_bundle_manifest.json), [live_bundle_manifest_validation.json](D:/documents/ProteoSphereV2/artifacts/status/live_bundle_manifest_validation.json), [p78_bundle_iteration_three_post_refresh_order.json](D:/documents/ProteoSphereV2/artifacts/status/p78_bundle_iteration_three_post_refresh_order.json), [ligand_stage1_operator_queue_preview.json](D:/documents/ProteoSphereV2/artifacts/status/ligand_stage1_operator_queue_preview.json), and [structure_followup_single_accession_validation_preview.json](D:/documents/ProteoSphereV2/artifacts/status/structure_followup_single_accession_validation_preview.json).

## Current Truth

The bundle remains a verified preview:

- `bundle_kind = debug_bundle`
- `packaging_layout = compressed_sqlite`
- `bundle_budget_class = A`
- `bundle_compressed_size_bytes = 266321`
- `validation_status = aligned_current_preview_with_verified_assets`
- `operator_go_no_go = no-go`
- `release_grade_status = blocked_on_release_grade_bar`

The refresh already materialized:

- `structure_similarity_signatures`
- `structure_followup_payloads`
- `ligand_support_readiness`

That means iteration four should preserve the same conservative ordering instead of inventing a wider family promotion.

## Candidate Order

1. `structure_similarity_signatures`

This stays first because it is already materialized and validated, and it is still the lowest-risk anchor family.

2. `structure_followup_payloads`

This is now included in the manifest, but the single-accession validation still says `candidate_only_no_variant_anchor` and `direct_structure_backed_join_certified = false`, so it remains narrow and non-promotable.

3. `ligand_support_readiness`

This is now included too, but it is still support-only, keeps `Q9UCM0` deferred, and does not materialize ligand rows.

## Operator Queue Boundaries

The queue preview gives real operator next steps, but it does not justify bundle-family promotion:

- `P00387` is `bulk_assay_actionable`
- `Q9NZD4` is `rescuable_now`

Those are the safest immediate actions in the queue, but they belong to report-only operator guidance, not to release or family promotion.

## Why This Order Stays Safe

The ordering is conservative for the same reason the refreshed bundle is still safe:

- start with what is already validated
- keep the now-materialized structure follow-up surface narrow
- keep the support-only ligand readiness surface behind it
- leave the queue as a truth-checking action lane, not a bundle-family expansion

## Still Deferred

The following remain outside this window:

- ligand row materialization
- interaction-family materialization
- ligand similarity signatures
- direct structure-backed variant join promotion
- release-grade promotion
- protected latest surface rewrites

## Boundary

This note is report-only. It does not edit code, does not rewrite protected latest surfaces, and does not claim release readiness. The operator queue can guide immediate rescue work, but the dashboard remains `no-go` and the release grade remains blocked.
