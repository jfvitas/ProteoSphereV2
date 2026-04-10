# P29 Summary Library V2 Bridge

This report maps the current schema in [core/library/summary_record.py](../../core/library/summary_record.py) to the first implementable v2 additions.

## Baseline

The current library schema is still v1 and only defines three top-level record kinds:

- `protein`
- `protein_protein`
- `protein_ligand`

Shared record context already covers provenance, cross references, motif/domain/pathway references, source rollups, source connections, and storage/lazy guidance.

## First V2 Additions

### `protein_variant`

Purpose: represent wild-type, engineered, isoform, truncation, and point-mutant variants without collapsing them into the protein spine.

Fields to add:

- `protein_ref`
- `parent_protein_ref`
- `variant_signature`
- `variant_kind`
- `mutation_list`
- `sequence_delta_signature`
- `construct_type`
- `is_partial`
- `variant_relation_notes`

Inherited baseline fields:

- `summary_id`
- `join_status`
- `join_reason`
- `context`
- `notes`

### `structure_unit`

Purpose: distinguish experimental and predicted structures while preserving chain, entity, assembly, and span lineage.

Fields to add:

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

Inherited baseline fields:

- `summary_id`
- `join_status`
- `join_reason`
- `context`
- `notes`

## Backward Compatibility

- Keep existing `protein`, `protein_protein`, and `protein_ligand` records unchanged.
- Do not rename or repurpose current protein fields.
- Do not fold variant-specific differences into `protein_ref`.
- Do not collapse experimental and predicted structure into one shape.
- Existing schema v1 payloads must remain readable.

## Implementation Order

1. Extend schema dataclasses and serializers for the new record kinds.
2. Add round-trip tests for the new record families.
3. Wire materialization and builder support after the schema contract is stable.

The report is intentionally additive-only. It is a bridge from the current schema to the first v2 additions, not a full schema redesign.
