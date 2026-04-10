# Structure Single Validation Next Step

## Summary
The new single-accession validation preview is aligned.
`P31749` stays selected, `P04637` stays deferred, and direct join certification remains blocked.

## Grounding
This note is grounded in:
- `artifacts/status/structure_followup_single_accession_preview.json`
- `artifacts/status/structure_followup_single_accession_validation_preview.json`
- `artifacts/status/structure_followup_anchor_validation.json`
- `runs/real_data_benchmark/full_results/operator_dashboard.json`

## Current State
- Selected accession: `P31749`
- Deferred accession: `P04637`
- Payload row count: `1`
- Scope: `single_accession_scope = true`
- Candidate-only boundary: `true`
- Direct structure-backed join certified: `false`
- Validation status: `aligned`

The validation preview confirms both accessions remain internally consistent with their recommended anchors:
- `P31749` -> `7NH5:A`
- `P04637` -> `9R2Q:K`

## Operator Dashboard Context
The broader operator dashboard is still `blocked_on_release_grade_bar`.
That means this next-step note stays narrow and adjacent, not release-grade.

## Next Safe Structure-Adjacent Step
The next safe adjacent step is still the single-accession candidate-only promotion path:
- Keep `P31749` selected
- Keep `P04637` deferred
- Do not certify the direct structure-backed join yet

Why:
- the preview and validation previews are aligned
- the selected accession already has an explicit structure-side `variant_ref`
- the direct join boundary remains blocked, so the next step must remain candidate-only

## Truth Boundary
This is a report-only note.
It confirms the next structure-adjacent step without certifying a direct structure-backed join.
