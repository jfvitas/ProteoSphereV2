# p82 Split Lane After Dual Ligand Validation

This note answers a narrow question: would having both `P00387` and `Q9NZD4` validation previews change split claims today?

## Answer

No.

Even if both ligand validation previews were present and aligned, the current split claims would not change today because the split engine still only operates on `protein`, `protein_variant`, and `structure_unit` rows.

The ligand axes remain reserved and the ligand family is still not materialized.

## Why The Split Claims Stay The Same

- The split candidate preview still covers 1889 rows across `protein`, `protein_variant`, and `structure_unit` only.
- The split recipe still keeps `ligand_identity_group` and `binding_context_group` as reserved null axes.
- The split simulation explicitly says ligand rows are not materialized yet.
- The leakage preview still shows `ligand_overlap_materialized=false`.
- The existing `P00387` validation preview only certifies fresh-run evidence shape and does not claim canonical ligand materialization or packet promotion.

## Current Live State

- Candidate rows: `1889`
- Primary hard group: `protein_spine_group`
- Reserved null axes: `ligand_identity_group`, `binding_context_group`
- Simulation split counts: `train=1440`, `val=266`, `test=183`
- Simulation rejected count: `0`

Current leakage classes still show:

- `candidate_overlap`: `2`
- `structure_followup`: `2`
- `protein_only`: `7`

## Ligand Validation State

The live ligand pilot preview already orders:

1. `P00387`
2. `Q9NZD4`
3. `P09105`
4. `Q2TAC2`

with `Q9UCM0` deferred.

Today, the `P00387` validation preview exists and is aligned. There is no live `Q9NZD4` validation preview yet, but even if one were added, it would still not change split or leakage claims without actual ligand row materialization.

## Truth Boundary

- report-only
- no ligand row materialization
- no split or leakage claim change today
- no fold-export unlock

## Risks

- Do not summarize the ligand validation previews as if they expanded the split candidate families.
- Do not claim a new leakage class unless ligand overlap is actually materialized and reflected in the leakage preview.
- Do not infer fold-export readiness from validation previews alone.

## Bottom Line

Even with both `P00387` and `Q9NZD4` validation previews, split claims would not change today. The split engine still sees protein, protein_variant, and structure_unit rows only, ligand axes remain reserved, and ligand rows are still unmaterialized.
