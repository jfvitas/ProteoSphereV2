# P64 Structure Follow-Up Execution Handoff

Report-only handoff for the first structure follow-up materialization attempt.

## Handoff Summary

Start with `P31749`.

Keep `P04637` queued as the secondary follow-up.

This is still a candidate-only handoff, not a direct-join claim.

## Why `P31749` First

- Fewer variant-position parse failures than `P04637` (`1` vs `9`)
- Cleaner recommended anchor: `7NH5:A`
- Higher-resolution experimental anchor: `1.9 Å`
- Current validation already confirms the anchor is present and span-compatible

## First Attempt Plan

1. Materialize the `P31749` structure-side row with an explicit `variant_ref`.
2. Preserve chain provenance and residue-span coverage in the row.
3. Re-run the structure follow-up validation gates.
4. Keep the row candidate-only if any field is inferred or missing.
5. Queue `P04637` only after the `P31749` attempt is validated.

## Required Truth Boundary

The current artifacts support an execution attempt, but they do not certify a direct structure-backed join.

What is true now:

- both rows are candidate-only
- the candidate surface is internally consistent
- the recommended anchors are present in the best-target lists

What is not true yet:

- a direct structure-backed variant join
- a promoted `structure_unit` row
- a materialized structure-side `variant_ref`
- release-grade structural completeness

## Operator Read

Treat this as the execution handoff for the first materialization pass:

- attempt `P31749` first
- keep `P04637` as the next step
- do not present either row as a completed join until a structure-side `variant_ref` exists explicitly
