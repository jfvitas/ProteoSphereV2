# Multimodal Package Notes

Date: 2026-03-22
Task: `P5-I013`

## Scope

This note records the first truthful validation of the selected-example multimodal package flow on top of the landed flagship pipeline and package/runtime path.

The validation stayed deliberately narrow:

- one selected-example package
- one explicit PPI representation
- the landed sequence, structure, and ligand embedding inputs
- the current training contract, which is still blocked at `trainer_runtime`

It does not claim corpus-scale benchmark coverage. The broader benchmark shape is still the 12-accession accession-level cohort described in `docs/reports/real_data_benchmark_plan_2026_03_22.md` and `docs/reports/benchmark_corpus_manifest_2026_03_22.md`.

## Evidence Basis

The packaging note is aligned to the current repo evidence:

- `docs/reports/real_data_benchmark_plan_2026_03_22.md`
- `docs/reports/benchmark_corpus_manifest_2026_03_22.md`
- `docs/reports/live_source_smoke_2026_03_22.md`
- `docs/reports/ppi_live_smoke_2026_03_22.md`
- `docs/reports/flagship_pipeline_integration_plan_2026_03_22.md`

The live-smoke evidence matters here mainly as a guardrail: it confirms the repo already has real-source anchors for the accession spine and interaction lane, but this validation is still only a package-flow check on one selected example.

## What The Validation Proved

### Validated example

- `package_id`: `package-1`
- `example_id`: `example-1`
- `ppi_summary_id`: `ppi-summary-1`
- canonical proteins: `protein:P69905`, `protein:P68871`
- requested modalities: `sequence`, `structure`, `ligand`, `ppi`

### Selected-example scope

- The storage runtime keeps the package scope to one selected example.
- The package build preserves that same selected-example list.
- The multimodal dataset and training result still point at the same single example.
- The flagship pipeline does not widen the scope behind the scenes.

### Package completeness

- The runtime reaches `integrated` for the synthetic package-shaped input.
- The selective materialization step reaches `materialized`.
- The package build reaches `built`.
- The PPI lane is present in the ready path when a PPI representation is supplied.
- The flagship pipeline remains `partial` only because the trainer runtime is still contract-plan-only.

### Missing-input handling

- When the PPI representation is omitted, the dataset becomes `partial`.
- The missing PPI lane is recorded explicitly as `missing_ppi_representation_record`.
- The training plan records `ppi` as a missing modality.
- The pipeline stays truthful about the gap instead of flattening it into success.

## Practical Interpretation

This is enough to hand off the package/runtime substrate to the benchmark wave, because it verifies the repository can carry a selected-example package through runtime assembly, multimodal dataset adaptation, training-plan construction, and the flagship wrapper without losing provenance or scope.

What it does not prove yet:

- corpus-scale accession batching
- split hygiene across multiple accessions
- long-running checkpoint resume behavior
- real trainer execution

Those remain the next benchmark wave.

## Verification Commands

- `python -m pytest tests\\integration\\test_multimodal_package_flow.py`
- `python -m ruff check tests\\integration\\test_multimodal_package_flow.py`

## Outcome

The package-flow validation is green for the selected-example path and remains honest about the explicit missing-PPI path.

Final verification passed:

- `python -m pytest tests\\integration\\test_multimodal_package_flow.py`
- `python -m ruff check tests\\integration\\test_multimodal_package_flow.py`
