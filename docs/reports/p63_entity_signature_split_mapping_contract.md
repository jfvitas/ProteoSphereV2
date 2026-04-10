# P63 Entity Signature Split Mapping Contract

This report-only contract defines how the current [entity_signature_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/entity_signature_preview.json) should feed a future leakage-safe split engine.

## Current Preview

The current preview already contains one row per materialized entity:

- `11` proteins
- `1874` protein variants
- `4` structure units
- `1889` total rows

That makes it a good input surface for split governance, because the preview is already entity-level instead of accession-only.

## Contract

The future split engine should treat each `entity_signature_preview` row as an atomic split unit.

Hard rule:

- never split inside an entity row

Default hard boundaries:

- `exact_entity_group`
- `protein_spine_group`

Strict leakage boundaries:

- `sequence_equivalence_group`
- `variant_delta_group`
- `structure_chain_group`
- `structure_fold_group`

Soft balance or diagnostics only:

- `taxon_group`
- `motif_domain_architecture_group`
- `pathway_context_group`

Reserved for later:

- `ligand_identity_group`
- `binding_context_group`

## How The Preview Feeds The Split Engine

The split engine should read the preview rows and derive one split-key bundle per row.

For proteins:

- `exact_entity_group = summary_id`
- `protein_spine_group = protein_ref`
- `sequence_equivalence_group = sequence_checksum`

For protein variants:

- `exact_entity_group = summary_id`
- `protein_spine_group = parent_protein_ref`
- `sequence_equivalence_group = inherited parent sequence checksum`
- `variant_delta_group = sequence_delta_signature`

For structure units:

- `exact_entity_group = summary_id`
- `protein_spine_group = protein_ref`
- `sequence_equivalence_group = inherited parent sequence checksum`
- `structure_chain_group = structure_source + structure_id + chain_id + residue span`
- `structure_fold_group = sorted current fold/domain identifiers`

Ligand axes stay present in the contract, but they must remain null until lightweight ligand rows exist.

## Why The Order Matters

The split engine should consult the keys in this order:

1. exact entity
1. protein spine
1. sequence or mutation or structure leakage axis
1. soft balance axes

That order prevents accidental leakage from the strongest identity signals before any balancing logic is considered.

## Grounded Examples

- `protein:P04637` should keep all variant rows on the same protein spine group.
- `protein_variant:protein:P04637:A119D` should stay anchored to `protein:P04637` while still carrying a unique `variant_delta_group`.
- `structure_unit:protein:P68871:4HHB:B` should remain isolated by exact entity, protein spine, chain, and fold groups.

## Boundary

This is report-only. It does not edit code, it does not rewrite protected latest surfaces, and it does not claim ligand split support yet.

