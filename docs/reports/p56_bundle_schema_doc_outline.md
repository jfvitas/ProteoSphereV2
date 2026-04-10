# P56 Bundle Schema Doc Outline

Date: 2026-04-01
Artifact: `p56_bundle_schema_doc_outline`

## Objective

Define a `report-only minimal outline` for the downloadable lightweight bundle schema document.

This is the outline a future `proteosphere-lite.schema.md` should follow when generated from the current bundle-manifest contract and the current live lightweight-library surfaces.

This artifact does not add code and does not claim that a built bundle already exists.

It is grounded in:

- [p51_bundle_manifest_budget_contract.md](/D:/documents/ProteoSphereV2/docs/reports/p51_bundle_manifest_budget_contract.md)
- [p53_bundle_manifest_example.md](/D:/documents/ProteoSphereV2/docs/reports/p53_bundle_manifest_example.md)
- [p54_bundle_manifest_export_contract.md](/D:/documents/ProteoSphereV2/docs/reports/p54_bundle_manifest_export_contract.md)
- [protein_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/protein_summary_library.json)
- [LATEST.json](/D:/documents/ProteoSphereV2/data/canonical/LATEST.json)

## Current Bundle Posture

The current truthful posture is still a narrow preview/debug bundle:

- packaging layout: `compressed_sqlite`
- bundle kind: `debug_bundle`
- content scope: `planning_governance_only`

The current live lightweight families are:

- `proteins`
- `motif_annotations`
- `pathway_annotations`
- `provenance_records`

The current preview does **not** yet materialize standalone lightweight tables for:

- `protein_variants`
- `structures`
- `ligands`
- `interactions`
- similarity/signature families
- `leakage_groups`
- `dictionaries`

That means the schema document should be minimal, explicit, and current-surface-first.

## Minimal Schema Document Outline

The future schema document should contain these sections.

### 1. Bundle Overview

Purpose:

- explain what the bundle is
- explain what it is not
- state bundle posture and release type

Minimum contents:

- bundle ID
- bundle kind
- schema version
- packaging layout
- content scope
- honesty note on preview vs built release

### 2. Included Assets

Purpose:

- describe the physical release assets users download

Minimum contents:

- `proteosphere-lite.sqlite.zst`
- `proteosphere-lite.release_manifest.json`
- `proteosphere-lite.sha256`
- optional docs if present

### 3. Schema Conventions

Purpose:

- give shared rules before table-by-table detail

Minimum contents:

- key naming conventions
- ID namespaces
- nullability guidance
- nested record guidance
- lineage/provenance conventions
- bundle-field vs source-field distinction

### 4. Current Live Table Families

Purpose:

- enumerate the currently materialized logical families

Minimum contents:

- family name
- inclusion status
- record count
- whether the family is standalone or nested in the preview
- source artifact used for grounding

### 5. `proteins` Family

Purpose:

- document the primary live table family

Minimum contents:

- row purpose
- primary keys and lookup keys
- required identity fields
- biological summary fields
- nested context fields
- source rollup fields

Current grounding from [protein_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/protein_summary_library.json):

- `11` protein rows
- row examples include:
  - `summary_id`
  - `protein_ref`
  - `protein_name`
  - `organism_name`
  - `taxon_id`
  - `sequence_checksum`
  - `sequence_version`
  - `sequence_length`
  - `gene_names`
  - `aliases`
  - `join_status`
  - `join_reason`
  - `context`

### 6. `motif_annotations` Family

Purpose:

- document how motif and domain references are represented in the current preview

Minimum contents:

- current preview representation
- source namespaces
- reference-level fields
- difference between motif and domain rows

Important current truth:

- this family is currently represented through nested arrays on protein rows, not a standalone table
- current preview count is effectively:
  - `13` motif references
  - `85` domain references
  - preview family count shown as `98`

### 7. `pathway_annotations` Family

Purpose:

- document pathway context carried by the current preview

Minimum contents:

- current nested representation
- pathway reference fields
- lineage to Reactome or other pathway sources

Current grounding:

- `254` pathway references in the current preview slice

### 8. `provenance_records` Family

Purpose:

- document source lineage and evidence pointers

Minimum contents:

- provenance ID
- source name
- source record ID
- release version or snapshot ID
- acquisition timestamp
- checksum
- join/evidence notes

Current grounding:

- `17` provenance pointers in the current preview slice

### 9. Reserved Families

Purpose:

- reserve future sections without pretending they are already materialized

Reserved stubs should exist for:

- `protein_variants`
- `structures`
- `ligands`
- `interactions`
- `protein_similarity_signatures`
- `structure_similarity_signatures`
- `ligand_similarity_signatures`
- `interaction_similarity_signatures`
- `leakage_groups`
- `dictionaries`

Each reserved section should say:

- not yet materialized
- expected role in the future bundle
- whether the family is intended to be required or optional

### 10. Source Lineage And Trust Notes

Purpose:

- explain how row fields tie back to upstream sources

Minimum contents:

- source snapshot IDs
- precedence notes
- partial/single-source warnings
- difference between corroborated and single-source values

### 11. Exclusions

Purpose:

- make heavy non-bundle payloads explicit

Minimum contents:

- raw structure assets
- raw assay dumps
- large network payloads
- heavy packet assets
- diagrams and maps

### 12. Schema Evolution Notes

Purpose:

- explain how the schema doc should evolve without breaking readers

Minimum contents:

- schema versioning rule
- preview vs release bundle differences
- migration trigger for standalone motif/pathway/provenance tables
- future partitioned-layout note if the bundle outgrows single-file packaging

## Minimal Section Ordering

The shortest acceptable generated schema doc should follow this order:

1. bundle overview
2. included assets
3. schema conventions
4. live families summary
5. proteins
6. motif annotations
7. pathway annotations
8. provenance records
9. reserved families
10. source lineage and trust
11. exclusions
12. schema evolution

## Required Family-Level Honesty Rules

The schema doc must:

- distinguish standalone tables from nested preview families
- report current family counts only from live lightweight surfaces
- avoid inferring family materialization from canonical counts alone
- mark reserved families as future-only until they are actually in the bundle

The schema doc must not:

- document ligands, structures, or interactions as live bundle tables yet
- claim similarity or leakage signatures are already shipped
- imply that the preview bundle is a final `core_default` release

## Recommended Example Anchors

The generated schema doc should include at least one field-level example rooted in a current protein row such as:

- `protein:P00387`

That row already demonstrates the current preview structure well because it contains:

- identity fields
- sequence fields
- motif references
- domain references
- provenance pointers
- source rollups

## Bottom Line

The minimal schema doc should describe the current preview bundle accurately, not the eventual full library.

That means:

- full documentation for the four live families
- explicit nested-preview notes for motif, pathway, and provenance content
- reserved stubs for future families
- strong lineage and exclusion notes

That is enough to make the current bundle intelligible without over-documenting non-existent tables.
