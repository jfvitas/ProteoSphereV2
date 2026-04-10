# P57 Bundle Preview Gate

This report-only note defines when the bundle manifest can move from `example_only_not_built` to `preview_generated_unverified`.

## Current State

The manifest is still in `example_only_not_built` because the repo has report-only bundle contracts, but no generated preview manifest artifact yet.

The gate is based on:

- [artifacts/status/p55_bundle_field_mapping.json](/D:/documents/ProteoSphereV2/artifacts/status/p55_bundle_field_mapping.json)
- [docs/reports/p55_bundle_field_mapping.md](/D:/documents/ProteoSphereV2/docs/reports/p55_bundle_field_mapping.md)
- [artifacts/status/p56_bundle_contents_contract.json](/D:/documents/ProteoSphereV2/artifacts/status/p56_bundle_contents_contract.json)
- [docs/reports/p56_bundle_contents_contract.md](/D:/documents/ProteoSphereV2/docs/reports/p56_bundle_contents_contract.md)
- [artifacts/status/p50_lightweight_bundle_packaging_proposal.json](/D:/documents/ProteoSphereV2/artifacts/status/p50_lightweight_bundle_packaging_proposal.json)

## Move Condition

The manifest can move to `preview_generated_unverified` when a run-scoped preview manifest has been generated from the current live bundle surfaces and checked against the report stack above.

That preview must:

- use the `compressed_sqlite` bundle direction
- reflect the current live protein and structure-unit artifacts
- include the current partial motif and pathway surfaces only as truth-bearing context
- preserve the declared-empty families as empty or reserved
- avoid inventing counts, checksums, or completeness claims

## Required Inputs For The Preview

The preview generator should consume these live inputs first:

- [artifacts/status/protein_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/protein_summary_library.json)
- [artifacts/status/structure_unit_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/structure_unit_summary_library.json)
- [artifacts/status/source_coverage_matrix.json](/D:/documents/ProteoSphereV2/artifacts/status/source_coverage_matrix.json)
- [artifacts/status/broad_mirror_progress.json](/D:/documents/ProteoSphereV2/artifacts/status/broad_mirror_progress.json)
- [artifacts/status/p51_structure_motif_join_mapping.json](/D:/documents/ProteoSphereV2/artifacts/status/p51_structure_motif_join_mapping.json)
- [artifacts/status/p50_motif_pathway_enrichment_tranche.json](/D:/documents/ProteoSphereV2/artifacts/status/p50_motif_pathway_enrichment_tranche.json)
- [artifacts/status/p53_structure_unit_operator_surface_contract.json](/D:/documents/ProteoSphereV2/artifacts/status/p53_structure_unit_operator_surface_contract.json)

## Gate Checks

Before the state can advance, the preview must satisfy all of the following:

1. The preview manifest mirrors the field map in `p55_bundle_field_mapping`.
1. The preview contents mirror the surface inventory in `p56_bundle_contents_contract`.
1. The preview keeps `ELM` conditional and does not treat it as scrape-first.
1. The preview keeps `mega_motif_base` and `motivated_proteins` out of the live payload.
1. The preview preserves `protein_variants`, ligands, interactions, similarity tables, leakage groups, and dictionaries as declared-but-not-populated.
1. The preview does not claim release-grade verification.

## Still Blocked

The gate stays closed until a real preview artifact exists. Current blockers are:

- no generated preview manifest file
- no exporter implementation producing the bundle preview yet
- no release-grade checksum or publication artifact

These blockers are acceptable for `preview_generated_unverified`, but not for a final release manifest.

## Bottom Line

The state can move from `example_only_not_built` to `preview_generated_unverified` once the repo has a generated, run-scoped manifest preview that is consistent with the current field map and contents contract. The move does not require final verification, but it does require a real preview artifact instead of an example-only note.
