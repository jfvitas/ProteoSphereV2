# P78 Bundle Iteration Three Post-Refresh Order

This is a report-only reassessment of the safest bundle-iteration-three order after the refreshed preview manifest, grounded in [lightweight_bundle_manifest.json](D:/documents/ProteoSphereV2/artifacts/status/lightweight_bundle_manifest.json), [live_bundle_manifest_validation.json](D:/documents/ProteoSphereV2/artifacts/status/live_bundle_manifest_validation.json), [p77_bundle_iteration_three_execution_order.json](D:/documents/ProteoSphereV2/artifacts/status/p77_bundle_iteration_three_execution_order.json), and [operator_dashboard.json](D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/operator_dashboard.json).

## Current Truth

The refreshed bundle is still a verified preview:

- `bundle_kind = debug_bundle`
- `packaging_layout = compressed_sqlite`
- `bundle_budget_class = A`
- `bundle_compressed_size_bytes = 266321`
- `validation_status = aligned_current_preview_with_verified_assets`
- `operator_go_no_go = no-go`
- `release_grade_status = blocked_on_release_grade_bar`

The refresh matters because the manifest now includes:

- `structure_followup_payloads`
- `ligand_support_readiness`

Both are aligned in live validation, which means the iteration-three window is now fully materialized in the preview bundle.

## Post-Refresh Order

1. `structure_similarity_signatures`

This remains first because it is still the stable, already-materialized anchor family.

2. `structure_followup_payloads`

This is now included and validated, so it should follow the anchor family as the narrow structure-adjacent executable surface.

3. `ligand_support_readiness`

This is now included and validated too, but it remains the safest ligand-adjacent surface because it is support-only and still defers Q9UCM0.

## Why This Order Is Safe

The refresh did not change the safety logic:

- start with what was already validated
- then keep the narrow structure follow-up surface
- then keep the support-only ligand readiness surface

That preserves the compact bundle and avoids moving into a broader family before the current iteration-three window is fully understood.

## What Changed In The Refresh

- `structure_followup_payloads` crossed from preview-only into included bundle material
- `ligand_support_readiness` crossed from preview-only into included bundle material
- the iteration-three window is now fully aligned in the refreshed manifest

## Still Deferred

The following remain outside this window:

- interaction-family materialization
- ligand similarity signatures
- direct structure-backed variant join promotion
- release-grade promotion
- protected latest surface rewrites

## Boundary

This note is report-only. It does not edit code, does not rewrite protected latest surfaces, and does not claim release readiness. The refreshed bundle is aligned, but the dashboard is still `no-go` and the release grade remains blocked.
