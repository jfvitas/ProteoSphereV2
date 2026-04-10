# P68 Structure Follow-Up First Payload Plan

Report-only plan for the first executable payload on `P31749`.

## Payload Target

- Accession: `P31749`
- Current status: `candidate_only_no_variant_anchor`
- Recommended anchor: `7NH5:A`
- Method: X-ray diffraction
- Resolution: `1.9 A`
- Coverage: `0.927`

## Minimum Payload Shape

The first executable payload needs only the fields required to identify one explicit structure-side record and one explicit variant anchor:

- accession
- protein reference
- `variant_ref`
- one explicit `protein_variant.summary_id`
- structure ID
- chain ID
- residue span
- UniProt span and coverage
- experimental context
- source artifact IDs
- candidate-only status
- join status, join reason, and truth note

## Execution Steps

1. Emit one structure-side row for `P31749` with the recommended anchor and one explicit `variant_ref`.
2. Keep the row candidate-only until that variant reference is explicit.
3. Run the current validation gates before any broader publication step.

## Truth Boundary

This is the first executable payload, not a certified join.

It can support a first materialized anchor row, but it cannot claim:

- a direct structure-backed variant join
- a promoted `structure_unit` row
- release-grade completeness

## Operator Read

Use this plan as the narrowest possible first payload for `P31749`. If the row cannot carry an explicit `variant_ref`, keep it candidate-only and do not promote it.
