# P84 Structure Follow-up After Q9NZD4 Bundle

This is a report-only recommendation for the next bounded structure-followup step after the Q9NZD4 bundle context.

## Current Structure-Followup State

- The current candidate accessions are `P04637` and `P31749`.
- Validation is aligned for both rows.
- No direct structure-backed join is certified yet.
- The boundary is still candidate-only.

## Q9NZD4 Context

- The Q9NZD4 bundle context is only contextual for this structure lane.
- It does not change the structure ordering.
- It does not certify a structure-backed join.

## Recommended Next Step

1. `P31749`
   - Materialize the first live preview row for `P31749` with an explicit structure-side `variant_ref`.
   - This remains first because it has the cleaner evidence surface: only 1 variant-position parse failure versus 9 for `P04637`.
   - The recommended anchor is already validated: `7NH5`, chain `A`, X-ray diffraction, `1.9 Å`, `0.927` coverage.

## Secondary Step

- Keep `P04637` queued for the next bounded structure follow-up after `P31749` is materialized and validated.

## Truth Boundary

- This does not certify a direct structure-backed join.
- This does not promote a structure unit row.
- This does not claim release-grade structural completeness.

## Bottom Line

The Q9NZD4 bundle context does not change the structure-only ordering: `P31749` remains the first bounded next step, with `P04637` still queued behind it.
