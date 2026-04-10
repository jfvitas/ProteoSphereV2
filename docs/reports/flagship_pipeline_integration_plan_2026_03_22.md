# Flagship Pipeline Integration Plan

Date: 2026-03-22
Gate: `P5-I012`

## Goal

Wire the landed multimodal surfaces into a single, conservative flagship path without redesigning the stack. The integration should stay aligned to the current repo contract: dataset adapter first, training entrypoint second, fusion model and uncertainty head as post-adaptation steps, and metrics as the final summary layer.

## Exact Wiring Points

- `datasets/multimodal/adapter.py::MultimodalDatasetAdapter.adapt` for turning `StorageRuntimeResult` plus optional `PPIRepresentation` into a `MultimodalDataset`.
- `training/multimodal/train.py::prepare_multimodal_training` and `train_multimodal_model` as the orchestration entrypoint. This is currently contract-plan-only and already surfaces a `trainer_runtime` blocker instead of pretending a trainer exists.
- `models/multimodal/fusion_model.py::FusionModel.fuse` and `fuse_modalities` for the deterministic multimodal fusion result.
- `models/multimodal/uncertainty.py::UncertaintyHead.evaluate` and `estimate_uncertainty` for the uncertainty sidecar.
- `evaluation/multimodal/metrics.py::summarize_multimodal_metrics` for the final aggregate report.

## Expected Artifacts

The integration should emit a small, JSON-ready chain of artifacts:

- `MultimodalDataset` with explicit `ready`, `partial`, or `unresolved` status.
- `MultimodalTrainingBackendResult` containing `spec`, `dataset`, `fusion_model`, `plan`, `state`, and `blockers`.
- `FusionModelResult` with modality presence, fused embedding, feature vector, and provenance.
- `UncertaintyHeadResult` with uncertainty, confidence, and modality coverage fields.
- `MultimodalMetrics` with per-example coverage and aggregate completeness statistics.

Preserve provenance through every step. Do not collapse missing or ambiguous modality cases into a clean-looking success.

## Test Shape

Keep the integration tests small and representative.

- Happy path: one storage runtime bundle with a ready example, a deterministic PPI representation, fusion on the landed three-modality contract, uncertainty estimation, and metrics summarization.
- Partial path: omit the PPI representation or one modality input and assert that the dataset and training plan surface the gap explicitly.
- Serialization path: assert that `to_dict()` output is JSON-ready for the training result, fusion result, uncertainty result, and metrics summary.

Use the existing unit tests as shape references:

- `tests/unit/datasets/test_multimodal_adapter.py`
- `tests/unit/training/test_multimodal_train.py`
- `tests/unit/models/test_fusion_model.py`
- `tests/unit/models/test_uncertainty.py`
- `tests/unit/evaluation/test_multimodal_metrics.py`

## Likely Failure Surfaces

- The dataset adapter can return `partial` or `unresolved` when `ppi` data is missing or ambiguous.
- `FusionModel.fuse` rejects empty modality input and invalid modality contracts.
- `UncertaintyHead.evaluate` must receive a real fusion result shape; malformed payloads should fail fast.
- `summarize_multimodal_metrics` rejects empty inputs or mixed model contracts.
- The training entrypoint must keep the explicit `trainer_runtime` blocker until a real trainer/checkpoint loop is actually wired.

## Execution Note

This is the smallest sensible flagship integration slice: keep the dataset contract, preserve the existing blocker semantics, and thread the new fusion, uncertainty, and metrics surfaces through the same run record. Once this is green, `P6-I007` can consume the resulting training artifacts as the benchmark substrate.
