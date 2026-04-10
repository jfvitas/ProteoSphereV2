# P61 Structure Follow-Up Candidate Review

Report-only truth-boundary review for `structure_followup_anchor_candidates`.

## What This Enables Now

- It gives a real shortlist of structure-backed follow-up candidates.
- It pairs each accession with an experimental anchor, AlphaFold evidence, and a small set of residue-span-compatible variant anchors.
- It can drive the next materialization step for structure-side linking without inventing a join that is not present yet.

## What It Still Cannot Claim

- It does not claim a direct structure-backed variant join.
- It does not claim a structure-side `variant_ref` is already materialized.
- It does not claim completed structure-unit rows for either accession.
- It does not claim release-grade structural completeness.

Both rows still sit in `candidate_only_no_variant_anchor` status, so this is a prioritization surface, not a finished structure bridge.

## Which Accession Should Be Materialized First

`P31749` should be materialized first.

Why:

- It has fewer variant-position parse failures than `P04637` (`1` vs `9`).
- Its recommended experimental anchor is a higher-resolution X-ray structure: `7NH5:A` at `1.9 Å`.
- The structure evidence is cleaner for a first execution pass.

`P04637` is still a strong follow-up target, especially because it carries much broader variant breadth and full-coverage EM evidence, but it is the heavier second step.

## Operator Read

Treat this artifact as a queue for the next structure materialization decision, not as proof that the joins already exist. The safe interpretation is:

- `P31749` first
- `P04637` second
- no direct structure-backed variant join yet

## Truth Boundary

- This surface uses real raw structure evidence.
- This surface uses real variant library rows.
- This surface remains report-only until a structure-side `variant_ref` is explicitly materialized.
