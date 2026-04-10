# P65 Bundle Iteration Three Contract

This report-only contract defines the exact third safe bundle expansion iteration and its exclusions.

## Baseline

The current bundle remains a verified preview:

- [artifacts/status/lightweight_bundle_manifest.json](/D:/documents/ProteoSphereV2/artifacts/status/lightweight_bundle_manifest.json)
- [artifacts/status/live_bundle_manifest_validation.json](/D:/documents/ProteoSphereV2/artifacts/status/live_bundle_manifest_validation.json)

Baseline facts:

- `manifest_status`: `preview_generated_verified_assets`
- `budget_class`: `A`
- compressed size: `237008` bytes

## Iteration Three Anchor

The third expansion iteration comes from:

- [artifacts/status/p62_bundle_family_expansion_order.json](/D:/documents/ProteoSphereV2/artifacts/status/p62_bundle_family_expansion_order.json)
- [artifacts/status/p64_bundle_iteration_two_contract.json](/D:/documents/ProteoSphereV2/artifacts/status/p64_bundle_iteration_two_contract.json)

The third family is `structure_similarity_signatures`, chosen because it extends the same low-risk similarity pattern to the existing structure surface once leakage grouping is in place.

## Exact Contents

Iteration three is structure-unit-derived similarity metadata only.

Included structure units, in priority order:

- `structure_unit:protein:P68871:4HHB:B`
- `structure_unit:protein:P68871:4HHB:D`
- `structure_unit:protein:P69905:4HHB:A`
- `structure_unit:protein:P69905:4HHB:C`

That is 4 rows total, derived from the two current parent accessions:

- P68871
- P69905

The iteration should use the current structure-unit surface and operator/runtime truth as its seed evidence:

- [artifacts/status/structure_unit_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/structure_unit_summary_library.json)
- [artifacts/status/entity_signature_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/entity_signature_preview.json)
- [artifacts/status/leakage_signature_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/leakage_signature_preview.json)
- [artifacts/status/p53_structure_unit_operator_surface_contract.json](/D:/documents/ProteoSphereV2/artifacts/status/p53_structure_unit_operator_surface_contract.json)
- [artifacts/status/p61_minimum_leakage_signature_schema.json](/D:/documents/ProteoSphereV2/artifacts/status/p61_minimum_leakage_signature_schema.json)

The row contract should carry chain and fold context, but remain compact and feature-cache friendly.

## Exact Exclusions

Iteration three does not include:

- `protein_variants`
- `ligands`
- `interactions`
- `protein_similarity_signatures`
- `leakage_groups`
- `ligand_similarity_signatures`
- `interaction_similarity_signatures`
- `dictionaries`

It also excludes heavy payloads such as full variant annotations, structure mapping payloads, coordinate projections, confidence or resolution payloads, raw interaction dumps, raw ligand dumps, learned similarity clusters, graph-derived topology signatures, and dictionary-coded bundle segments.

## Size-Risk Note

The direct size risk for this iteration is low-to-moderate. It only uses four existing structure units, so the slice should stay compact, but it is richer than the accession-only leakage contracts because it carries chain and fold context. The operational rule remains the same: keep the bundle in budget class `A` and re-measure size after emission.

## Bottom Line

Iteration three is the structure-similarity seed set for the four verified structure units in the current preview. It stays small, derived, and source-backed, and it keeps all heavier families out of this slice.
