# P84 Ligand Lane Next Execution After Q9NZD4 Bundle Note

## Recommendation

If `q9nzd4_bridge_validation_preview` is included in the preview bundle, the next bounded ligand execution step should be:

- `Q9NZD4`
- action: `ingest_local_structure_bridge_using_1Y01`

## Why

- The current `Q9NZD4` bridge validation preview is already `aligned`.
- Its explicit best next action is to ingest the local structure bridge using `1Y01`.
- The lane is already classified as `rescuable_now`.
- Bundle visibility for the validation preview reduces reporting uncertainty, but it does not itself materialize the bridge or ligand rows.
- `P09105` and `Q2TAC2` still have no grounded local ligand payloads, so they remain weaker follow-on lanes.

## Ordering Context

- `P83` still stands as the broader lane order:
  - `P00387` first
  - `Q9NZD4` second
- This note is narrower:
  - once the `Q9NZD4` bridge-validation preview is bundle-visible, the next bounded step for that branch is the bridge ingestion itself.

## Hold and Defer

- Hold:
  - `P09105`
  - `Q2TAC2`
- Defer:
  - `Q9UCM0`

## Truth Boundary

- Report-only.
- Does not claim ligand rows are materialized.
- Does not claim bundle ligands are included.
- Does not claim packet promotion.
- Does not claim direct structure-backed join certification.
