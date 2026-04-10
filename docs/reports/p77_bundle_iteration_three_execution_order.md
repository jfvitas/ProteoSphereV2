# P77 Bundle Iteration Three Execution Order

This is a report-only execution-order note for bundle iteration three, grounded in [p76_bundle_next_family_ranking.json](D:/documents/ProteoSphereV2/artifacts/status/p76_bundle_next_family_ranking.json), [lightweight_bundle_manifest.json](D:/documents/ProteoSphereV2/artifacts/status/lightweight_bundle_manifest.json), [live_bundle_manifest_validation.json](D:/documents/ProteoSphereV2/artifacts/status/live_bundle_manifest_validation.json), and [operator_dashboard.json](D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/operator_dashboard.json).

## Current Truth

The bundle is still a verified preview:

- `bundle_kind = debug_bundle`
- `packaging_layout = compressed_sqlite`
- `bundle_budget_class = A`
- `bundle_compressed_size_bytes = 265356`
- `validation_status = aligned_current_preview_with_verified_assets`
- `operator_go_no_go = no-go`
- `release_grade_status = blocked_on_release_grade_bar`

So iteration three should be treated as a truth-preserving bundle step, not as a release move.

## Execution Order

1. `structure_similarity_signatures`

This stays first because it is already materialized and already validated. It is the lowest-risk anchor for iteration three.

2. `structure_followup_payloads`

This is the narrow candidate-only structure follow-up surface. It is the safest next incremental step after the existing structure similarity family because it is explicit about remaining variant-anchor requirements.

3. `ligand_support_readiness`

This is the safest ligand-adjacent follow-up because it is support-only, keeps `Q9UCM0` deferred, and does not materialize ligand rows.

## Why This Order Works

The order keeps the bundle honest:

- start with what is already in the manifest and validated
- move next to a narrow candidate-only structure surface
- finish with a support-only ligand readiness surface

That sequence preserves the current preview counts and avoids widening the bundle faster than the evidence supports.

## What Must Stay Out

The following remain deferred:

- interaction-family materialization
- ligand similarity signatures
- direct structure-backed variant join promotion
- release-grade promotion
- protected latest surface rewrites

## Boundary

This note is report-only. It does not edit code, does not rewrite protected latest surfaces, and does not claim release readiness. Only the first-ranked family is already materialized and validated; the other two remain preview/support surfaces.
