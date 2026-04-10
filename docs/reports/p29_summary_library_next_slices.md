# P29 Summary Library Next Slices

This slice refines the current summary-library plan into the next executable units.

## Execution Shape

- Root slice: `schema_v2`
- Parallel follow-ups after the schema contract is stable:
  - `variant_structure_unit`
  - `similarity_leakage_scaffolding`

## Next Slices

### `schema_v2`

- Goal: extend the summary schema with structure, variant, pathway, provenance, and explicit similarity/leakage attachment shapes.
- Primary files: `core/library/summary_record.py`, `core/storage/planning_index_schema.py`, `execution/library/build_summary_library.py`, `tests/unit/core/test_summary_record.py`, `tests/unit/execution/test_build_summary_library.py`
- Acceptance:
  - new record families round-trip through `to_dict` and `from_dict`
  - mixed-library serialization keeps record kinds distinct
  - existing protein, pair, and ligand behavior stays stable

### `variant_structure_unit`

- Goal: materialize variant and structure-unit records on the new schema spine.
- Primary files: `execution/library/protein_summary_materializer.py`, `execution/library/build_summary_library.py`, `core/library/summary_record.py`, `tests/unit/execution/test_protein_summary_materializer.py`
- Acceptance:
  - variant records keep parent accession and mutation signature explicit
  - structure-unit records keep source, entity, chain, assembly, and residue span explicit
  - experimental and predicted structure stay separate

### `similarity_leakage_scaffolding`

- Goal: emit compact similarity signatures and leakage-group scaffolding for split governance.
- Primary files: `execution/library/similarity_signature_materializer.py`, `datasets/splits/locked_split.py`, `scripts/emit_leakage_audit.py`, `tests/unit/datasets/test_locked_split.py`
- Acceptance:
  - signatures are compact and queryable
  - leakage groups separate exact entity, family, and context proximity
  - split audit consumes the new labels without weakening fail-closed behavior

## Recommended Order

1. `schema_v2`
2. `variant_structure_unit`
3. `similarity_leakage_scaffolding`

The second and third slices can run in parallel once the schema v2 contract is settled.
