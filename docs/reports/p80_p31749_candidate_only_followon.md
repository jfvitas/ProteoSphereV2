# p80 P31749 Candidate-Only Follow-On

This report-only note keeps the narrow structure follow-up on `P31749` and leaves `P04637` deferred. The safest next follow-on is a single-accession candidate-only hold for operator steering, not a direct-join certification.

Grounding sources:
- `D:/documents/ProteoSphereV2/artifacts/status/structure_followup_single_accession_preview.json`
- `D:/documents/ProteoSphereV2/artifacts/status/structure_followup_single_accession_validation_preview.json`
- `D:/documents/ProteoSphereV2/artifacts/status/p79_structure_single_validation_next_step.json`
- `D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/operator_dashboard.json`

Recommendation:
- Keep `P31749` as the only selected accession.
- Keep `P04637` deferred.
- Preserve the existing candidate-only boundary and do not certify a direct structure-backed join.
- Do not widen into ligands, interactions, or additional accessions yet.

Why this is the safest follow-on:
- The single-accession preview and validation previews are aligned.
- `P31749` already has an explicit structure-side `variant_ref`, which makes it the narrowest truthful follow-on.
- The operator dashboard is still release-blocked, so the next step must remain adjacent and non-certifying.

Operator boundary:
- This is report-only.
- The direct join remains uncertified.
- The follow-on is meant for steering, not promotion.
