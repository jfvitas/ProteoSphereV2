# P23-I007 RC Bundle Validation

## Scope
This report validates the RC bundle and cold-start install flow using the local evidence now present in the repo. It is intentionally report-only and fails closed on the same truth boundaries as the surrounding release work.

## Evidence Inspected
- [install_bootstrap_state.json](/D:/documents/ProteoSphereV2/artifacts/status/install_bootstrap_state.json)
- [release_bundle_manifest.json](/D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/release_bundle_manifest.json)
- [release_notes.md](/D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/release_notes.md)
- [release_support_manifest.json](/D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/release_support_manifest.json)
- [sample_project_tutorial_package_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/sample_project_tutorial_package_preview.json)
- [sample_project_tutorial_package_preview.md](/D:/documents/ProteoSphereV2/docs/reports/sample_project_tutorial_package_preview.md)
- [operator_dashboard.json](/D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/operator_dashboard.json)
- [orchestrator_state.json](/D:/documents/ProteoSphereV2/artifacts/status/orchestrator_state.json)

## Commands Run
```powershell
python scripts\install_proteosphere.py
python scripts\generate_release_notes.py
python scripts\package_sample_projects.py
python scripts\validate_operator_state.py --json
```

## Cold-Start Install Validation
The install/bootstrap path is now materially validated by [install_bootstrap_state.json](/D:/documents/ProteoSphereV2/artifacts/status/install_bootstrap_state.json), which reports:
- `dependency_verified = true`
- `bootstrap_verified = true`
- `bootstrap_status = ready`
- no missing dependencies
- no missing bootstrap paths

The install script also confirms the repo has the required runtime entrypoints and bootstrap surfaces in place, including `scripts/bootstrap_repo.py`, `scripts/orchestrator.py`, `scripts/monitor.py`, `scripts/tasklib.py`, `scripts/validate_operator_state.py`, and `scripts/powershell_interface.ps1`.

This is enough to treat cold-start installation as **ready for the prototype runtime**, but not as production-equivalent. The report stays blocked if any of the bootstrapping checks drift.

## RC Bundle Validation
The RC bundle is represented by [release_bundle_manifest.json](/D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/release_bundle_manifest.json) and is still explicitly marked `assembled_with_blockers`.

The generated release notes and support manifest were refreshed by [release_notes.md](/D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/release_notes.md) and [release_support_manifest.json](/D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/release_support_manifest.json). Those artifacts preserve the same blocker categories and truth boundary:
- `runtime maturity`
- `source coverage depth`
- `provenance/reporting depth`

The bundle evidence remains internally consistent:
- cohort size is `12`
- resolved accessions are `12`
- unresolved accessions are `0`
- split counts remain `train=8`, `val=2`, `test=2`
- leakage is reported as `true` in the manifest sense, but the bundle is still not release-grade because the blocker categories are carried through

## First-Run Flow
The first-run and sample-project packaging flow is validated by:
- [sample_project_tutorial_package_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/sample_project_tutorial_package_preview.json)
- [sample_project_tutorial_package_preview.md](/D:/documents/ProteoSphereV2/docs/reports/sample_project_tutorial_package_preview.md)

That preview reports:
- `sample_project_count = 2`
- `tutorial_doc_count = 2`
- `missing_artifact_count = 0`
- `stale_doc_count = 0`
- `release_user_ready = true`

The two packaged sample-project manifests remain grounded in the local mirror:
- `bio-agent-lab/demo`
- `bio-agent-lab/training_examples`

This means the RC path can now demonstrate a realistic first-run experience: install, verify bootstrap, generate release notes/support manifest, and package sample-project/tutorial materials without silently accepting missing artifacts or stale docs.

## Current Blockers
The bundle is still not release-ready, and the blocker language must remain explicit:
- `runtime maturity`
- `source coverage depth`
- `provenance/reporting depth`
- the benchmark release state remains `blocked_on_release_grade_bar`

Operationally, the live state still shows a prototype runtime with the release gate blocked, so this RC bundle is valid as an RC artifact but not as a final release artifact.

## Conclusion
The RC bundle and cold-start install flow are validated at the prototype level. The evidence-backed path now covers install/bootstrap, release notes/support manifest generation, sample-project packaging, and operator-state parity, but the bundle remains intentionally blocked on the same release-grade gaps as the rest of the project.
