# P67 Structure Follow-Up Schema Review

Report-only review of whether the minimum structure follow-up materialization schema is sufficient for a first executable artifact.

## Verdict

Yes, for the first executable payload.

No, for join certification or promotion on its own.

The schema is sufficient to express the first materialized anchor row, but it still depends on the execution and validation layers to keep the candidate-only boundary intact.

## Why It Is Sufficient

The minimum schema already carries everything the first attempt needs:

- accession and protein reference
- explicit `variant_ref` / `protein_variant.summary_id`
- structure ID and chain ID
- residue span and coverage
- experimental context
- provenance and truth markers

That matches the first-attempt contract, which asks for an explicit variant anchor plus explicit structure identity and span.

## Why It Still Cannot Claim More

The validation artifact only checks internal consistency of the candidate surface. It does not certify a direct structure-backed join.

So the schema is enough to write a first row, but not enough to say that the row is promoted, joined, or release-ready.

## What To Watch

The one readability risk is `candidate_only_status`.

That field is useful because it keeps the truth boundary explicit, but it can also be misread as a permanent status if the schema is reused later. For the current first attempt, that is acceptable and still minimal.

## Operator Read

Use the schema as-is for the first `P31749` materialization attempt. Keep promotion logic in the executor and validation layers, not inside the payload schema.

## Truth Boundary

This review is report-only. It confirms the schema is sufficient for a first executable payload, but it does not certify a direct structure-backed join or a promoted `structure_unit` row.
