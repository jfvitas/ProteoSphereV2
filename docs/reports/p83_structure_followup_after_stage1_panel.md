# P83 Structure Follow-up After Stage1 Panel

This is a report-only recommendation for the next bounded structure-followup step after the new stage1 ligand panel.

## Current Structure-Followup State

- The current candidate accessions are `P04637` and `P31749`.
- Validation is aligned for both rows.
- No direct structure-backed join is certified yet.
- The boundary is still candidate-only.

## Recommended Next Step

1. `P31749`
   - Materialize the first live preview row for `P31749` with an explicit structure-side `variant_ref`.
   - This is first because it has the cleaner evidence surface: only 1 variant-position parse failure versus 9 for `P04637`.
   - The recommended anchor is already validated: `7NH5`, chain `A`, X-ray diffraction, `1.9 Å`, `0.927` coverage.

## Required Preview Fields

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

## Secondary Step

- Keep `P04637` queued for the next bounded structure follow-up after `P31749` is materialized and validated.

## Truth Boundary

- This does not certify a direct structure-backed join.
- This does not promote a structure unit row.
- This does not claim release-grade structural completeness.

## Bottom Line

The next bounded structure-followup step is `P31749` first, with an explicit structure-side `variant_ref`, while `P04637` stays queued and the candidate-only boundary stays intact.
