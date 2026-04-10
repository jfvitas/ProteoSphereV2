# P24-A001 RC Signoff Plan

## Purpose
This report defines the RC signoff cohort and the dogfood scenarios that we can safely use while the release remains blocked on the existing truth boundary. It is report-only and deliberately fails closed: it documents what is ready to exercise, what is still blocked, and who owns each lane.

## Evidence Inspected
- [release_bundle_manifest.json](/D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/release_bundle_manifest.json)
- [release_notes.md](/D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/release_notes.md)
- [release_support_manifest.json](/D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/release_support_manifest.json)
- [install_bootstrap_state.json](/D:/documents/ProteoSphereV2/artifacts/status/install_bootstrap_state.json)
- [sample_project_tutorial_package_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/sample_project_tutorial_package_preview.json)
- [operator_dashboard.json](/D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/operator_dashboard.json)
- [P23-T003.json](/D:/documents/ProteoSphereV2/artifacts/status/P23-T003.json)
- [P23-T004.json](/D:/documents/ProteoSphereV2/artifacts/status/P23-T004.json)
- [P23-I007.json](/D:/documents/ProteoSphereV2/artifacts/status/P23-I007.json)
- [P23-I008.json](/D:/documents/ProteoSphereV2/artifacts/status/P23-I008.json)
- [P1-I019.json](/D:/documents/ProteoSphereV2/artifacts/status/P1-I019.json)
- [P1-I020.json](/D:/documents/ProteoSphereV2/artifacts/status/P1-I020.json)
- [training_set_readiness_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/training_set_readiness_preview.json)
- [package_readiness_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/package_readiness_preview.json)

## RC Signoff Cohort
The RC signoff cohort is the frozen 12-accession benchmark cohort already carried through the release bundle:

- Cohort size: `12`
- Resolved accessions: `12`
- Unresolved accessions: `0`
- Split counts: `train=8`, `val=2`, `test=2`
- Leakage posture: `leakage_free=true` in the release bundle evidence
- Runtime surface: `local prototype runtime with surrogate modality embeddings and identity-safe resume continuity`

The cohort is intentionally the same frozen set used throughout the current benchmark evidence. We should not widen it for RC signoff. The cohort is useful because it already covers the major proof points we need for dogfooding:

- direct live smoke accessions: `P69905`, `P04637`, `P31749`
- mixed-evidence lane: `P68871`
- thin but resolved accessions: `P00387`, `P02042`, `P02100`, `P69892`, `P09105`, `Q2TAC2`, `Q9NZD4`, `Q9UCM0`

The signoff cohort should be treated as stable unless a later explicit release decision authorizes a new cohort manifest.

## Dogfood Scenarios
The dogfood set is the minimum practical loop we can run repeatedly without pretending the project is release-grade.

### 1. Cold-start install
- Owner: install/bootstrap lane
- Evidence: [install_bootstrap_state.json](/D:/documents/ProteoSphereV2/artifacts/status/install_bootstrap_state.json)
- Scenario: bootstrap a fresh clone, verify repo prerequisites, and confirm the runtime entrypoints are present.
- Exit criteria: bootstrap and dependency checks both report `ready`; no required paths are missing.

### 2. RC bundle assembly and notes generation
- Owner: release bundle lane
- Evidence: [release_bundle_manifest.json](/D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/release_bundle_manifest.json), [release_notes.md](/D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/release_notes.md), [release_support_manifest.json](/D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/release_support_manifest.json)
- Scenario: regenerate the RC bundle notes/support manifest and confirm blocker categories are carried through verbatim.
- Exit criteria: bundle remains `assembled_with_blockers`; blocker categories remain explicit; no silent cohort widening occurs.

### 3. Sample-project packaging
- Owner: user-facing packaging lane
- Evidence: [sample_project_tutorial_package_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/sample_project_tutorial_package_preview.json)
- Scenario: package the `demo` and `training_examples` sample projects and the associated tutorial docs.
- Exit criteria: missing artifact count stays `0`, stale doc count stays `0`, and the package remains report-only rather than authorization-granting.

### 4. Reference execution pipeline smoke run
- Owner: reference execution lane
- Evidence: [P1-I019.json](/D:/documents/ProteoSphereV2/artifacts/status/P1-I019.json), [P1-I020.json](/D:/documents/ProteoSphereV2/artifacts/status/P1-I020.json)
- Scenario: run the baseline dataset builder, reference model summary, reference training loop, and reference metrics as an honest end-to-end smoke path.
- Exit criteria: pipeline returns a partial result when the training backend is summary-only, preserves the `trainer_runtime` blocker, and does not claim production training readiness.

### 5. Schema upgrade and rollback
- Owner: release recovery lane
- Evidence: [P23-T003.json](/D:/documents/ProteoSphereV2/artifacts/status/P23-T003.json), [P23-T004.json](/D:/documents/ProteoSphereV2/artifacts/status/P23-T004.json), [P23-I007.json](/D:/documents/ProteoSphereV2/artifacts/status/P23-I007.json), [P23-I008.json](/D:/documents/ProteoSphereV2/artifacts/status/P23-I008.json)
- Scenario: upgrade a pinned schema artifact forward, then validate rollback/recovery against the paired release manifests.
- Exit criteria: forward migration remains additive-only, rollback remains lineage-aware, and missing lineage artifacts fail closed.

### 6. Operator-state parity
- Owner: runtime supervision lane
- Evidence: [operator_dashboard.json](/D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/operator_dashboard.json)
- Scenario: compare the dashboard truth against the runtime state, queue state, and procurement state.
- Exit criteria: the dashboard reflects the current prototype reality, blocker status is explicit, and release readiness remains blocked.

## Ownership
The RC signoff work is split across stable lanes rather than a single monolithic owner:

- Release/operator owner: keeps the RC narrative honest and decides whether a scenario is signoff-safe.
- Install/bootstrap owner: keeps cold-start setup green and surfaces dependency drift.
- Packaging owner: keeps sample-project and tutorial packaging report-only and fresh.
- Reference runtime owner: keeps the baseline builder, model, training loop, and metrics aligned and summary-only.
- Recovery owner: keeps schema migration and rollback fail-closed and lineage-aware.
- Runtime supervision owner: keeps the dashboard, queue, and procurement truth synchronized.

If one of these lanes drifts, the signoff should stop rather than widening scope to compensate.

## Exit Criteria
RC signoff can proceed only when all of the following remain true:

1. The frozen 12-accession cohort stays unchanged and leakage-free.
2. Cold-start install stays `ready` and does not lose required bootstrap paths.
3. The RC bundle and support manifest continue to preserve blocker categories explicitly.
4. Sample-project packaging stays report-only and fresh.
5. The reference pipeline stays partial when the backend is summary-only, with blockers preserved.
6. Schema upgrade and rollback stay forward-only, additive-only, and lineage-aware.
7. Operator-state parity still reports the project as blocked on the existing release-grade bar.
8. No dogfood lane silently claims release-grade readiness, production-equivalent runtime, or wider corpus validation than the evidence supports.

## Current Decision
The RC signoff cohort is ready to dogfood, but the release is not ready to sign off as production. The correct posture is `ready_for_review` for RC scenarios and `blocked_on_release_grade_bar` for release authorization.
