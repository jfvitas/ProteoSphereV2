# P25-T004 Clean-Machine Reproduction Plan

## Purpose
This report defines the clean-machine reproduction harness as a report-only, fail-closed plan. Its job is to describe how a released system would be rebuilt from tagged artifacts and then replayed through install, packet, and benchmark flows without claiming release authorization or production readiness.

## Evidence Inspected
- [P25 GA Tagging and Manifest Pinning](/D:/documents/ProteoSphereV2/scripts/tag_release.py)
- [P24 GA Signoff Package Validation](/D:/documents/ProteoSphereV2/docs/reports/p24_ga_signoff_package.md)
- [P24 RC Regression Matrix](/D:/documents/ProteoSphereV2/docs/reports/p24_rc_regression_matrix.md)
- [P24 Governance and Contribution Gate Pack](/D:/documents/ProteoSphereV2/docs/reports/p24_governance_pack.md)
- [Post-Release Maintenance Runbook](/D:/documents/ProteoSphereV2/docs/runbooks/post_release_maintenance.md)
- [Release Program Master Plan](/D:/documents/ProteoSphereV2/docs/reports/release_program_master_plan.md)
- [Release Artifact Hardening](/D:/documents/ProteoSphereV2/docs/reports/release_artifact_hardening.md)
- [Release Benchmark Bundle](/D:/documents/ProteoSphereV2/docs/reports/release_benchmark_bundle.md)
- [Release Grade Gap Analysis](/D:/documents/ProteoSphereV2/docs/reports/release_grade_gap_analysis.md)
- [Release Provenance Lineage Gap Analysis](/D:/documents/ProteoSphereV2/docs/reports/release_provenance_lineage_gap_analysis.md)
- [Release Stabilization Regression](/D:/documents/ProteoSphereV2/docs/reports/release_stabilization_regression.md)
- [Operator Dashboard](/D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/operator_dashboard.json)
- [Release Bundle Manifest](/D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/release_bundle_manifest.json)
- [Release Support Manifest](/D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/release_support_manifest.json)
- [Release Notes](/D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/release_notes.md)
- [Procurement Status Board](/D:/documents/ProteoSphereV2/artifacts/status/procurement_status_board.json)
- [Procurement Tail Freeze Gate Preview](/D:/documents/ProteoSphereV2/artifacts/status/procurement_tail_freeze_gate_preview.json)
- [P25-T001](/D:/documents/ProteoSphereV2/artifacts/status/P25-T001.json)
- [P25-T005](/D:/documents/ProteoSphereV2/artifacts/status/P25-T005.json)

## Clean-Machine Scope
The clean-machine harness is the reproduction path we would use to prove that a tagged release can be rebuilt from pinned artifacts on a fresh machine. It is not a claim that release is already authorized.

The harness covers three replay lanes:

1. `install` replay
2. `packet` replay
3. `benchmark` replay

Each lane must preserve the current truth boundary:

- report-only rather than authorization-granting
- fail-closed on missing or stale artifacts
- blocked on the existing release-grade bar until the evidence fully clears it

## Reproduction Contract
The reproduction harness should follow this order:

1. Pin the tagged release identity and manifests.
2. Rebuild the release surface from tagged artifacts only.
3. Replay install on a clean machine.
4. Replay packet materialization against pinned packet manifests.
5. Replay benchmark and compare the resulting artifacts to the tagged evidence set.
6. Stop if any required artifact is missing, stale, or lineage-inconsistent.

The plan should not widen the cohort, swap in live-only evidence, or silently skip blockers to make the replay look successful.

## Required Tagged Artifacts
The clean-machine harness should only be considered complete when these artifacts are present, fresh, and mutually consistent:

- [release_bundle_manifest.json](/D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/release_bundle_manifest.json)
- [release_support_manifest.json](/D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/release_support_manifest.json)
- [release_notes.md](/D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/release_notes.md)
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
- [post_release_maintenance.md](/D:/documents/ProteoSphereV2/docs/runbooks/post_release_maintenance.md)
- [operator_dashboard.json](/D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/operator_dashboard.json)
- [procurement_status_board.json](/D:/documents/ProteoSphereV2/artifacts/status/procurement_status_board.json)
- [procurement_tail_freeze_gate_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/procurement_tail_freeze_gate_preview.json)
- [P25-T001.json](/D:/documents/ProteoSphereV2/artifacts/status/P25-T001.json)
- [P25-T005.json](/D:/documents/ProteoSphereV2/artifacts/status/P25-T005.json)

## Replay Lanes

### Install Replay
The install replay should verify that a clean checkout can bootstrap without hidden state. It should confirm required entrypoints exist, prerequisites are available, and the reproduction harness can write a machine-readable install state.

Expected outcome:
- install succeeds from tagged artifacts
- missing prerequisites fail closed
- no production-readiness claim is made

### Packet Replay
The packet replay should rebuild the selected packet surface from pinned manifests and checksum-validated inputs. It should preserve partial-vs-complete honesty and keep modality deficits visible.

Expected outcome:
- packet materialization is deterministic from tagged inputs
- partial packets remain partial if evidence is incomplete
- missing modalities are surfaced explicitly

### Benchmark Replay
The benchmark replay should run from the tagged benchmark artifacts and compare the resulting truth surface against the frozen evidence set. It should preserve the prototype-runtime boundary and the release-grade blocker language.

Expected outcome:
- benchmark replay reproduces the tagged result set
- prototype-only limitations remain explicit
- any drift or missing lineage blocks the replay

## Truth Boundary
The reproduction harness must remain conservative:

- It is `report-only`.
- It is `fail-closed`.
- It is `blocked_on_release_grade_bar`.
- It is suitable for reproduction rehearsal, not for release authorization.

The harness should stop rather than infer success when a tagged artifact is missing, stale, or inconsistent with the dashboard or procurement truth.

## Current Blockers
The clean-machine reproduction path is still blocked by the same broad release-grade reality:

- the runtime remains a local prototype
- the benchmark evidence remains bounded by the frozen in-tree cohort
- the procurement tail still has active partial downloads
- release lineage remains fail-closed rather than fully cleared

Those blockers are acceptable for a reproduction plan, but they are not acceptable as a release claim.

## Exit Criteria
This plan is sufficient only when:

1. Every required tagged artifact is present and fresh.
2. Install, packet, and benchmark replay are all described as deterministic, tagged-artifact-driven lanes.
3. Missing or stale artifacts fail closed.
4. The current release posture remains explicit and blocked.
5. The report never claims GA authorization, production equivalence, or wider cohort validation than the evidence supports.

## Current Decision
The clean-machine reproduction harness is ready to define and rehearse, but it is not release-authorizing. The correct posture is `report-only`, `fail-closed`, and `blocked_on_release_grade_bar`.
