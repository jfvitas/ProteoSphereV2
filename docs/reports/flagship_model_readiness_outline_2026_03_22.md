# Flagship Model Readiness Outline

Date: 2026-03-22
Task: `P5-I014`

## Purpose

Prepare the structure and decision criteria for the flagship model readiness report without inventing new architecture or pretending the runtime is further along than it is. This outline assumes the landed sequence, structure, and ligand encoders; the conservative fusion and uncertainty contracts; the storage/runtime and package materialization direction; and the live-data smoke evidence already checked into the repo.

The report that follows this outline should answer one question plainly: is the flagship path ready to be called ready, or is it still only partially integrated and benchmark-dependent?

## Gate Summary

Use three explicit readiness buckets.

### 1. Already proven components

These are grounded in landed code and live-smoke evidence:

- Storage/runtime assembly for selected-example packages is conservative and explicit.
- The multimodal training entrypoint preserves blocker semantics instead of fabricating a trainer.
- The fusion model exists as a deterministic contract over the landed three-modality baseline.
- The uncertainty head exists as a deterministic contract over the fusion result.
- Live-source evidence exists for the benchmark spine: UniProt, InterPro, Reactome, BindingDB, IntAct, experimental structure, predicted structure, and evolutionary/MSA smoke.

### 2. Integration-dependent components

These require the flagship integration gate to stay green in the current repo:

- `datasets/multimodal/adapter.py` must continue to turn storage runtime output plus optional PPI representation into a `MultimodalDataset` with explicit `ready`, `partial`, or `unresolved` status.
- `training/multimodal/train.py` must continue to emit a deterministic `MultimodalTrainingBackendResult` with `spec`, `dataset`, `fusion_model`, `plan`, `state`, and `blockers`.
- `models/multimodal/fusion_model.py` must keep rejecting empty or malformed modality contracts and preserve provenance in its result object.
- `models/multimodal/uncertainty.py` must keep accepting the fusion contract and surfacing confidence/uncertainty without collapsing malformed payloads into a clean-looking success.
- `evaluation/multimodal/metrics.py` must keep producing JSON-ready summary metrics for the landed multimodal contract.

### 3. Benchmark-dependent components

These are not ready until the benchmark corpus is assembled and exercised:

- The frozen 12-accession benchmark bundle.
- The accession-level `8/2/2` split labels.
- The mixed rich/moderate/sparse cohort assembly.
- The cohort-wide enrichment pulls for the non-smoke accessions.
- The unattended checkpointed benchmark run and its replay/resume behavior.

## Decision Criteria

The report should classify the flagship model as ready only if all of the following are true:

1. The integration path still passes with explicit provenance and explicit missingness.
2. The packaging/materialization path preserves accession-level identity and does not silently widen or repartition examples.
3. The benchmark corpus exists as a pinned, reproducible cohort rather than only as smoke evidence.
4. The final multimodal summary is JSON-ready and does not mask partial or unresolved states.
5. Any unsupported or missing modality remains visible as a blocker, note, or partial state rather than being coerced into success.

If any of those checks fail, the report should state that the stack is not yet fully ready and should name the exact missing layer.

## Recommended Report Structure

Use this structure for `docs/reports/flagship_model_readiness.md` when P5-I014 is finalized:

1. Bottom line.
2. What is already proven.
3. What still depends on integration.
4. What still depends on the benchmark corpus.
5. Evidence table with repo references.
6. Failure surfaces and open gaps.
7. Final readiness call.

## Evidence Basis

The outline is anchored in the current repo evidence:

- `docs/reports/flagship_pipeline_integration_plan_2026_03_22.md`
- `docs/reports/benchmark_corpus_manifest_2026_03_22.md`
- `docs/reports/package_materialization_notes.md`
- `docs/reports/real_data_benchmark_plan_2026_03_22.md`
- `docs/reports/annotation_pathway_live_smoke_2026_03_22.md`
- `docs/reports/bindingdb_live_smoke_2026_03_22.md`
- `docs/reports/ppi_live_smoke_2026_03_22.md`
- `docs/reports/evolutionary_live_smoke_2026_03_22.md`
- `docs/reports/live_source_smoke_2026_03_22.md`
- `tests/integration/test_storage_runtime.py`
- `tests/integration/test_training_package_materialization.py`
- `tests/unit/training/test_multimodal_train.py`
- `tests/unit/models/test_fusion_model.py`
- `tests/unit/models/test_uncertainty.py`
- `tests/unit/evaluation/test_multimodal_metrics.py`

## Notes On Honesty

Do not overstate readiness. The current repo has meaningful building blocks and live-source validation, but the flagship model should still be described as integration-dependent until the P5 gates and benchmark corpus are both satisfied.
