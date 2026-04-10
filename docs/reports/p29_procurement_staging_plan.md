# P29 Procurement Staging Plan

- Generated at: `2026-03-30T00:49:28.4244984-05:00`
- Staging file: [`artifacts/status/p29_procurement_staging_plan.json`](/D:/documents/ProteoSphereV2/artifacts/status/p29_procurement_staging_plan.json)

## What Is In Flight

- `BioGRID`, `STRING`, `AlphaFold DB`, `IntAct`, and `BindingDB` are already in the live download wave.
- These should be treated as in-flight, not requeued.

## Immediate Local Copy

- `PROSITE` should be copied from the promoted bio-agent-lab mirror.
- This is the cheapest way to fill the motif lane without paying another download cost.

## Next Guarded Downloads

- `ELM` comes next for motif breadth.
- `SABIO-RK` follows to fill the missing metadata lane.
- `Q9UCM0` AlphaFold probing follows as the next structure-specific download.

## Deferred Oversized Or Fan-Out Work

- `UniProt` TrEMBL stays lazy so the reviewed Swiss-Prot spine is not disturbed.
- `Q9UCM0` PPI validation should be indexed only, because it depends on the curated PPI pulls that are already underway.
- The ligand rescue bundle for `P00387`, `P09105`, `Q2TAC2`, and `Q9NZD4` should also stay indexed only, since it fans out across sources that are already present locally.
- `Mega Motif Base` and `Motivated Proteins` stay deferred because they are lower-yield motif fan-out sources.

## Readout

The staging plan is intentionally simple: keep the current live procurement wave moving, take the local-copy win on `PROSITE`, then queue the next guarded downloads only after the current wave has stabilized. The oversized fan-out items are left deferred so they do not steal cycles from the missing interaction, motif, and structure gaps.
