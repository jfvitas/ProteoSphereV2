# P76 Operator Ligand Support Truth Review

## Scope

This note reviews the current operator-facing ligand support surface and whether it stays inside current truth boundaries. The grounding inputs are:

- [runs/real_data_benchmark/full_results/operator_dashboard.json](/D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/operator_dashboard.json)
- [artifacts/status/ligand_support_readiness_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/ligand_support_readiness_preview.json)
- [scripts/validate_operator_state.py](/D:/documents/ProteoSphereV2/scripts/validate_operator_state.py)

## Current Operator Surface

The operator dashboard exposes `ligand_support_readiness_preview` as a summarized procurement-status card, not as a full row payload.

Current operator-facing summary:

- `status = complete`
- `row_count = 4`
- `support_accessions = [P00387, P09105, Q2TAC2, Q9NZD4]`
- `deferred_accessions = [Q9UCM0]`
- `bundle_ligands_included = false`
- `ligand_rows_materialized = false`
- `q9ucm0_deferred = true`
- `ready_for_operator_preview = true`

That matches the underlying preview artifact, which is explicitly a `support_only_readiness_card`.

## What The Validator Actually Enforces

[scripts/validate_operator_state.py](/D:/documents/ProteoSphereV2/scripts/validate_operator_state.py) checks the following exact conditions for the ligand support operator surface:

- `row_count == 4`
- `support_accessions == [P00387, P09105, Q2TAC2, Q9NZD4]`
- `deferred_accessions == [Q9UCM0]`
- `bundle_ligands_included == false`
- `ligand_rows_materialized == false`
- `q9ucm0_deferred == true`
- `ready_for_operator_preview == true`

These are the right checks for preventing the main overclaims:

- no claim that bundle ligand rows exist
- no silent scope widening
- no accidental inclusion of `Q9UCM0`

## What The Validator Does Not Check

The validator does not directly validate the row-level details in [ligand_support_readiness_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/ligand_support_readiness_preview.json), including:

- `source_ref`
- `pilot_role`
- `pilot_lane_status`
- `current_blocker`
- `next_stage_target`
- `source_provenance_refs`
- `surface_kind`

It also does not verify that `lane_status_counts` in the operator dashboard still exactly match the row payload.

## Truth Assessment

The current operator surface is **truthful but summary-only**.

What is solid now:

- It does not claim ligand family materialization.
- It keeps the surface narrow and explicit.
- It preserves the `Q9UCM0` deferral.
- It presents readiness/support state rather than pretending the ligand bundle family already exists.

What remains limited:

- The dashboard should not be treated as proof of row-level ligand evidence quality.
- The dashboard is a status summary, not a row-certified operator record.

## Risks

### R1. Row-Level Overread

Low severity. A reader could assume the operator dashboard validates the per-row ligand support details. It does not.

### R2. Lane Label Drift

Low severity. `lane_status_counts` is surfaced, but there is no explicit validation that the row-level `pilot_lane_status` values still aggregate to those counts.

### R3. Support-To-Materialization Confusion

Medium severity. If future operator wording starts implying real ligand-family emission without changing the validator gates, the operator surface could overclaim.

## Next Safe Rule

Keep the operator ligand support surface summary-only until a real lightweight ligand family exists.

The following must remain true:

- `bundle_ligands_included = false`
- `ligand_rows_materialized = false`
- the support accession set remains the current four-row scope
- `Q9UCM0` remains deferred

The first safe upgrade after that would be an operator-visible row digest, but only if it is either directly validated or explicitly labeled as unvalidated preview detail.

## Bottom Line

The current operator-facing ligand support surface is safe and truthful at summary level. The main truth boundary is preserved by the validator: no bundle ligand rows, no widened accession scope, and no premature `Q9UCM0` inclusion. The main limitation is that row-level readiness details are not validated, so the surface should continue to be treated as an operator status summary rather than a row-proof evidence surface.
