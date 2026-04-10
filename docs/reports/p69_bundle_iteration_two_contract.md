# p69 Bundle Iteration Two Contract

## Summary
The next safe lightweight bundle family expansion is `protein_similarity_signatures`.
It is the safest remaining missing family because it is derived from the already-materialized protein surface, uses the existing 11 protein rows, and does not require any new procurement lane.

## Grounding
This contract is grounded in:
- `artifacts/status/lightweight_bundle_manifest.json`
- `artifacts/status/p68_bundle_family_gap_ranking.json`
- `artifacts/status/entity_signature_preview.json`
- `artifacts/status/p67_ligand_signature_emission_prereqs.json`

The current preview bundle remains `preview_generated_verified_assets` with `budget_class = A` and `compressed_size_bytes = 239656`.

## Iteration Two Contract
- Family: `protein_similarity_signatures`
- Rank: `1`
- Safety tier: `safe_now`
- Row count: `11`
- Input surface: `entity_signature_preview`
- Basis: protein rows with `sequence_equivalence_group`
- Size risk: `low`

The included accessions are:
`P00387`, `P02042`, `P02100`, `P04637`, `P09105`, `P31749`, `P68871`, `P69892`, `P69905`, `Q2TAC2`, `Q9NZD4`.

## What This Excludes
Already materialized and not ranked:
- `structure_similarity_signatures`
- `leakage_groups`

Deferred behind current prereqs or later ranking:
- `dictionaries`
- `ligand_similarity_signatures`
- `interaction_similarity_signatures`
- `ligands`
- `interactions`

The ligand prereq artifact still blocks non-null ligand grouping, so ligand-derived families remain out of scope for this slice.

## Truth Boundary
This is a report-only contract.
It does not claim implementation, completeness, or release readiness.
