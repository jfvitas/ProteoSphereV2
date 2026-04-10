Date: 2026-03-22

# Provenance Integrity Notes

## Scope

Validated the canonical pipeline's lineage behavior across sequence, structure, assay, and final assembly steps.

## What Was Checked

- Sequence provenance records are retained and threaded into structure ingest as explicit parent IDs.
- Structure ingest preserves unresolved references and conflicts instead of collapsing them.
- Assay ingest preserves provenance on the resolved path and exposes unresolved ligand cases explicitly.
- Pipeline checkpoints capture node execution order, completed nodes, and run metadata.

## Outcome

The resolved path stayed fully traceable from source ingest to canonical outputs. A mixed input path also preserved the unresolved structure and assay cases without flattening them into a generic success state.

## Verification

- Focused integration test: `tests/integration/test_provenance_integrity.py`
- Focused Ruff check: `tests/integration/test_provenance_integrity.py`
