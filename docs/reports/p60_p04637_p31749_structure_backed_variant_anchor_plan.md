# P60 P04637 P31749 Structure Backed Variant Anchor Plan

Report-only next truthful anchor plan for `P04637` and `P31749` using the current variant library and local structure evidence.

## Truth Boundary

- This note is report-only.
- It does not authorize code changes or publication.
- It checks the current variant and structure surfaces and proposes the next explicit anchor required before a direct structure-backed join is allowed.

## Current State

The variant side is already strong:

- `P04637` has `1439` materialized protein_variant rows.
- `P31749` has `23` materialized protein_variant rows.

The structure evidence is also local and supportive:

- `P04637` points to `9R2Q` with chains `K`, `L`, `M`, and `N`.
- `P31749` points to `7NH5` with chain `A`.

But the current structure-unit library still has no materialized rows for either accession, and no structure-side row names a `variant_ref`.

## Exact Missing Anchor

The missing explicit anchor is not more variant evidence. It is a structure-side record that explicitly sets:

- `variant_ref`
- `protein_ref`
- `structure_id`
- `chain_id`
- `residue_span_start`
- `residue_span_end`

Until that exists, a direct structure-backed variant join is not truthful.

## Proposed Rules

1. Require an exact accession match between the variant row and the structure row.
2. Require `variant_ref` to be explicit on the structure side.
3. Bind one structure anchor to one explicit `variant_signature`.
4. Require the structure-unit residue span to cover the claimed variant residue.
5. Keep `P04637` and `P31749` in `candidate_only` state until the structure-side anchor exists.

## Accessions

### P04637

- Variant support: `1439` rows
- Best local structure target: `9R2Q`
- Candidate chains: `K`, `L`, `M`, `N`
- Missing anchor: structure-side `variant_ref` to one explicit `P04637` protein_variant summary id

### P31749

- Variant support: `23` rows
- Best local structure target: `7NH5`
- Candidate chain: `A`
- Missing anchor: structure-side `variant_ref` to one explicit `P31749` protein_variant summary id

## Operator Labels

Allowed now:

- `protein_variant_anchor_present`
- `local_structure_evidence_present`
- `candidate_only`

Not allowed now:

- `direct_structure_backed_variant_join`
- `variant_ref_inferred`
- `name_only_mapping`

## Bottom Line

`P04637` and `P31749` are the right next structure-backed variant candidates, but the direct join is still blocked until the structure side emits an explicit `variant_ref` for one chosen variant signature on each accession.
