# P23-I008 Upgrade and Rollback Validation

## Scope
This report validates the upgrade and rollback path using the completed schema migration work, the rollback/recovery implementation, and the RC bundle evidence already present in the repository. It is report-only and fails closed on missing lineage artifacts.

## Evidence Inspected
- [release_bundle_manifest.json](/D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/release_bundle_manifest.json)
- [release_notes.md](/D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/release_notes.md)
- [release_support_manifest.json](/D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/release_support_manifest.json)
- [install_bootstrap_state.json](/D:/documents/ProteoSphereV2/artifacts/status/install_bootstrap_state.json)
- [P23-T003.json](/D:/documents/ProteoSphereV2/artifacts/status/P23-T003.json)
- [P23-T004.json](/D:/documents/ProteoSphereV2/artifacts/status/P23-T004.json)
- [P23-I007.json](/D:/documents/ProteoSphereV2/artifacts/status/P23-I007.json)
- [schema_migrate.py](/D:/documents/ProteoSphereV2/scripts/schema_migrate.py)
- [rollback_release.py](/D:/documents/ProteoSphereV2/scripts/rollback_release.py)

## Commands Replayed From Local Validation Artifacts
The completed task evidence records the following commands as the ones actually used to validate the flow:
```powershell
python -m pytest tests\integration\test_schema_migrate.py -q
python -m ruff check scripts\schema_migrate.py tests\integration\test_schema_migrate.py
python scripts\schema_migrate.py --input artifacts\status\summary_library_inventory.json --output <temp> --report-json
python -m pytest tests\integration\test_rollback_release.py -q
python -m ruff check scripts\rollback_release.py tests\integration\test_rollback_release.py
python scripts\install_proteosphere.py
python scripts\generate_release_notes.py
python scripts\package_sample_projects.py
python scripts\validate_operator_state.py --json
```

## Upgrade Validation
The schema migration path is implemented as a forward-only, additive-only upgrade from schema version 1 to 2. The recorded validation evidence in [P23-T003.json](/D:/documents/ProteoSphereV2/artifacts/status/P23-T003.json) shows:
- the pinned `schema_version: 1` artifact can be upgraded to `schema_version: 2`
- the migration preserves top-level truth boundaries
- unsupported target versions are rejected
- the migration report is file-safe and includes input/output SHA-256 values

This is enough to treat schema upgrade as auditable for pinned in-tree artifacts, but only within the supported forward path.

## Rollback Validation
The rollback/recovery path is implemented in [rollback_release.py](/D:/documents/ProteoSphereV2/scripts/rollback_release.py) and validated by [P23-T004.json](/D:/documents/ProteoSphereV2/artifacts/status/P23-T004.json). The rollback path:
- requires a paired `release_bundle_manifest.json`
- checks lineage against a matching `versioned_release_bundle_manifest.json`
- copies a coherent recovery state only when the manifests are lineage-compatible
- deletes partial output if required artifacts are missing or unsafe
- fails closed rather than orphaning a recovery root

That gives us a recoverability contract for tagged release artifacts, but only when both manifests are present and lineage-compatible.

## RC Bundle and Cold-Start Evidence
The RC bundle evidence in [release_notes.md](/D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/release_notes.md) and [release_support_manifest.json](/D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/release_support_manifest.json) confirms the release bundle is still `assembled_with_blockers`, with blocker categories carried through verbatim:
- `runtime maturity`
- `source coverage depth`
- `provenance/reporting depth`

The cold-start and packaging path is supported by [install_bootstrap_state.json](/D:/documents/ProteoSphereV2/artifacts/status/install_bootstrap_state.json) and [P23-I007.json](/D:/documents/ProteoSphereV2/artifacts/status/P23-I007.json), which show the repo bootstraps cleanly, sample project packaging is report-only and fresh, and the operator-state checks remain honest.

## Current Blockers
This validation is intentionally not upgraded to release-grade because one required lineage artifact is still absent from the tree:
- [versioned_release_bundle_manifest.json](/D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/versioned_release_bundle_manifest.json)

The absence of that tagged manifest means the rollback path cannot yet be exercised against a fully materialized versioned release lineage in-repo. The report therefore stays fail-closed.

## Conclusion
The upgrade and rollback flow is implemented and auditable:
- schema upgrade is forward-only and additive-only
- rollback is lineage-aware and fail-closed
- RC bundle evidence remains blocked, not overclaimed

Recoverability is validated at the prototype level on the available artifacts, but the tagged versioned release manifest still needs to be materialized before the flow can be called fully closed.
