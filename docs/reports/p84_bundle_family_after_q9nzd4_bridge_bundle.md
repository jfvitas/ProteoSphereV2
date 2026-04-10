# P84 Bundle Family After Q9NZD4 Bridge Bundle

This is a report-only ranking of the next safe preview-bundle family after `q9nzd4_bridge_validation_preview` is now included, grounded in [lightweight_bundle_manifest.json](D:/documents/ProteoSphereV2/artifacts/status/lightweight_bundle_manifest.json), [live_bundle_manifest_validation.json](D:/documents/ProteoSphereV2/artifacts/status/live_bundle_manifest_validation.json), [p83_bundle_family_after_stage1_panel.json](D:/documents/ProteoSphereV2/artifacts/status/p83_bundle_family_after_stage1_panel.json), [p68_ligand_family_materialization_order.json](D:/documents/ProteoSphereV2/artifacts/status/p68_ligand_family_materialization_order.json), and [operator_dashboard.json](D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/operator_dashboard.json).

## Rank 1

`ligand_identity_core_pilot`

This is the next safest family after the Q9NZD4 bridge preview because the repo already treats it as the first lightweight ligand-family materialization slice. It is identity-core only, keeps `Q9UCM0` deferred, and does not require binding context or ligand similarity to come first.

Why it is first:

- the bridge preview is already included and validated
- the materialization order guidance already identifies the four-accession identity-core pilot as the safest first ligand family
- it widens the surface only from a one-row bridge to a small identity-only ligand family
- it keeps the dashboard truth intact while the bundle still reports `ligands.included = false`

## Still Deferred

The following remain outside the next safe addition:

- binding-context grouping
- ligand similarity signatures
- interaction-family materialization
- release-grade promotion
- protected latest surface rewrites

## Boundary

This note is report-only. It does not claim the ligand family already exists in the bundle, and it does not loosen the current no-go dashboard state. The safest next family after the Q9NZD4 bridge preview is the identity-core ligand pilot, but it remains a proposal until real ligand rows are materialized.
