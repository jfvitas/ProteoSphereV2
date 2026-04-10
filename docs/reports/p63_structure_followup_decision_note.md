# P63 Structure Follow-Up Decision Note

Report-only decision note comparing `P04637` and `P31749` as the next structure follow-up materialization target.

## Decision

`P31749` should be materialized first.

`P04637` stays the stronger follow-up after that.

## Why `P31749` First

- Fewer variant-position parse failures: `1` versus `9` for `P04637`
- Cleaner recommended anchor: `7NH5:A`, X-ray diffraction, `1.9 Å`, `0.927` coverage
- Smaller and simpler candidate surface for the first explicit structure-side anchor

## Why `P04637` Second

- Much broader variant breadth: `1439` variants versus `23` for `P31749`
- Full-coverage experimental anchor: `9R2Q:K`, Electron Microscopy, `3.2 Å`, `1.0` coverage
- Strong follow-up target, but heavier than the first materialization pass

## What The Validation Actually Says

The current anchor validation confirms only that the candidate surface is internally consistent:

- both rows are present
- both recommended anchors are present in the best-target lists
- both variant spans fit the anchor spans

That validation does **not** certify a direct structure-backed join.

## Truth Boundary

This note can support a queueing decision, not a join claim.

It can say:

- `P31749` is the first target
- `P04637` is the second target
- both rows remain `candidate_only_no_variant_anchor`

It cannot say:

- a direct structure-backed variant join already exists
- a structure-side `variant_ref` is already materialized
- either row is a promoted `structure_unit` record

## Operator Read

Use this note as the decision boundary for the next structure materialization pass:

1. Materialize `P31749` first.
2. Keep `P04637` queued as the next follow-up.
3. Do not treat either candidate as a completed join until a structure-side `variant_ref` is written explicitly.
