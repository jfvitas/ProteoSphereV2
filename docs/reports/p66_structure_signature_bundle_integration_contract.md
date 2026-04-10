# P66 Structure Signature Bundle Integration Contract

This report-only contract defines the safest way to add `structure_similarity_signatures` into the lightweight preview bundle.

## Baseline

The bundle is still a verified preview:

- [artifacts/status/lightweight_bundle_manifest.json](/D:/documents/ProteoSphereV2/artifacts/status/lightweight_bundle_manifest.json)
- [artifacts/status/live_bundle_manifest_validation.json](/D:/documents/ProteoSphereV2/artifacts/status/live_bundle_manifest_validation.json)

Current baseline facts:

- `manifest_status`: `preview_generated_verified_assets`
- `budget_class`: `A`
- compressed size: `237008` bytes
- current `structure_similarity_signatures` count: `0`
- current `structures` count: `4`

## Source Grounding

This contract is grounded in:

- [artifacts/status/structure_similarity_signature_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/structure_similarity_signature_preview.json)
- [artifacts/status/p65_bundle_iteration_three_contract.json](/D:/documents/ProteoSphereV2/artifacts/status/p65_bundle_iteration_three_contract.json)
- [artifacts/status/structure_unit_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/structure_unit_summary_library.json)
- [artifacts/status/lightweight_bundle_manifest.json](/D:/documents/ProteoSphereV2/artifacts/status/lightweight_bundle_manifest.json)

The preview already shows a compact four-row structure signature slice derived from the current structure-unit library.

## Exact Rows To Integrate

Integrate the four preview rows, in this order:

1. `structure_unit:protein:P68871:4HHB:B`
1. `structure_unit:protein:P68871:4HHB:D`
1. `structure_unit:protein:P69905:4HHB:A`
1. `structure_unit:protein:P69905:4HHB:C`

These rows are structure-unit-derived, not variant-backed.

## Minimum Bundle Fields

The structure-signature family should carry only compact, derivable fields:

- `structure_signature_id`
- `entity_ref`
- `entity_type`
- `protein_ref`
- `parent_protein_ref`
- `structure_source`
- `structure_id`
- `chain_id`
- `residue_span_start`
- `residue_span_end`
- `fold_signature_id`
- `domain_signature_parts`
- `span_signature`
- `source_names`
- `source_manifest_id`
- `signature_schema_version`
- `derivation_status`
- `confidence_tier`
- `exact_entity_group_key`
- `protein_spine_group_key`
- `sequence_equivalence_group_key`
- `structure_chain_group_key`
- `structure_fold_group_key`
- `axes_present`
- `axes_inherited_from_parent`
- `recommended_split_policy`
- `derivation_notes`

## Integration Steps

1. Materialize the four preview rows as `structure_similarity_signatures` alongside the current structure-unit rows.
1. Keep fold and chain signatures derived directly from the current structure-unit summary library.
1. Carry the split-governance axes forward so the family can support leakage-safe planning.
1. Re-measure bundle size after emission and keep the bundle in budget class `A`.

## Size Risk

The size risk is `low_to_moderate`. The slice is only four rows and derives from existing structure units, but it introduces new family metadata and split-governance fields, so the bundle still needs a fresh measured size after integration.

## Exclusions

This integration does not add:

- `protein_variants`
- `ligands`
- `interactions`
- `protein_similarity_signatures`
- `leakage_groups`
- `ligand_similarity_signatures`
- `interaction_similarity_signatures`
- `dictionaries`

It also does not claim direct variant-structure anchoring, release readiness, or completeness beyond the four preview rows.

## Bottom Line

The next safe way to add structure similarity signatures is to promote the existing four-row preview slice into the bundle as a compact, structure-unit-derived family with fold and chain context, while keeping all heavier families out and re-measuring size after emission.
