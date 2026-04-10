# P65 Structure Follow-Up First Attempt Contract

Report-only contract for the first executable structure materialization order.

## First Attempt Order

1. `P31749`
2. `P04637`

## Why `P31749` First

- Fewer variant-position parse failures than `P04637` (`1` vs `9`)
- Cleaner first anchor for an explicit structure-side record
- The anchor validation already confirms the recommended anchor is present and span-compatible

Recommended anchor:

- `7NH5:A`
- X-ray diffraction
- `1.9 A`
- `0.927` coverage

## Why `P04637` Second

- Broader variant breadth
- Higher follow-up complexity
- Best treated as the second pass after the first attempt is validated

Recommended anchor:

- `9R2Q:K`
- Electron Microscopy
- `3.2 A`
- `1.0` coverage

## Truth Boundary

This contract supports execution order only.

It does **not** claim:

- a direct structure-backed variant join
- a materialized structure-side `variant_ref`
- a promoted `structure_unit` row
- release-grade structural completeness

Both accessions remain `candidate_only_no_variant_anchor` until a structure-side record names one explicit `protein_variant.summary_id` in `variant_ref` and preserves chain-level provenance plus residue-span coverage.

## Operator Read

Use this contract to start the first materialization attempt on `P31749`, then queue `P04637` only after that attempt is validated. If any field is inferred or missing, keep the row candidate-only and do not promote it.
