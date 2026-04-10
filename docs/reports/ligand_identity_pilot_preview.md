# Ligand Identity Pilot Preview

- Status: `complete`
- Active rows: `4`
- Deferred accession: `Q9UCM0`

## Pilot Order

- `1` `P00387` -> `bulk_assay_actionable` then `ingest_local_bulk_assay`
  evidence: `local_chembl_bulk_assay_summary`
- `2` `Q9NZD4` -> `rescuable_now` then `Ingest the local structure bridge for Q9NZD4 using 1Y01`
  evidence: `local_structure_bridge_summary`
- `3` `P09105` -> `structure_companion_only` then `hold_for_ligand_acquisition`
  evidence: `support_only_no_grounded_payload`
- `4` `Q2TAC2` -> `structure_companion_only` then `hold_for_ligand_acquisition`
  evidence: `support_only_no_grounded_payload`

## Truth Boundary

- This is an execution-order preview for the narrow ligand identity pilot. It remains report-only, does not materialize ligand rows, and keeps Q9UCM0 deferred.
