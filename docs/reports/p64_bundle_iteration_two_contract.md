# P64 Bundle Iteration Two Contract

This report-only contract defines the exact second safe bundle expansion iteration and its exclusions.

## Baseline

The current bundle remains a verified preview:

- [artifacts/status/lightweight_bundle_manifest.json](/D:/documents/ProteoSphereV2/artifacts/status/lightweight_bundle_manifest.json)
- [artifacts/status/live_bundle_manifest_validation.json](/D:/documents/ProteoSphereV2/artifacts/status/live_bundle_manifest_validation.json)

Baseline facts:

- `manifest_status`: `preview_generated_verified_assets`
- `budget_class`: `A`
- compressed size: `237008` bytes

## Iteration Two Anchor

The second expansion iteration comes from:

- [artifacts/status/p62_bundle_family_expansion_order.json](/D:/documents/ProteoSphereV2/artifacts/status/p62_bundle_family_expansion_order.json)

The second family is `leakage_groups`, chosen because split governance needs to stay explicit before broader family expansion.

## Exact Contents

Iteration two is accession-level leakage governance only.

Included accessions, in priority order:

- P68871
- P69905
- P04637
- P31749
- P00387
- P02042
- P02100
- P09105
- P69892
- Q2TAC2
- Q9NZD4

That is 11 rows total, one per currently materialized protein accession.

The iteration should use the current split-candidate preview as its seed evidence:

- [artifacts/status/leakage_signature_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/leakage_signature_preview.json)
- [artifacts/status/entity_signature_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/entity_signature_preview.json)
- [artifacts/status/protein_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/protein_summary_library.json)

The first two accessions are the current candidate-overlap surfaces, followed by the structure-followup accessions and then the protein-only accessions.

## Exact Exclusions

Iteration two does not include:

- `protein_variants`
- `structure_units`
- `ligands`
- `interactions`
- `protein_similarity_signatures`
- `structure_similarity_signatures`
- `ligand_similarity_signatures`
- `interaction_similarity_signatures`
- `dictionaries`

It also excludes heavy payloads such as full variant annotations, structure mapping payloads, coordinate projections, raw interaction dumps, raw ligand dumps, learned similarity clusters, graph-derived topology signatures, and dictionary-coded bundle segments.

## Size-Risk Note

The direct size risk for this iteration is low because it reuses the current accession-level split preview and does not pull in payload-heavy families. The operational rule is still the same: keep the bundle in budget class `A` and re-measure size after emission.

## Bottom Line

Iteration two is the leakage-group seed set for the 11 current split-candidate accessions. It stays compact, derives only from existing preview surfaces, and keeps all heavier families out of this slice.
