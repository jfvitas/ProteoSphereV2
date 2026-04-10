# Post-Release Maintenance and Incident Rota

This runbook is report-only and fail-closed. It documents the maintenance expectations and incident rota that apply after a release candidate or signoff package is visible, while the project remains blocked on the current release-grade bar. It does not authorize release, widen the cohort, or relax the truth boundary.

## Evidence Inspected
- [release_program_master_plan.md](/D:/documents/ProteoSphereV2/docs/reports/release_program_master_plan.md)
- [release_artifact_hardening.md](/D:/documents/ProteoSphereV2/docs/reports/release_artifact_hardening.md)
- [release_benchmark_bundle.md](/D:/documents/ProteoSphereV2/docs/reports/release_benchmark_bundle.md)
- [release_grade_gap_analysis.md](/D:/documents/ProteoSphereV2/docs/reports/release_grade_gap_analysis.md)
- [release_provenance_lineage_gap_analysis.md](/D:/documents/ProteoSphereV2/docs/reports/release_provenance_lineage_gap_analysis.md)
- [release_stabilization_regression.md](/D:/documents/ProteoSphereV2/docs/reports/release_stabilization_regression.md)
- [p24_rc_signoff_plan.md](/D:/documents/ProteoSphereV2/docs/reports/p24_rc_signoff_plan.md)
- [p24_rc_regression_matrix.md](/D:/documents/ProteoSphereV2/docs/reports/p24_rc_regression_matrix.md)
- [p24_governance_pack.md](/D:/documents/ProteoSphereV2/docs/reports/p24_governance_pack.md)
- [p24_ga_signoff_package.md](/D:/documents/ProteoSphereV2/docs/reports/p24_ga_signoff_package.md)
- [support_simulation_pack.md](/D:/documents/ProteoSphereV2/docs/runbooks/support_simulation_pack.md)
- [operator_dashboard.json](/D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/operator_dashboard.json)
- [procurement_status_board.json](/D:/documents/ProteoSphereV2/artifacts/status/procurement_status_board.json)
- [procurement_tail_freeze_gate_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/procurement_tail_freeze_gate_preview.json)

## Current Posture
The current posture remains `blocked_on_release_grade_bar`.

This runbook is useful for maintenance rehearsal, support triage, and incident routing, but it must stay honest about the current evidence:

- the runtime is still a local prototype
- the benchmark remains bounded by the frozen 12-accession cohort
- the procurement tail still contains active partial downloads
- GA signoff remains report-only and fail-closed

## Maintenance Expectations
Maintenance work should keep the release surface accurate without changing the release truth boundary.

- Refresh governance, RC, and support artifacts when the source evidence changes.
- Keep the dashboard, procurement board, and signoff reports mutually consistent.
- Preserve fail-closed validators for freshness, provenance, and rollback truth.
- Keep release docs, support docs, and incident notes small, explicit, and reviewable.
- Avoid silently widening the cohort, corpus, or release claims.
- Keep partial downloads, prototype runtime outputs, and preview surfaces labeled as non-governing.

Maintenance is successful when the project remains explainable under repeat inspection and the blocker state stays accurate.

## Incident Rota
Use the following rota when something drifts after RC visibility or during maintenance windows:

### 1. Operator and Dashboard Incident
Owner: runtime supervision lane.

What to check:

- dashboard truth against queue truth
- procurement truth against the active download lanes
- whether the release posture still reports `blocked_on_release_grade_bar`

Expected action:

- refresh the operator dashboard and status boards
- keep any mismatch explicit
- do not infer release readiness from a stale view

### 2. Governance and Docs Incident
Owner: release docs lane.

What to check:

- freshness of the release program and governance pack
- freshness of the RC signoff and regression matrix
- presence of the GA signoff package and support simulation pack

Expected action:

- rerun the freshness validator
- update the affected report only after the source evidence changes
- keep missing or stale docs fail-closed

### 3. Procurement and Tail Incident
Owner: procurement lane.

What to check:

- whether STRING or UniRef partial downloads are still active
- whether the freeze gate is still blocked
- whether a download restart or truncation changed the partial-file truth

Expected action:

- refresh procurement summaries
- keep the two remaining partials visible
- do not treat progress as completion until the gate is zero-gap

### 4. Recovery or Rollback Incident
Owner: recovery lane.

What to check:

- lineage compatibility
- release bundle presence
- whether rollback artifacts are present and fresh

Expected action:

- fail closed on missing lineage
- preserve any partial output removal rules
- do not relax the recovery gate to make the incident look resolved

## Required Maintenance Artifacts
These artifacts must remain present and mutually consistent for this runbook to stay complete:

- [release_program_master_plan.md](/D:/documents/ProteoSphereV2/docs/reports/release_program_master_plan.md)
- [release_artifact_hardening.md](/D:/documents/ProteoSphereV2/docs/reports/release_artifact_hardening.md)
- [release_benchmark_bundle.md](/D:/documents/ProteoSphereV2/docs/reports/release_benchmark_bundle.md)
- [release_grade_gap_analysis.md](/D:/documents/ProteoSphereV2/docs/reports/release_grade_gap_analysis.md)
- [release_provenance_lineage_gap_analysis.md](/D:/documents/ProteoSphereV2/docs/reports/release_provenance_lineage_gap_analysis.md)
- [release_stabilization_regression.md](/D:/documents/ProteoSphereV2/docs/reports/release_stabilization_regression.md)
- [p24_rc_signoff_plan.md](/D:/documents/ProteoSphereV2/docs/reports/p24_rc_signoff_plan.md)
- [p24_rc_regression_matrix.md](/D:/documents/ProteoSphereV2/docs/reports/p24_rc_regression_matrix.md)
- [p24_governance_pack.md](/D:/documents/ProteoSphereV2/docs/reports/p24_governance_pack.md)
- [p24_ga_signoff_package.md](/D:/documents/ProteoSphereV2/docs/reports/p24_ga_signoff_package.md)
- [support_simulation_pack.md](/D:/documents/ProteoSphereV2/docs/runbooks/support_simulation_pack.md)

If any of these are missing, stale, or inconsistent with the dashboard or procurement truth, the runbook should remain blocked.

## Escalation Rules
- Escalate to the operator lane first if the dashboard and procurement truth disagree.
- Escalate to the docs lane if a report is stale or the blocker language drifts.
- Escalate to the recovery lane if a rollback or lineage check fails closed.
- Escalate to the procurement lane if the remaining partial downloads stop changing unexpectedly.

## Exit Criteria
This runbook is adequate for maintenance and incident rota use when:

1. the required maintenance artifacts are present and fresh
2. the incident rota names the correct owners and actions
3. the current blocked release posture stays explicit
4. no scenario claims release authorization
5. no scenario hides the current blockers

## Notes
- Treat this as an operator aid, not as a release authorization artifact.
- If the evidence changes, update the affected report references before changing the rota language.
- If the release posture changes, the runbook must be refreshed rather than implicitly reinterpreted.
