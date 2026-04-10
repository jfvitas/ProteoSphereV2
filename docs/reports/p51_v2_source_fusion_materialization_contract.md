# P51 V2 Source Fusion Materialization Contract

This contract maps the current summary-library schema in [core/library/summary_record.py](../../core/library/summary_record.py) and the current builder in [execution/library/build_summary_library.py](../../execution/library/build_summary_library.py) to the first v2 record families: `protein_variant` and `structure_unit`.

## Scope

- This is report-only.
- It is grounded in the current summary-library plans and trust contracts.
- It focuses on already-procured sources first, not future procurement.

## Source Order

### `protein_variant`

Populate from already-procured evidence in this order:

1. `UniProt`
2. `local extracted assets`
3. `AlphaFold DB`
4. `RCSB/PDBe`

UniProt stays the accession and sequence spine. Local extracted assets may carry already-procured construct or isoform hints. AlphaFold DB and RCSB/PDBe can support the record only when they concretely corroborate an already-known variant or construct boundary.

### `structure_unit`

Populate from already-procured evidence in this order:

1. `RCSB/PDBe`
2. `PDBe UniProt mapping / SIFTS-style bridge`
3. `AlphaFold DB`
4. `PDBBind`
5. `BioLiP`
6. `local extracted assets`

RCSB/PDBe supplies experimental identity. The UniProt mapping bridge resolves the accession projection. AlphaFold DB supplies explicit predicted-structure support only. PDBBind and BioLiP are support lanes, not replacements for experimental truth.

## Field Mapping

### `protein_variant`

Fields added in v2:

- `protein_ref`
- `parent_protein_ref`
- `variant_signature`
- `variant_kind`
- `mutation_list`
- `sequence_delta_signature`
- `construct_type`
- `is_partial`
- `variant_relation_notes`

Inheritance from the current schema:

- `summary_id`
- `join_status`
- `join_reason`
- `context`
- `notes`

Population rules:

- `protein_ref` and `parent_protein_ref` stay accession-first and come from UniProt.
- `variant_signature` should uniquely encode the mutation or construct difference.
- `mutation_list` and `sequence_delta_signature` should only be filled from already-resolved evidence.
- `construct_type` should come from explicit construct or isoform labels, not inferred names.
- `is_partial` should be true whenever the variant cannot be fully grounded.

### `structure_unit`

Fields added in v2:

- `protein_ref`
- `variant_ref`
- `structure_source`
- `structure_kind`
- `structure_id`
- `model_id`
- `entity_id`
- `chain_id`
- `assembly_id`
- `residue_span_start`
- `residue_span_end`
- `resolution_or_confidence`
- `experimental_or_predicted`
- `mapping_status`
- `structure_relation_notes`

Inheritance from the current schema:

- `summary_id`
- `join_status`
- `join_reason`
- `context`
- `notes`

Population rules:

- `protein_ref` should be projected only through an explicit mapping.
- `variant_ref` should be set only when the structure already resolves to a known variant or construct.
- `structure_id`, `entity_id`, `chain_id`, and `assembly_id` must remain explicit.
- `residue_span_start` and `residue_span_end` should only come from an explicit span projection.
- `experimental_or_predicted` must be explicit and never inferred from a display name.

## Backward Compatibility

- Keep all schema v1 payloads readable.
- Keep existing `protein`, `protein_protein`, and `protein_ligand` records unchanged.
- Do not rename or repurpose current protein fields.
- Do not fold variant-specific differences into `protein_ref`.
- Do not collapse experimental and predicted structure into one record.
- New v2 kinds should be additive rather than overloading the v1 shapes.

## Materialization Rule

The contract follows the existing source-trust posture in the p29 artifacts: source-native truth first, direct evidence before proxy evidence, and no collapse when the claim would become invented rather than resolved.

The practical rule is simple: if the evidence is not already present in the current source set, the record stays partial instead of being guessed.
