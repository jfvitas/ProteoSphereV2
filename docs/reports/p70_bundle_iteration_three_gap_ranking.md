# p70 Bundle Iteration Three Gap Ranking

## Summary
The next safe family after `protein_similarity_signatures` is `dictionaries`.
It remains the safest missing step because it is packaging and lookup work, not a new biological acquisition lane.

## Grounding
This ranking is grounded in:
- `artifacts/status/lightweight_bundle_manifest.json`
- `artifacts/status/p69_bundle_iteration_two_contract.json`
- `artifacts/status/p69_ligand_signature_stage1_contract.json`
- `artifacts/status/p68_bundle_family_gap_ranking.json`

The current manifest still reports `protein_similarity_signatures = 0`, `ligands = 0`, and `dictionaries = 0`, while `structure_similarity_signatures` and `leakage_groups` are already materialized.

## Ranked Gap Set
1. `dictionaries`
2. `ligand_similarity_signatures`
3. `ligands`
4. `interaction_similarity_signatures`
5. `interactions`

## Why `dictionaries` First
`dictionaries` is the lowest-risk missing family after the protein similarity slice. It changes bundle packaging and lookup mechanics, not biological procurement, so it stays ahead of the ligand lane.

## Ligand Lane Context
The stage-1 ligand contract is useful, but it does not mean ligand materialization is already live. It still describes a pilot path, and the current manifest continues to show zero ligands and zero ligand similarity signatures.

That keeps `ligand_similarity_signatures` and `ligands` behind `dictionaries` in the safe ordering.

## Truth Boundary
This is a report-only ranking.
It does not claim implementation, completeness, or release readiness.
