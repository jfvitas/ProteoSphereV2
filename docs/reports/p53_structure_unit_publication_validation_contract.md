# Structure-Unit Publication Validation Contract

- Generated at: `2026-04-01T11:16:33.1311833-05:00`
- Scope: report-only validation contract for publishing the structure-unit summary library alongside protected latest surfaces
- Basis: the landed structure-unit summary library, the inventory report, the protected-surface contract, the structure-unit materializer contract, and the lightweight bundle guidance

## Current Library State

- Library id: `summary-library:structure-units:v1`
- Schema version: `2`
- Source manifest id: `UniProt:2026-03-23:api:2a2e3af898cc6772|bio-agent-lab/reactome:2026-03-16|IntAct:20260323T002625Z:download:6a49b82dc9ec053d|bio-agent-lab-import-manifest:v1`
- Record count: `4`
- Record types: `structure_unit: 4`
- Storage tier: `feature_cache`

This contract treats the structure-unit library as a publishable artifact only when it stays versioned or run-scoped. It is not a rewrite path for the protected latest surfaces.

## Protected Surfaces

These surfaces are immutable during publication:

- `data/canonical/LATEST.json`
- `data/packages/LATEST.json`
- `data/packages/LATEST.partial.json`
- `data/raw/bootstrap_runs/LATEST.json`
- `data/raw/local_registry_runs/LATEST.json`

Current package latest remains held and not release-grade-ready, so publication must stay outside the protected latest paths.

## Publication Checks

Before publishing the structure-unit summary library, verify:

- the output path is versioned or run-scoped and never named `LATEST.json` or `LATEST.partial.json`
- the published artifact preserves the source `library_id`, `schema_version`, `source_manifest_id`, and `record_count`
- the artifact remains a feature-cache or release-asset publication, not a canonical overwrite
- the publication does not change `data/packages/LATEST.json` or `data/packages/LATEST.partial.json`
- if a lightweight bundle is built, its manifest includes exact file inventory, sizes, and checksums
- the publication output remains separate from canonical, bootstrap, and local-registry latest surfaces

The current supporting guidance remains the same as in [`p50_lightweight_bundle_packaging_proposal.md`](/D:/documents/ProteoSphereV2/docs/reports/p50_lightweight_bundle_packaging_proposal.md), [`release_benchmark_bundle.md`](/D:/documents/ProteoSphereV2/docs/reports/release_benchmark_bundle.md), and [`package_materialization_notes.md`](/D:/documents/ProteoSphereV2/docs/reports/package_materialization_notes.md).

## Cleanup Interaction

If duplicate cleanup runs before publication, the cleanup must also satisfy:

- the structure-unit source artifact remains recoverable from a surviving manifest or versioned output
- duplicate cleanup does not delete the only source artifact needed to publish the library
- cleanup and publication are validated independently so one does not mutate the other's protected surfaces

## Post-Action Validation

After publication:

- parse `data/canonical/LATEST.json` successfully
- parse `data/packages/LATEST.json` successfully
- parse `data/packages/LATEST.partial.json` successfully
- parse `data/raw/bootstrap_runs/LATEST.json` successfully
- parse `data/raw/local_registry_runs/LATEST.json` successfully
- confirm no protected-surface file content changed as a side effect
- confirm any new structure-unit bundle artifact lives outside protected latest paths

If cleanup happened first, also rerun the inventory and status checks that prove the surviving bytes still line up with the pre-cleanup digests.

## What This Contract Is Not

- No code edits.
- No publication execution.
- No cleanup execution.
- No canonical latest rewrites.
- No package latest rewrites.
- No bootstrap or local registry latest rewrites.
- No publishing by filename or size alone.

## Evidence Anchors

- [`structure_unit_summary_library.json`](/D:/documents/ProteoSphereV2/artifacts/status/structure_unit_summary_library.json)
- [`summary_library_inventory.json`](/D:/documents/ProteoSphereV2/artifacts/status/summary_library_inventory.json)
- [`p51_protected_surface_validation_contract.json`](/D:/documents/ProteoSphereV2/artifacts/status/p51_protected_surface_validation_contract.json)
- [`p52_structure_unit_materializer_contract.json`](/D:/documents/ProteoSphereV2/artifacts/status/p52_structure_unit_materializer_contract.json)
- [`structure_unit_summary_library.md`](/D:/documents/ProteoSphereV2/docs/reports/structure_unit_summary_library.md)
- [`summary_library_inventory.md`](/D:/documents/ProteoSphereV2/docs/reports/summary_library_inventory.md)
- [`summary_library_validation.md`](/D:/documents/ProteoSphereV2/docs/reports/summary_library_validation.md)
- [`p51_protected_surface_validation_contract.md`](/D:/documents/ProteoSphereV2/docs/reports/p51_protected_surface_validation_contract.md)
- [`p52_structure_unit_materializer_contract.md`](/D:/documents/ProteoSphereV2/docs/reports/p52_structure_unit_materializer_contract.md)
- [`p50_lightweight_bundle_packaging_proposal.md`](/D:/documents/ProteoSphereV2/docs/reports/p50_lightweight_bundle_packaging_proposal.md)
- [`release_benchmark_bundle.md`](/D:/documents/ProteoSphereV2/docs/reports/release_benchmark_bundle.md)
- [`package_materialization_notes.md`](/D:/documents/ProteoSphereV2/docs/reports/package_materialization_notes.md)
- [`source_storage_strategy.md`](/D:/documents/ProteoSphereV2/docs/reports/source_storage_strategy.md)

