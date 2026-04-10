# P72 Structure-Followup Next Safe Implementation Order

## Objective

Define the next safe implementation order for expanding beyond the current `P31749` structure-followup preview without overstating direct joins.

Grounding:

- [structure_followup_payload_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/structure_followup_payload_preview.json)
- [structure_followup_anchor_candidates.json](/D:/documents/ProteoSphereV2/artifacts/status/structure_followup_anchor_candidates.json)
- [structure_followup_anchor_validation.json](/D:/documents/ProteoSphereV2/artifacts/status/structure_followup_anchor_validation.json)
- [p70_structure_followup_payload_impl_order.json](/D:/documents/ProteoSphereV2/artifacts/status/p70_structure_followup_payload_impl_order.json)
- [structure_variant_candidate_map.json](/D:/documents/ProteoSphereV2/artifacts/status/structure_variant_candidate_map.json)

## Current State

The live preview is currently narrow and controlled:

- one payload row
- accession: `P31749`
- anchor: `7NH5:A`
- explicit `variant_ref = protein_variant:protein:P31749:K14Q`
- `join_status = candidate_only`
- `candidate_only_status = candidate_only_no_variant_anchor`

That current row is useful because it proves the payload shape can be emitted while still keeping the truth boundary explicit.

It does not prove:

- a certified direct structure-backed join
- a promoted structure-unit interpretation
- a wider multi-accession preview

## Safe Expansion Order

### 1. Keep `P31749` fixed as the baseline

Do not reinterpret the current row while expanding.

Preserve:

- `payload_row_count = 1` until the next accession is separately validated
- `join_status = candidate_only`
- `candidate_only_status = candidate_only_no_variant_anchor`
- the current truth note

This row is the baseline control surface, not a promotion candidate.

### 2. Use `P04637` as the next narrow payload candidate

`P04637` is the safest next row because it is already present in both anchor surfaces.

Recommended anchor from the current candidate surface:

- `structure_id = 9R2Q`
- `chain_id = K`
- `experimental_method = Electron Microscopy`
- `resolution = 3.2`
- `coverage = 1.0`
- `uniprot_span = 1-393`

Candidate variant anchors already listed:

- `Q5H`
- `S6L`
- `D7H`
- `P8S`
- `V10I`

That is enough to add a second candidate-only row.

It is not enough to claim certification.

### 3. Add `P04637` only if it matches the existing payload schema exactly

The second row should use the same executable field shape as the current `P31749` row:

- `accession`
- `protein_ref`
- `variant_ref`
- `protein_variant.summary_id`
- `structure_id`
- `chain_id`
- `residue_span_start`
- `residue_span_end`
- `uniprot_span`
- `coverage`
- `experimental_method`
- `resolution_angstrom`
- `source_artifact_ids`
- `candidate_only_status`
- `join_status`
- `join_reason`
- `truth_note`

After this step, the preview should have exactly two rows:

- `P31749`
- `P04637`

Both rows must still be candidate-only.

### 4. Keep `P68871` and `P69905` out of the payload preview

They are not the next safe step.

Reason:

- [structure_variant_candidate_map.json](/D:/documents/ProteoSphereV2/artifacts/status/structure_variant_candidate_map.json) still shows:
  - `candidate_only_no_variant_anchor`
  - `variant_refs_on_structure_side = []`

That means those rows are still accession-overlap candidates only.

They should stay in candidate-map surfaces, not payload preview surfaces.

### 5. Require explicit structure-side evidence before any promotion

Once the preview has more than one row, the risk of misreading it increases.

Promotion must still depend on row-level evidence only:

- explicit structure-side `variant_ref`
- row-specific validation
- row-specific truth-note update

Never promote based on:

- shared accession
- residue-span compatibility alone
- family membership
- presence in `best_experimental_targets`

## Next Safe Target

The next safe target is:

- `P04637`

Why:

- it is already validated as an anchor candidate
- it has a recommended experimental anchor
- it has span-compatible candidate variants
- it can be added without widening the join claim

## Explicit Deferrals

Defer:

- `P68871`
- `P69905`

Reason:

- both remain `candidate_only_no_variant_anchor`
- both still have empty `variant_refs_on_structure_side`
- adding them to preview now would overstate join certainty

## Unsafe Moves

Avoid:

- promoting `P31749` because a preview row exists
- adding `P68871` or `P69905` to the payload preview now
- treating accession overlap as a direct structure-backed variant join
- strengthening `join_reason` before certification exists
- widening the next step beyond two narrow candidate-only rows

## Bottom Line

The next safe expansion is one additional narrow `P04637` candidate-only payload row beside the current `P31749` row. `P68871` and `P69905` should remain in candidate-only mapping surfaces until they have explicit structure-side variant anchors.
