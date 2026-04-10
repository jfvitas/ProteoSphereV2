# Structure Follow-up Next Single Accession Plan

## Summary
The next single accession to promote, while staying candidate-only, is `P31749`.
`P04637` remains deferred for the next step.

## Grounding
This plan is grounded in:
- `artifacts/status/structure_followup_payload_preview.json`
- `artifacts/status/structure_followup_anchor_validation.json`
- `artifacts/status/structure_followup_anchor_candidates.json`
- `artifacts/status/p75_structure_followup_operator_note.json`

## Why `P31749` Next
`P31749` is the cleaner one-row promotion target for a single-accession step:
- It already has an explicit structure-side `variant_ref` in the preview row.
- Anchor validation is aligned.
- The variant positions sit within the recommended span.
- It has fewer parse failures than `P04637`, so it is the narrower and more conservative move.

Promotion target details:
- Access accession: `P31749`
- Structure: `7NH5:A`
- Coverage: `0.927`
- Experimental method: `X-ray diffraction`
- Resolution: `1.9 Å`

## Deferred Accessions
`P04637` stays deferred for the next step.
It is still validated and candidate-only, but this plan keeps the promotion to a single accession.

Deferred target details:
- Access accession: `P04637`
- Structure: `9R2Q:K`
- Coverage: `1.0`
- Experimental method: `Electron Microscopy`
- Resolution: `3.2 Å`

## Truth Boundary
This is a report-only plan.
It does not certify a direct structure-backed join and it does not expand beyond one accession.
