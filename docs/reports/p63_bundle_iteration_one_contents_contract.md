# P63 Bundle Iteration One Contents Contract

This report-only contract defines the exact first safe bundle expansion iteration and its exclusions.

## Baseline

The current bundle is a verified preview:

- [artifacts/status/lightweight_bundle_manifest.json](/D:/documents/ProteoSphereV2/artifacts/status/lightweight_bundle_manifest.json)
- [artifacts/status/live_bundle_manifest_validation.json](/D:/documents/ProteoSphereV2/artifacts/status/live_bundle_manifest_validation.json)

Baseline facts:

- `manifest_status`: `preview_generated_verified_assets`
- `budget_class`: `A`
- compressed size: `237008` bytes

## Iteration One Anchor

The first expansion iteration comes from:

- [artifacts/status/p62_bundle_family_expansion_order.json](/D:/documents/ProteoSphereV2/artifacts/status/p62_bundle_family_expansion_order.json)

The first family is `protein_similarity_signatures`, chosen as the smallest truth-preserving governance surface.

## Exact Contents

Iteration one is protein-only.

Included accessions:

- P00387
- P02042
- P02100
- P04637
- P09105
- P31749
- P68871
- P69892
- P69905
- Q2TAC2
- Q9NZD4

That is 11 rows total, one per currently materialized protein.

The iteration should use the current protein summary slice and the live entity signature preview as its seed evidence:

- [artifacts/status/protein_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/protein_summary_library.json)
- [artifacts/status/entity_signature_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/entity_signature_preview.json)
- [artifacts/status/leakage_signature_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/leakage_signature_preview.json)

The row contract should stay compact and derived, not payload-heavy. It should carry identity, linkage, and split-governance fields only.

## Exact Exclusions

Iteration one does not include:

- `protein_variants`
- `structure_units`
- `ligands`
- `interactions`
- `structure_similarity_signatures`
- `ligand_similarity_signatures`
- `interaction_similarity_signatures`
- `leakage_groups`
- `dictionaries`

It also excludes heavy payloads such as full variant annotations, structure mapping payloads, coordinate projections, raw interaction dumps, raw ligand dumps, and dictionary-coded bundle segments.

## Size-Aware Rule

The first iteration should remain low impact because it is derived metadata around the current protein baseline. The operational rule is simple: keep the bundle in budget class `A` and re-measure size after emission.

## Bottom Line

Iteration one is a protein-only similarity-signature seed set for the 11 verified proteins. Everything variant-, structure-, ligand-, interaction-, leakage-, and dictionary-related stays out of this first expansion slice.
