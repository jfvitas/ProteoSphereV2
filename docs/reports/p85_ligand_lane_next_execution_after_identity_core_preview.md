# P85 Ligand Lane Next Execution After Identity-Core Preview

## Recommendation

If `ligand_identity_core_materialization_preview` is included in the preview bundle, the next bounded ligand execution step should still be:

- `P00387`
- action: `ingest_local_bulk_assay`

## Why

- The identity-core preview marks `P00387` as `grounded_ready_identity_core_candidate`.
- `Q9NZD4` is still `candidate_bridge_ready_identity_core_candidate` and remains `candidate_only`.
- `P00387` remains the only `bulk_assay_actionable` lane.
- `P00387` still has the strongest grounded ligand evidence:
  - `93` total activities
  - `25` emitted rows
  - `23` distinct ligands in the current payload

Bundle visibility for the identity-core preview changes reporting visibility only. It does not change the safest first execution slice.

## Ordering Context

- Current grounded order remains:
  - `P00387`
  - `Q9NZD4`
- `Q9NZD4` remains the next follow-on after `P00387`, using `1Y01`.
- `P09105` and `Q2TAC2` remain hold-for-acquisition lanes.
- `Q9UCM0` remains deferred.

## Truth Boundary

- Report-only.
- Does not claim ligand rows are materialized.
- Does not claim bundle ligands are included.
- Does not claim packet promotion.
- Does not claim direct structure-backed join certification.
