# p81 Split Lane Readiness After Ligand Family

This note answers a narrow question: would adding a ligand identity pilot preview family change any split or leakage claims today?

## Answer

No.

The current split and leakage claims stay unchanged today because:

- the split candidate preview still contains 1889 `entity_signature_row` entries,
- the split recipe still allows only `protein`, `protein_variant`, and `structure_unit`,
- `ligand_identity_group` and `binding_context_group` remain reserved null axes,
- the simulation preview explicitly says ligand rows are not materialized yet,
- the leakage preview still says `ligand_overlap_materialized=false`.

## Current Live Split State

- Candidate rows: `1889`
- Primary hard group: `protein_spine_group`
- Reserved null axes: `ligand_identity_group`, `binding_context_group`
- Simulation split counts: `train=1440`, `val=266`, `test=183`
- Simulation rejected count: `0`

Current leakage classes still show:

- `candidate_overlap`: `2`
- `structure_followup`: `2`
- `protein_only`: `7`

## Ligand Pilot State

The ligand pilot preview is still report-only and still has no materialized ligand rows.

It surfaces the ordered accessions:

1. `P00387`
2. `Q9NZD4`
3. `P09105`
4. `Q2TAC2`

with `Q9UCM0` deferred.

## Truth Boundary

- report-only
- no ligand row materialization
- no split or leakage claim change today
- no fold-export unlock

## Risks

- Do not summarize the ligand pilot preview as if it were a materialized ligand family in the split engine.
- Do not claim a new leakage class unless ligand overlap is actually materialized and reflected in the leakage preview.
- Do not infer fold-export readiness from the ligand preview.

## Bottom Line

Adding the ligand identity pilot preview family does not change split or leakage claims today. The live split and leakage previews still operate on protein, protein_variant, and structure_unit rows only, with ligand axes reserved and ligand rows not materialized.
