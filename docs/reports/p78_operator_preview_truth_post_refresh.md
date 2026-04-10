# P78 Operator Preview Truth Post Refresh

## Scope

This note reviews whether the refreshed operator dashboard surfaces remain truthful after the latest bundle refresh. It is grounded in:

- [runs/real_data_benchmark/full_results/operator_dashboard.json](/D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/operator_dashboard.json)
- [artifacts/status/ligand_identity_pilot_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/ligand_identity_pilot_preview.json)
- [artifacts/status/structure_followup_single_accession_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/structure_followup_single_accession_preview.json)
- [artifacts/status/lightweight_bundle_manifest.json](/D:/documents/ProteoSphereV2/artifacts/status/lightweight_bundle_manifest.json)
- [artifacts/status/live_bundle_manifest_validation.json](/D:/documents/ProteoSphereV2/artifacts/status/live_bundle_manifest_validation.json)

## What Changed In The Bundle Refresh

The refreshed bundle manifest now includes two additional live families:

- `structure_followup_payloads` with `2` records
- `ligand_support_readiness` with `4` records

The live bundle validation confirms both are aligned with current preview artifacts.

What did **not** change:

- `ligands` is still absent from the bundle
- `interactions` is still absent from the bundle
- the bundle is still a `debug_bundle`
- the bundle is still `compressed_sqlite`
- the bundle remains class `A`

## Structure Single-Accession Preview

The operator dashboard exposes:

- `selected_accession = P31749`
- `deferred_accession = P04637`
- `payload_row_count = 1`
- `single_accession_scope = true`
- `candidate_only_no_variant_anchor = true`
- `direct_structure_backed_join_certified = false`
- `structure_ref = 7NH5:A`
- `variant_ref = protein_variant:protein:P31749:K14Q`
- `coverage = 0.927`

This remains truthful after the bundle refresh.

Why:

- the broader bundled family is still `structure_followup_payloads` with two rows
- the dashboard surface is explicitly a narrower one-accession steering view
- the dashboard keeps the candidate-only boundary explicit
- the dashboard does not claim a certified direct structure-backed join

The key boundary:

- this is a narrowed operator summary over the broader structure follow-up layer
- it is not a new bundled family

## Ligand Identity Pilot Preview

The operator dashboard now exposes a richer ligand pilot summary:

- `row_count = 4`
- `ordered_accessions = [P00387, Q9NZD4, P09105, Q2TAC2]`
- `first_accession = P00387`
- `second_accession = Q9NZD4`
- `deferred_accession = Q9UCM0`
- `report_only = true`
- `row_complete_operator_summary = true`
- `ligand_rows_materialized = false`
- `bundle_ligands_included = false`

This also remains truthful after the bundle refresh.

Why:

- the ordered list matches the four ranked rows in [ligand_identity_pilot_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/ligand_identity_pilot_preview.json)
- the dashboard still explicitly says the pilot is `report_only`
- the dashboard still explicitly says no ligand rows are materialized
- the dashboard still explicitly says ligands are not included in the bundle
- the dashboard preserves the `Q9UCM0` deferral

The key boundary:

- `ordered_accessions` is an operator ordering summary
- it is not evidence that a ligand bundle family exists

## New Low-Risk Wording Risks

### W1. `row_complete_operator_summary`

Low risk. This wording is accurate as a summary claim, but it can be overread as:

- fully validated
- bundled
- production-ready

Safer interpretation:

- it is row-complete **for the operator summary surface only**

### W2. `ordered_accessions`

Low risk. After the bundle refresh, operators may assume richer dashboard surfaces are now bundled. That is not true here.

Safer interpretation:

- it is an operator-only ordered pilot list

### W3. Single-Accession Structure Summary

Low risk. Because `structure_followup_payloads` is now a validated bundle family, the single-accession summary can be mistaken for a separate promoted family.

Safer interpretation:

- it is a narrowed steering view over the broader bundled structure-followup payload family

## Safe Wording Rule

For the structure surface:

- describe it as a narrowed operator steering view
- keep `candidate_only_no_variant_anchor = true` visible
- keep `direct_structure_backed_join_certified = false` visible

For the ligand pilot surface:

- describe `ordered_accessions` as an operator ordering summary
- keep `report_only = true` visible
- keep `bundle_ligands_included = false` visible
- keep `ligand_rows_materialized = false` visible
- avoid using `row_complete` as shorthand for validated or bundled

## Bottom Line

The refreshed dashboard surfaces remain truthful. The bundle refresh validated broader structure-followup and ligand-support families, but the newer single-accession structure summary and ordered ligand pilot summary still sit above that layer as operator-only steering surfaces. The only new issues are low-risk wording and summarization risks, not hard truth-boundary failures.
