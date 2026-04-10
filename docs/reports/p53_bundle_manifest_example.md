# P53 Bundle Manifest Example

Date: 2026-04-01
Artifact: `p53_bundle_manifest_example`

## Objective

Provide a report-only example of what the downloadable lightweight-library manifest should look like if it were generated from the current repo surfaces.

This example is grounded in:

- [p51_bundle_manifest_budget_contract.md](/D:/documents/ProteoSphereV2/docs/reports/p51_bundle_manifest_budget_contract.md)
- [p50_lightweight_bundle_packaging_proposal.md](/D:/documents/ProteoSphereV2/docs/reports/p50_lightweight_bundle_packaging_proposal.md)
- [protein_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/protein_summary_library.json)
- [LATEST.json](/D:/documents/ProteoSphereV2/data/canonical/LATEST.json)
- [source_coverage_matrix.json](/D:/documents/ProteoSphereV2/artifacts/status/source_coverage_matrix.json)

## Scope Of This Example

This is a `report-only manifest example`, not a claim that the bundle has already been built.

The example intentionally models the current repo state as a preview bundle:

- bundle kind: `debug_bundle`
- packaging layout: `compressed_sqlite`
- content scope: `planning_governance_only`

That choice is deliberate. The current lightweight library surface is still only a first protein-centered slice, not the full future library.

## Why The Example Uses A Preview/Debug Bundle

The current library surfaces are still narrow:

- [protein_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/protein_summary_library.json) contains `11` protein records
- the same artifact currently exposes:
  - `13` motif references
  - `85` domain references
  - `254` pathway references
  - `17` provenance pointers
- [LATEST.json](/D:/documents/ProteoSphereV2/data/canonical/LATEST.json) shows a larger canonical state:
  - `11` proteins
  - `4124` ligands
  - `5138` assays
  - `0` unresolved assay cases

That means a realistic current manifest example should:

- include protein and annotation-oriented tables
- acknowledge that ligand, interaction, structure, variant, and signature tables are not yet materialized in the lightweight bundle
- stay within the `Class A` size target from [p51_bundle_manifest_budget_contract.md](/D:/documents/ProteoSphereV2/docs/reports/p51_bundle_manifest_budget_contract.md)

## Manifest Example Shape

The example manifest assumes:

- asset filename: `proteosphere-lite.sqlite.zst`
- release manifest filename: `proteosphere-lite.release_manifest.json`
- checksum file: `proteosphere-lite.sha256`
- packaging layout: `compressed_sqlite`

It also assumes a preview release token:

- `2026.04.01-protein-preview.1`

## Included Families In The Example

The example marks these families as included:

- `proteins`
- `motif_annotations`
  - current preview folds motif and domain reference counts into this family
- `pathway_annotations`
- `provenance_records`

The example marks these as not yet included:

- `protein_variants`
- `structures`
- `ligands`
- `interactions`
- all similarity/signature families
- `leakage_groups`
- `dictionaries`

This is the most honest representation of the current repo surfaces.

## Size-Budget Interpretation

Because this is only a preview bundle over a small first-slice summary library, the example marks the bundle as:

- `budget_class = A`
- `cap_compliance = true`

The sizes are explicitly estimated, not measured. The example uses a conservative preview estimate:

- compressed size: about `4 MiB`
- uncompressed size: about `12 MiB`

That is comfortably inside the `Class A` target defined in [p51_bundle_manifest_budget_contract.md](/D:/documents/ProteoSphereV2/docs/reports/p51_bundle_manifest_budget_contract.md).

## Important Honesty Boundaries

The manifest example explicitly avoids pretending that:

- the bundle already exists on disk
- checksums have been computed for a built artifact
- ligand, interaction, structure, or similarity tables are already packaged
- the preview bundle is publish-ready as a final `core_default` release

Instead, it shows what the manifest contract should look like right now if we emitted a truthful preview bundle from the current library surfaces.

## Source Snapshot Grounding

The example manifest carries source snapshot lineage from the current summary-library and canonical surfaces:

- `UniProt:2026-03-23:api:2a2e3af898cc6772`
- `bio-agent-lab/reactome:2026-03-16`
- `IntAct:20260323T002625Z:download:6a49b82dc9ec053d`
- `bio-agent-lab-import-manifest:v1`
- canonical run: `raw-canonical-20260330T221513Z`

It also includes the current coverage summary:

- `53` tracked sources
- `48` present
- `2` partial
- `3` missing

## Recommended Reading Of The Example

Read this example manifest as:

- a contract-valid preview
- a template for future generated manifests
- a checkpoint showing how the current repo surfaces map into the final bundle model

Do not read it as:

- a built release artifact
- a final library manifest
- a full-content distribution declaration

## Bottom Line

The example manifest shows the correct current posture:

- use `compressed_sqlite`
- ship a narrow planning/governance preview first
- keep the bundle inside `Class A`
- explicitly mark non-materialized table families as absent
- carry real current source-snapshot lineage and current library counts

That gives the repo a truthful manifest template now, while preserving a clean path to the future fuller `core_default` bundle.
