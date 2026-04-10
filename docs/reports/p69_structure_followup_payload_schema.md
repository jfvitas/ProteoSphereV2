# P69 Structure Follow-Up Payload Schema

Report-only executable payload schema for the first narrow structure follow-up payload.

## Scope

- Accession: `P31749`
- Current status: `candidate_only_no_variant_anchor`
- Recommended anchor: `7NH5:A`
- Method: X-ray diffraction
- Resolution: `1.9 A`
- Coverage: `0.927`

## Executable Payload Shape

The first payload needs one explicit row with these field groups:

- identity: `accession`, `protein_ref`
- explicit variant anchor: `variant_ref`, `protein_variant.summary_id`
- structure anchor: `structure_id`, `chain_id`
- span and coverage: `residue_span_start`, `residue_span_end`, `uniprot_span`, `coverage`
- experimental context: `experimental_method`, `resolution_angstrom`
- provenance and truth: `source_artifact_ids`, `candidate_only_status`, `join_status`, `join_reason`, `truth_note`

## Minimum Example

- `accession = P31749`
- `protein_ref = protein:P31749`
- `structure_id = 7NH5`
- `chain_id = A`
- `residue_span_start = 2`
- `residue_span_end = 446`
- `uniprot_span = 2-446`
- `coverage = 0.927`
- `experimental_method = X-ray diffraction`
- `resolution_angstrom = 1.9`
- `candidate_only_status = candidate_only_no_variant_anchor`
- `join_status = candidate_only`
- `join_reason = explicit structure-side variant_ref required before promotion`

The only missing payload value is the explicit `variant_ref` / `protein_variant.summary_id`.

## Truth Boundary

This schema is enough to write the first narrow payload row, but it still cannot claim:

- a direct structure-backed variant join
- a promoted `structure_unit` row
- release-grade completeness

The row must remain candidate-only until the structure-side `variant_ref` is explicit and the validation gate passes.

## Why This Is Minimal

The current validation already checks the important truth gates:

- accession match
- explicit variant anchor
- chain and span provenance
- residue coverage consistency
- operator truthfulness
- no inferred join
- publication boundary

The neighboring `structure_variant_candidate_map` carries the same rule: candidate-only remains the status until the structure-side `variant_ref` exists.

## Operator Read

Use this schema to emit the first narrow `P31749` payload row and nothing broader. If the explicit variant anchor cannot be written, keep the row candidate-only and stop before promotion.
