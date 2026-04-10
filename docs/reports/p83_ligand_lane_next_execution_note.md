# P83 Ligand Lane Next Execution Note

## Recommendation

The next bounded ligand execution step should be `P00387`, specifically `execute_p00387_local_bulk_assay_ingestion`.

## Why `P00387` Is Next

- It is rank `1` in the current ligand pilot ordering.
- It is the only accession currently marked `bulk_assay_actionable`.
- It already has grounded local ChEMBL evidence:
  - target `CHEMBL2146`
  - `93` total activities
  - `25` emitted rows
  - `23` distinct ligands in the current payload
- This is a narrower and safer first execution slice than `Q9NZD4`, because it does not depend on a bridge interpretation step.

## Follow-On Order

- Second step after `P00387`: `Q9NZD4`
  - current status: `rescuable_now`
  - current blocker: `bridge_rescue_not_materialized`
  - grounded bridge: `1Y01` with component `CHK`
- Hold:
  - `P09105`
  - `Q2TAC2`
- Defer:
  - `Q9UCM0`

## Truth Boundary

- This note is report-only.
- It does not claim ligand rows are materialized.
- It does not claim bundle ligand inclusion.
- It does not promote `P09105`, `Q2TAC2`, or `Q9UCM0`.
- It does not claim any new cross-accession or bundle-certified ligand joins.
