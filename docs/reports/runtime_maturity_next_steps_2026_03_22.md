# Runtime Maturity Next Steps

Date: 2026-03-22  
Scope: release-readiness analysis for the multimodal trainer/runtime surface

## Current Prototype Constraints

- `training/multimodal/train.py` is still contract-plan-only. It emits `trainer_backend = "contract-plan-only"`, sets the trainer blocker at `trainer_runtime`, and leaves `MultimodalTrainingState.phase` as `blocked` with `processed_examples = 0`.
- `training/multimodal/runtime.py` is still a local prototype runtime. It synthesizes surrogate modality embeddings (`sequence-surrogate-runtime-v1`, `structure-surrogate-runtime-v1`, `ligand-surrogate-runtime-v1`) and tags the backend as `local-prototype-runtime`.
- Resume is identity-safe, but only at the example-identity level today. The runtime checks `processable_example_ids` and refuses mismatched tails, which is good for honesty but still not a real trainer resume stack.
- `execution/flagship_pipeline.py` already threads training, fusion, uncertainty, metrics, GPU policy, and registry wiring, but it is still consuming the blocked prototype training result, not a production trainer output.
- The benchmark gap analysis and the full-results manifests both say the same thing: the runtime remains a prototype with surrogate embeddings, while provenance and source coverage are still thinner than a release-grade bar.

## Smallest Next Tasks

| Task | Outcome | Owner files |
| --- | --- | --- |
| 1. Replace surrogate runtime embeddings with real modality inputs and a real step loop. | The runtime should consume actual encoder outputs and perform a real forward/training step instead of fabricating modality vectors. | `training/multimodal/runtime.py`, `models/multimodal/sequence_encoder.py`, `models/multimodal/structure_encoder.py`, `models/multimodal/ligand_encoder.py`, `models/multimodal/fusion_model.py` |
| 2. Persist trainer state and resume cursor in a checkpoint shape that survives round-trip reloads. | Checkpoints should carry optimizer/head state, processed example identity, and resume metadata without relying on prototype-only assumptions. | `training/multimodal/runtime.py`, `execution/checkpoints/store.py` |
| 3. Turn `train.py` into a thin executable training entrypoint instead of a blocker-only planner. | The public multimodal training entrypoint should execute the real runtime path and only emit blockers when the backend is genuinely unavailable. | `training/multimodal/train.py` |
| 4. Wire the flagship pipeline to the real trainer/runtime result shape. | The pipeline should keep the current fusion, uncertainty, metrics, GPU policy, and registry flow, but consume a real runtime result rather than a contract plan. | `execution/flagship_pipeline.py`, `training/runtime/experiment_registry.py` |
| 5. Add checkpoint/resume regression coverage for the real runtime path. | Tests should prove continuation, identity-safe resume, and explicit failure on mismatched dataset tails. | `tests/unit/training/test_multimodal_runtime.py`, `tests/unit/training/test_multimodal_train.py` |
| 6. Add end-to-end pipeline smoke coverage once the runtime becomes executable. | The flagship path should be verified as a real local run, not just a contract wrapper. | `tests/integration/test_flagship_pipeline.py` |

## Practical Ownership Split

- Runtime execution belongs in `training/multimodal/runtime.py`.
- The public training surface belongs in `training/multimodal/train.py`.
- Persistent checkpoint semantics belong in `execution/checkpoints/store.py`.
- Pipeline integration and registry threading belong in `execution/flagship_pipeline.py` and `training/runtime/experiment_registry.py`.
- The proof burden belongs in the matching unit and integration tests listed above.

## Why This Is The Smallest Honest Path

This sequence keeps the current prototype honest while moving the surface toward a real trainer in the least disruptive order:

1. make the runtime real,
2. persist and resume it correctly,
3. expose it through the entrypoint,
4. thread it through the flagship pipeline,
5. lock the behavior with tests,
6. then widen the integration smoke.

That avoids redesigning the benchmark or pipeline before the runtime itself is no longer surrogate-backed.
