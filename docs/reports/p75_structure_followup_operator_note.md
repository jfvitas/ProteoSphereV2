# P75 Structure Followup Operator Note

This report-only note gives the operator the next truthful read on the two-row structure followup payload preview.

## What Is Preview-Ready

The narrow payload preview is ready as a candidate-only preview surface:

- [artifacts/status/structure_followup_payload_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/structure_followup_payload_preview.json)
- [artifacts/status/structure_followup_anchor_validation.json](/D:/documents/ProteoSphereV2/artifacts/status/structure_followup_anchor_validation.json)
- [artifacts/status/structure_followup_anchor_candidates.json](/D:/documents/ProteoSphereV2/artifacts/status/structure_followup_anchor_candidates.json)

What is grounded:

- two preview rows only
- accessions `P31749` and `P04637`
- real structure anchors and real variant rows
- real residue-span and coverage metadata
- validation status is aligned

## What Is Still Blocked

The surface is still blocked from claiming direct structure-backed promotion:

- `direct_structure_backed_join_certified` is false
- both rows remain `candidate_only`
- both rows explicitly require a structure-side `variant_ref` before promotion
- the preview is not yet a certified direct structure-backed join

## Operator Truth

The right operator read is:

- preview-ready: yes
- direct promotion: no
- certified structure-backed join: no
- candidate-only followup payload: yes

## Low-Risk Next Improvements

- Keep the two-row preview as a narrow candidate surface until a structure-side `variant_ref` is materialized explicitly.
- Preserve the current span and coverage metadata, since they are already internally aligned.
- Promote only one accession at a time when the next structure-side bridge is ready.
- Keep the candidate-only wording visible until certification is real.

## Truth-Boundary Caution

This preview uses real raw structure evidence and real variant library rows, but it still does not certify a direct structure-backed variant join. It is a followup candidate surface, not a promoted structure unit.

## Bottom Line

The two-row structure followup payload preview is trustworthy as a candidate-only operator surface. It is not yet trustworthy as a certified structure-backed join.
