# Index Rebuild Notes

## Scope

Validated the landed planning-index rebuild flow against the runtime and indexing stack using a real ingest result from sequence observations.

## Input Shape

- Sequence ingest records:
  - `P12345` observed twice with different metadata to force an ambiguous join state
  - `Q99999` observed once to produce a resolved join state
- Rebuild target:
  - `build_protein_planning_index(...)`
- Runtime target:
  - `integrate_storage_runtime(...)`

The rebuilt planning index therefore carried two real planning rows:

- `protein:P12345` with `join_status="ambiguous"`
- `protein:Q99999` with `join_status="joined"`

## Commands Run

```powershell
python -m pytest tests\integration\test_index_rebuild.py tests\integration\test_storage_runtime.py
python -m ruff check tests\integration\test_index_rebuild.py
```

## What Succeeded

- Planning-index rebuild was deterministic across a round-trip through `PlanningIndexSchema.to_dict()` and `PlanningIndexSchema.from_dict()`.
- Join state survived rebuild intact:
  - `protein:P12345` stayed `ambiguous`
  - `protein:Q99999` stayed `joined`
- Storage runtime integrated cleanly when the full rebuilt planning index was present.

## Missing-Input Behavior

- When the rebuilt planning index was stripped down to only `protein:Q99999`, the storage runtime returned `partial`.
- The runtime emitted a `missing_planning_index_entry` issue for `example-p12345`.

## Implication For The Next Wave

- The rebuild path is stable enough to use as the planning-index baseline.
- The next work should focus on broader source coverage and any runtime cases where a selected example depends on a planning row that is not yet rebuilt.
- No code changes were required for this validation pass; the landed stack already preserves deterministic rebuilds and surfaces missing planning inputs explicitly.
