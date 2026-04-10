# Multimodal Package Flow Checklist

Date: 2026-03-22
Task: `P5-I013`

## Purpose

This is the execution-side checklist for validating the landed package/runtime path immediately after `P5-I012`. It stays aligned to the current code path:

- storage runtime assembly
- package builder
- multimodal dataset adapter
- multimodal training entrypoint

The goal is not to redesign the flow. The goal is to verify that the landed contract stays conservative, provenance-safe, and JSON-ready on real package-shaped inputs.

## What Is Already Proven

The repo already proves the package/runtime chain can materialize a selected-example package end to end:

- `execution/storage_runtime.py` integrates a selected-example package into `StorageRuntimeResult`.
- `execution/materialization/package_builder.py` preserves selected-example scope and package provenance.
- `datasets/multimodal/adapter.py` can turn `StorageRuntimeResult` plus optional PPI representation into a `MultimodalDataset`.
- `training/multimodal/train.py` produces a deterministic `MultimodalTrainingBackendResult` and keeps the trainer runtime blocked instead of inventing execution.

The relevant integration coverage is already in:

- `tests/integration/test_training_package_materialization.py`
- `tests/unit/datasets/test_multimodal_adapter.py`
- `tests/unit/training/test_multimodal_train.py`

## Validation Checklist

### 1. Storage runtime assembly

- Start from a selected-example `PackageManifest` and integrate it through `integrate_storage_runtime(...)`.
- Verify the runtime status is explicit: `integrated`, `partial`, or `unresolved`.
- Verify `selected_example_ids` are preserved exactly.
- Verify `package_build.package_manifest.selected_examples` matches the manifest scope and is not widened.
- Verify package provenance and notes thread through the runtime object.

### 2. Package builder contract

- Confirm `build_training_package(...)` returns a `TrainingPackageBuildResult`.
- Confirm the returned `package_manifest.materialization` is present and carries split metadata when provided.
- Confirm the resulting package status reflects the materialization state:
  - `built` for fully materialized selections
  - `partial` for incomplete selections
  - `unresolved` when nothing materialized
- Confirm the selected examples remain unchanged across the package build.

### 3. Multimodal dataset adapter

- Feed the storage runtime into `MultimodalDatasetAdapter.adapt(...)`.
- If a PPI representation is available, include it; otherwise validate the explicit PPI gap path.
- Verify the dataset status is one of `ready`, `partial`, or `unresolved`.
- Verify requested modalities are preserved and normalized.
- Verify missing or ambiguous inputs surface as explicit issues instead of being dropped.
- Verify provenance refs include the runtime and package lineage.

### 4. Training entrypoint

- Call `prepare_multimodal_training(...)` or `train_multimodal_model(...)` on the storage runtime.
- Verify the result is deterministic for the same inputs and seed.
- Verify the result contains:
  - `spec`
  - `dataset`
  - `fusion_model`
  - `plan`
  - `state`
  - `blockers`
- Verify the blocker is still explicit while the trainer runtime is not wired.
- Verify the checkpoint tag is deterministic and derived from the package lineage.
- Verify the plan records observed, missing, and unsupported modalities explicitly.

### 5. Serialization sanity

- Verify `to_dict()` output is JSON-ready for:
  - `StorageRuntimeResult`
  - `TrainingPackageBuildResult`
  - `MultimodalDataset`
  - `MultimodalTrainingBackendResult`
- Verify no nested provenance, notes, or issue payload collapses to a non-serializable shape.

## Expected Artifacts

The validation should produce or inspect these artifacts:

- `StorageRuntimeResult`
- `SelectiveMaterializationResult`
- `TrainingPackageBuildResult`
- `PackageManifest`
- `MultimodalDataset`
- `MultimodalTrainingBackendResult`
- `MultimodalTrainingPlan`
- `MultimodalTrainingState`
- `MultimodalTrainingRuntimeStatus`
- `MultimodalTrainingBlocker`

At the package level, the important concrete fields are:

- `package_manifest.selected_examples`
- `package_manifest.materialization`
- `package_manifest.provenance`
- `package_manifest.notes`
- `selected_example_ids`
- `status`

At the training level, the important concrete fields are:

- `spec.source_path`
- `spec.config`
- `dataset.status`
- `dataset.provenance_refs`
- `plan.checkpoint_tag`
- `plan.plan_signature`
- `plan.status.blocker`
- `state.state_signature`

## Failure Conditions

Treat the validation as failed if any of the following happen:

- Selected-example scope widens, shrinks, or reorders unexpectedly.
- Provenance is lost or collapsed across storage runtime, package build, dataset, or training output.
- A partial or unresolved input is reported as clean success.
- The dataset adapter hides missing PPI data instead of surfacing an explicit issue.
- The training entrypoint stops being deterministic for the same storage/runtime inputs and seed.
- The trainer runtime blocker disappears before a real trainer is actually wired.
- `to_dict()` output is not JSON-ready or drops lineage fields needed for replay.

## Execution Order

1. Validate one fully integrated selected-example package.
2. Validate the explicit missing-PPI path.
3. Validate the deterministic training contract over the same runtime.
4. Validate JSON-ready serialization on the resulting package and training artifacts.

If these four checks pass, `P5-I013` is green enough to hand the resulting artifacts to the flagship integration work and the benchmark prep wave.
