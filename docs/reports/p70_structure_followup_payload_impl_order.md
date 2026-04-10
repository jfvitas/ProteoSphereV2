# P70 Structure Follow-Up Payload Implementation Order

Report-only implementation order for turning the `P31749` payload schema into a live preview surface.

## Target

- Accession: `P31749`
- Status: `candidate_only_no_variant_anchor`
- Recommended anchor: `7NH5:A`
- Method: X-ray diffraction
- Resolution: `1.9 A`

## Implementation Order

1. Emit the payload row in the exact p69 field order.
2. Set the first preview row to `P31749` with the recommended anchor values.
3. Preserve the candidate-only truth markers in the preview output.
4. Run the current validation gates against the preview surface.
5. Keep `P04637` and any broader payloads deferred.

## Preview Rules

The live preview surface should:

- expose the exact payload fields from p69
- stay readable as candidate-only, not promoted
- avoid inventing extra join or promotion fields
- stay separate from protected latest surfaces

## Truth Boundary

This is an implementation order, not a join claim.

The preview may be shown as aligned only if it still preserves:

- `candidate_only_status = candidate_only_no_variant_anchor`
- `join_status = candidate_only`
- a truth note that says the join is not certified

It must not claim:

- a direct structure-backed join
- a promoted `structure_unit` row
- release readiness

## Operator Read

Use this order to bring up the first live preview surface for `P31749` and nothing broader. If the preview cannot keep the candidate-only markers intact, stop before promotion and keep the row queued.
