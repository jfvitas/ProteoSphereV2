# Structure Follow-up Payload Expansion Contract

## Summary
The next safe payload expansion after the current P31749-only preview is a two-row candidate-only bridge for `P68871` and `P69905`.
That keeps the slice conservative: it expands the existing follow-up surface, but it still does not certify a direct structure-backed variant join.

## Grounding
This contract is grounded in:
- `artifacts/status/structure_followup_payload_preview.json`
- `artifacts/status/structure_followup_anchor_candidates.json`
- `artifacts/status/structure_followup_anchor_validation.json`
- `artifacts/status/structure_variant_bridge_summary.json`
- `artifacts/status/structure_variant_candidate_map.json`
- `artifacts/status/p72_ligand_similarity_signature_implementation_contract.json`

## Next Safe Expansion
- Target surface: `structure_variant_candidate_map`
- Rank: `1`
- Expected next accessions: `P68871`, `P69905`
- Size risk: `low_to_moderate`

Why this is next:
- The current preview already proves the narrow candidate-only pattern on `P31749`.
- The bridge summary shows accession-level overlap for `P68871` and `P69905`.
- The candidate map confirms the structure side still lacks explicit `variant_ref`, so the truthful next step is to expand the candidate-only payload, not to promote a direct join.

## Payload Contract
The expanded slice should preserve:
- `candidate_only_status = candidate_only_no_variant_anchor`
- `join_status = candidate_only`
- `direct_structure_backed_variant_join_materialized = false`
- `ready_for_preview_validation = true`

The expanded slice should add:
- one row for `P68871`
- one row for `P69905`

The minimum row fields remain:
- accession
- protein_ref
- variant_ref
- protein_variant.summary_id
- structure_id
- chain_id
- residue_span_start
- residue_span_end
- uniprot_span
- coverage
- experimental_method
- resolution_angstrom
- source_artifact_ids
- candidate_only_status
- join_status
- join_reason
- truth_note

## Truth Boundary
This is a report-only contract.
It does not certify direct structure-backed joins, and it does not expand beyond the exact overlap currently reported by the anchor and candidate surfaces.
