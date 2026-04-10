# P24-I007 RC Regression Matrix

## Purpose
This report-only matrix exercises the RC-facing flows that matter most for regression confidence while the project remains blocked on the existing release-grade bar. It is intentionally conservative: it records what we can verify today, what is still partial, and what remains blocked without widening the release boundary.

## Evidence Inspected
- [P24-A001 RC Signoff Plan](/D:/documents/ProteoSphereV2/docs/reports/p24_rc_signoff_plan.md)
- [P24 Governance and Contribution Gate Pack](/D:/documents/ProteoSphereV2/docs/reports/p24_governance_pack.md)
- [Support Simulation Pack](/D:/documents/ProteoSphereV2/docs/runbooks/support_simulation_pack.md)
- [operator_dashboard.json](/D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/operator_dashboard.json)
- [training_set_readiness_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/training_set_readiness_preview.json)
- [package_readiness_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/package_readiness_preview.json)
- [procurement_status_board.json](/D:/documents/ProteoSphereV2/artifacts/status/procurement_status_board.json)
- [P1-I019.json](/D:/documents/ProteoSphereV2/artifacts/status/P1-I019.json)
- [P1-I020.json](/D:/documents/ProteoSphereV2/artifacts/status/P1-I020.json)
- [P23-T003.json](/D:/documents/ProteoSphereV2/artifacts/status/P23-T003.json)
- [P23-T004.json](/D:/documents/ProteoSphereV2/artifacts/status/P23-T004.json)
- [P23-I007.json](/D:/documents/ProteoSphereV2/artifacts/status/P23-I007.json)
- [P23-I008.json](/D:/documents/ProteoSphereV2/artifacts/status/P23-I008.json)
- [P24-T002.json](/D:/documents/ProteoSphereV2/artifacts/status/P24-T002.json)
- [P24-T003.json](/D:/documents/ProteoSphereV2/artifacts/status/P24-T003.json)
- [P24-T004.json](/D:/documents/ProteoSphereV2/artifacts/status/P24-T004.json)
- [P24-T005.json](/D:/documents/ProteoSphereV2/artifacts/status/P24-T005.json)
- [P24-T006.json](/D:/documents/ProteoSphereV2/artifacts/status/P24-T006.json)

## Regression Matrix

| Flow | What We Verify | Current Evidence | Current Assessment | Remaining Blockers |
| --- | --- | --- | --- | --- |
| Install | Cold-start bootstrap, required paths, and dependency presence | Install/bootstrap state and RC signoff evidence | `ready_for_review` for RC drills, not release-ready | None newly introduced; the flow is still bounded by the general release gate |
| Operator | Dashboard truth, queue/procurement parity, and honest blocker reporting | Operator dashboard, procurement status, training/package readiness previews | `blocked_on_release_grade_bar` with explicit state visibility | Supervisor/procurement truth remain operationally active; release authorization remains blocked |
| Packet | Packet completeness, modality deficits, and partial-vs-complete honesty | Support simulation pack and packet deficit references in the dashboard | `report-only` and safe for support drills | Partial packet lanes remain partial; missing modalities remain visible |
| Benchmark | Reference runtime smoke path, RC bundle assembly, and benchmark blocker preservation | `P1-I019`, `P1-I020`, RC signoff plan, governance pack | `partial` and useful for dogfood, but not production-equivalent | Runtime is still a local prototype; benchmark evidence remains bounded by the frozen 12-accession cohort |
| Recovery | Schema upgrade, rollback, and lineage-aware recovery behavior | `P23-T003`, `P23-T004`, `P23-I007`, `P23-I008` | `fail-closed` and suitable for regression rehearsal | Versioned release lineage is still incomplete in-tree; rollback remains lineage-aware but not signoff-grade |

## Flow Notes

### Install
The install path is the least risky of the five flows, but it still only supports RC rehearsal. It confirms that bootstrap artifacts and repo prerequisites are present and that the runtime entrypoints exist. That is enough to keep the RC drill honest, but not enough to widen the release claim.

### Operator
The operator path is currently healthy as a truth surface, not as a release signal. The dashboard and queue/procurement surfaces agree that the system is still blocked on the release-grade bar, and that is the correct posture to keep.

### Packet
Packet handling is explicitly report-only. Partial packets and modality deficits are surfaced honestly, but the matrix should not interpret partial coverage as an acceptable substitute for full corpus completeness.

### Benchmark
The benchmark lane remains a prototype smoke path. The reference pipeline and bundle assembly are useful for regression checking, yet they do not represent production-grade training or release-grade validation.

### Recovery
Recovery is the most important fail-closed lane for RC regressions. The schema and rollback evidence shows we can exercise additive migration and lineage-aware rollback, but missing versioned lineage still blocks any broader claim.

## Blocker Triage
- `release_grade_bar`: still active, so RC coverage stays advisory rather than authoritative for release authorization.
- `prototype_runtime`: still active, so benchmark and training results remain bounded by the local runtime surface.
- `partial_packet_coverage`: still active, so packet regressions should continue to report deficits rather than normalizing them away.
- `incomplete_release_lineage`: still active, so recovery and rollback should continue to fail closed on missing or mismatched lineage.
- `procurement_tail_partial`: still active, so STRING/UniRef-dependent claims remain out of scope for RC signoff.

## Current Decision
This regression matrix supports RC rehearsal and blocker triage only. It does not upgrade the project to release-ready, and it should not be interpreted as changing the current `blocked_on_release_grade_bar` posture.

## Exit Criteria
The matrix can be considered sufficient for RC regression tracking when:

1. All five flows are represented with concrete evidence.
2. Remaining blockers are named explicitly and stay fail-closed.
3. The report never claims production readiness, release authorization, or corpus completeness beyond the evidence.
4. The report stays aligned with the current dashboard and support-runbook truth.
