# P85 Bundle Family After Identity Core Preview

This is a report-only ranking of the next safe preview-bundle family after `ligand_identity_core_materialization_preview` is now included, grounded in [lightweight_bundle_manifest.json](D:/documents/ProteoSphereV2/artifacts/status/lightweight_bundle_manifest.json), [live_bundle_manifest_validation.json](D:/documents/ProteoSphereV2/artifacts/status/live_bundle_manifest_validation.json), [p84_bundle_family_after_q9nzd4_bridge_bundle.json](D:/documents/ProteoSphereV2/artifacts/status/p84_bundle_family_after_q9nzd4_bridge_bundle.json), [p68_ligand_family_materialization_order.json](D:/documents/ProteoSphereV2/artifacts/status/p68_ligand_family_materialization_order.json), [p72_ligand_similarity_signature_implementation_contract.json](D:/documents/ProteoSphereV2/artifacts/status/p72_ligand_similarity_signature_implementation_contract.json), and [operator_dashboard.json](D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/operator_dashboard.json).

## Rank 1

`ligand_similarity_signatures`

This is the next safe preview-bundle family in the repo's own order after the identity-core preview is included. It is the first derived ligand surface that can follow once a real ligand family exists, but it remains blocked today because `ligands.included = false` and the bundle still reports zero ligand records.

Why it is first:

- the identity-core preview and Q9NZD4 bridge preview are already included
- the repo's own implementation contract ranks ligand similarity as the next safest derived family after dictionaries
- it widens the surface from preview panels to a derived family without jumping straight to interaction materialization

## Still Deferred

The following remain outside the next safe addition:

- ligands source-family materialization
- interaction-family materialization
- interaction_similarity_signatures
- release-grade promotion
- protected latest surface rewrites

## Boundary

This note is report-only. It does not claim the ligand similarity family already exists in the bundle, and it does not loosen the current no-go dashboard state. The next safe family in order is ligand similarity, but it remains blocked until real ligand rows are materialized.
