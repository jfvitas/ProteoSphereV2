# P66 Structure Follow-Up Materialization Schema

Report-only minimum schema note for a future materialized structure follow-up anchor artifact.

## Source Basis

- [p65_structure_followup_first_attempt_contract.json](/D:/documents/ProteoSphereV2/artifacts/status/p65_structure_followup_first_attempt_contract.json)
- [structure_followup_anchor_candidates.json](/D:/documents/ProteoSphereV2/artifacts/status/structure_followup_anchor_candidates.json)
- [structure_followup_anchor_validation.json](/D:/documents/ProteoSphereV2/artifacts/status/structure_followup_anchor_validation.json)
- [structure_variant_candidate_map.json](/D:/documents/ProteoSphereV2/artifacts/status/structure_variant_candidate_map.json)

## Minimum Schema

A future materialized anchor artifact only needs the fields required to identify one explicit structure-side record and one explicit variant anchor.

Required groups:

- `accession`, `protein_ref`, `structure_id`, `chain_id`
- `variant_ref`, `protein_variant.summary_id`
- `residue_span_start`, `residue_span_end`, `uniprot_span`, `coverage`
- `experimental_method`, `resolution_angstrom`
- `source_artifact_ids`, `candidate_only_status`, `join_status`, `join_reason`, `truth_note`

## Required Semantics

The schema must stay explicit:

- one accession
- one explicit `protein_variant.summary_id` in `variant_ref`
- one structure ID
- one chain ID
- one residue span

It must preserve:

- chain-level provenance
- residue-span coverage
- candidate-only status until the explicit structure-side `variant_ref` exists
- report-only truth boundaries in operator surfaces

It must not claim:

- a direct structure-backed variant join before the structure-side row exists
- a promoted `structure_unit` row before validation passes
- release-grade completeness

## Why This Is Minimal

The first executable attempt only needs enough structure to say exactly which accession, which variant, and which chain/span were materialized.

The current validation already checks the important gates:

- accession match
- explicit variant anchor
- chain and span provenance
- residue coverage consistency
- operator truthfulness
- no inferred join
- publication boundary

The current `structure_variant_candidate_map` shows the same rule in a neighboring surface: candidate-only remains the truth until `variant_ref` is explicit on the structure side.

## First-Attempt Anchor

The first target remains `P31749`, with anchor `7NH5:A`, X-ray diffraction, `1.9 Å`, and `0.927` coverage.

That is the best anchor for the first materialized record, but it still needs an explicit `variant_ref` before it can be treated as a completed structure-side anchor.

## Truth Boundary

This schema note is report-only. It defines the minimum shape for the future artifact, but it does not claim the artifact already exists or that a direct structure-backed join is certified.
