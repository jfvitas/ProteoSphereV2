# P77 Operator Preview Truth Review

## Scope

This note reviews the current operator-facing truth boundaries for:

- [runs/real_data_benchmark/full_results/operator_dashboard.json](/D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/operator_dashboard.json)
- [artifacts/status/structure_followup_single_accession_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/structure_followup_single_accession_preview.json)
- [artifacts/status/ligand_identity_pilot_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/ligand_identity_pilot_preview.json)

## Structure Single-Accession Preview

The operator dashboard currently exposes a narrow structure follow-up summary with:

- `selected_accession = P31749`
- `deferred_accession = P04637`
- `payload_row_count = 1`
- `single_accession_scope = true`
- `candidate_only_no_variant_anchor = true`
- `direct_structure_backed_join_certified = false`
- `structure_ref = 7NH5:A`
- `variant_ref = protein_variant:protein:P31749:K14Q`
- `coverage = 0.927`

That is truth-preserving relative to the underlying preview artifact.

What the operator surface can truthfully say:

- this is a one-accession steering preview
- P31749 is the current focus
- P04637 is still deferred
- the preview is still candidate-only
- there is no certified direct structure-backed join yet

What it must not imply:

- direct structure-backed variant certification
- multi-accession rollout
- ligand or interaction payload expansion
- promotion beyond the current candidate-only preview

## Ligand Identity Pilot Preview

The operator dashboard currently exposes a compact ligand pilot summary with:

- `row_count = 4`
- `first_accession = P00387`
- `second_accession = Q9NZD4`
- `deferred_accession = Q9UCM0`
- `report_only = true`
- `ligand_rows_materialized = false`
- `bundle_ligands_included = false`
- `ready_for_operator_preview = true`

That is also truth-preserving relative to the underlying preview artifact.

What the operator surface can truthfully say:

- there is a narrow ligand pilot ordering surface
- the pilot is still report-only
- no ligand rows are materialized yet
- the bundle still does not include ligands
- Q9UCM0 is still deferred

What it must not imply:

- a live lightweight ligand family already exists
- ligand identity grouping is materialized
- the operator dashboard alone is the full four-row pilot record
- Q9UCM0 is part of the active pilot

## Main Limits

### Structure Preview

The surface is safe because it keeps the candidate-only boundary explicit.

### Ligand Pilot Preview

The surface is safe, but it is more compressed than the underlying artifact. The dashboard only exposes the first two ranked accessions, not the full four-row pilot ordering. That means it should be treated as a steering summary, not the full pilot ledger.

## Risks

### R1. Row-Detail Compression On Ligand Pilot Surface

Low severity. The operator dashboard omits the third and fourth pilot rows, so it should not be treated as the full ordered pilot artifact.

### R2. Structure Preview Overread

Low severity. The structure surface stays safe only while `candidate_only_no_variant_anchor = true` and `direct_structure_backed_join_certified = false` remain explicit.

### R3. Materialization Wording Drift

Medium severity. If future operator wording drops `report_only = true` or `bundle_ligands_included = false`, the ligand pilot surface could start overstating readiness.

## Next Safe Operator Rule

For the structure preview:

- keep `single_accession_scope = true`
- keep `candidate_only_no_variant_anchor = true`
- keep `direct_structure_backed_join_certified = false`
- do not expand beyond `P31749` until a direct join is actually certifiable

For the ligand pilot preview:

- keep `report_only = true`
- keep `ligand_rows_materialized = false`
- keep `bundle_ligands_included = false`
- keep `Q9UCM0` deferred
- do not treat the dashboard summary as the full four-row pilot source of truth

## Bottom Line

Both new operator previews are currently truthful. The structure preview is safe because it remains single-accession and candidate-only. The ligand pilot preview is safe because it remains report-only, non-materialized, and explicit about deferred scope. The main limitation is that both are operator steering summaries, not row-complete proof surfaces.
