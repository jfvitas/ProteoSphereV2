# Flagship Model Readiness

Date: 2026-03-22
Task: `P5-I014`

## Bottom Line

The repository is **not release-ready for the flagship model itself**.
The supporting infrastructure is release-ready, and the multimodal contract path is prototype-ready, but the model remains blocked by two missing depths:

- the training runtime is still contract-plan-only
- the benchmark corpus has not yet been assembled and executed as a real 12-accession run

Dependency callout:

- `P5-I012` is green and proves the flagship pipeline contract path.
- `P5-I013` is green and proves selected-example multimodal package flow.
- `P6-I007` remains blocked until the real benchmark corpus is actually executed.

That is the honest state after the landed flagship pipeline, the multimodal package-flow validation, and the live-data smoke evidence.

## Findings

- **High**: `training/multimodal/train.py` still returns a deterministic plan with a `trainer_runtime` blocker rather than a real trainer loop. The flagship pipeline is therefore an end-to-end contract wrapper, not a shipped training system.
- **High**: the benchmark corpus is still a manifest and plan, not a completed run. The repo has a pinned cohort design, but no full real-data benchmark execution yet, so no flagship-readiness claim can rest on corpus-scale evidence.
- **Medium**: multimodal packaging is validated only on a single selected example. That proves scope preservation, provenance threading, and explicit missing-PPI handling, but not corpus-scale completeness.
- **Medium**: the live-source evidence is broad, but it is still smoke-scale. It validates source-path truthfulness, parser normalization, and lane coverage, not the unattended benchmark behavior needed for release confidence.

## Release-Ready Infrastructure

These pieces are ready to use as infrastructure:

- selected-example storage/runtime assembly and package materialization
- summary-library schema, protein-pair cross-reference indexing, and explicit unresolved surfacing
- live-data source acquisition smoke for UniProt, InterPro, Reactome, BindingDB, IntAct, RCSB / PDBe, AlphaFold DB, and evolutionary / MSA
- operator-facing inspection surfaces for queue, library, and runtime state
- deterministic GPU scheduling policy for the current runtime surface

The important distinction is that this is infrastructure readiness, not flagship-model readiness.

## Prototype-Ready Multimodal Path

The multimodal stack is prototype-ready because the contract surfaces are now stable and integrated:

- sequence, structure, and ligand encoders are landed
- the multimodal dataset adapter preserves selected-example scope and explicit PPI missingness
- the training entrypoint emits deterministic `spec`, `dataset`, `fusion_model`, `plan`, `state`, and `blockers`
- the flagship pipeline threads storage/runtime, fusion, uncertainty, metrics, GPU policy, and experiment registry
- the multimodal package-flow validation is green on one selected example and keeps missing PPI input explicit

This is enough to support experimentation and downstream packaging, but not enough to call the model released.

## Blocked Depth

The flagship model is still blocked by:

- a real multimodal trainer runtime under `training/multimodal`
- a completed real-data benchmark corpus and the first corpus-scale execution wave
- unattended checkpoint/resume evidence over the benchmark population
- corpus-level split hygiene and leakage reporting

The benchmark report template exists, and the benchmark plan is pinned, but the run itself is still pending.

## Evidence Table

| Area | Evidence | Status | Readiness Impact |
| --- | --- | --- | --- |
| Flagship pipeline | `execution/flagship_pipeline.py`, `tests/integration/test_flagship_pipeline.py` | prototype-ready | runs end to end only as a contract path; trainer runtime remains blocked |
| Multimodal package flow | `tests/integration/test_multimodal_package_flow.py`, `docs/reports/multimodal_package_notes.md` | prototype-ready | selected-example scope is preserved and missing PPI input stays explicit |
| Storage/runtime + materialization | `tests/integration/test_storage_runtime.py`, `tests/integration/test_training_package_materialization.py` | release-ready infrastructure | package scope, provenance, and selected-example materialization are conservative |
| Live source validation | `docs/reports/live_source_smoke_2026_03_22.md`, `docs/reports/ppi_live_smoke_2026_03_22.md`, `docs/reports/bindingdb_live_smoke_2026_03_22.md` | release-ready smoke | real source paths are proven on tiny probes: `P69905`, `P04637`, `P31749`, `1CBS` |
| Benchmark corpus | `docs/reports/real_data_benchmark_plan_2026_03_22.md`, `docs/reports/benchmark_corpus_manifest_2026_03_22.md`, `docs/reports/real_data_benchmark_report_template_2026_03_22.md` | blocked | corpus is pinned in plan/manifest form, but no real run exists yet |

## What Is Genuinely Release-Ready

Release-ready means the repo can safely support the flagship effort without hiding missingness:

- selected-example packaging and runtime materialization
- provenance-preserving summary and cross-reference handling
- live source acquisition surfaces for the core accession spine and interaction lanes
- queue/library/runtime inspection
- GPU policy gating

Those pieces are usable now.

## What Is Prototype-Ready

Prototype-ready means the multimodal contract path works, but the runtime is still a prototype:

- the flagship pipeline runs through dataset, fusion, uncertainty, metrics, and registry
- the training contract remains deterministic and JSON-ready
- the package-flow validation proves scope and missing-input honesty
- the encoders and fusion head are stable enough for integration and benchmark preparation

That is the correct label for the flagship multimodal path today.

## What Remains Blocked

The following are still not ready for release claims:

- a real multimodal trainer runtime
- full benchmark execution over the pinned 12-accession cohort
- week-long unattended benchmark stability
- corpus-scale split hygiene and leakage reporting

The live-smoke evidence is strong enough to support the next wave, but not enough to replace it.

## Final Readiness Call

**Overall verdict: prototype-ready, not release-ready.**

The repository now has a strong supporting infrastructure layer and a working flagship contract path, but the actual flagship model remains blocked until real trainer depth and real-data benchmark execution are both present.
