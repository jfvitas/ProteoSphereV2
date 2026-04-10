# Real Data Benchmark Report

Date: 2026-03-22
Task: `P6-I007`
Manifest: `benchmark-corpus-manifest-2026-03-22`
Plan: `docs/reports/real_data_benchmark_plan_2026_03_22.md`

## Findings

- The full corpus-scale benchmark could not be truthfully executed from this workspace because the required package-validation path is still incomplete: `P5-I013` remains dispatched, `tests/integration/test_multimodal_package_flow.py` is not present in-tree, and `runs/real_data_benchmark/` does not contain a benchmark bundle, checkpoints, or logs yet.
- The strongest truthful validation proxy passed. A focused suite covering the flagship pipeline, summary library, storage runtime, package materialization, multimodal training, fusion, uncertainty, and multimodal metrics passed `17/17` tests in `4.01s`.
- Style-only issues remain in the proxy slice. Ruff reported `5` existing `E501` line-length violations in the storage/materialization integration tests. Those did not invalidate the runtime proxy, but they do mean the benchmark-adjacent slice is not lint-clean.

## Run Summary

| Field | Value |
| --- | --- |
| Run ID | `validation-proxy-2026-03-22` |
| Start time | `2026-03-22` |
| End time | `2026-03-22` |
| Wall-clock runtime | `4.01s` for the proxy test suite |
| Pipeline commit / branch | repository workspace state on 2026-03-22 |
| Manifest ID | `benchmark-corpus-manifest-2026-03-22` |
| Cohort size | `12` planned; not corpus-materialized in this workspace |
| Split policy | accession-level only |
| Split counts | not materialized |
| Overall status | `partial / blocked` |

## Inputs And Pins

| Input | Pinned value | Notes |
| --- | --- | --- |
| Benchmark plan | `docs/reports/real_data_benchmark_plan_2026_03_22.md` | scope, statistics, failure criteria |
| Corpus manifest | `docs/reports/benchmark_corpus_manifest_2026_03_22.md` | accession spine and split policy |
| Launch checklist | `runs/real_data_benchmark/checklist_2026_03_22.md` | launch gates and stop conditions |
| Package validation gate | `P5-I013` | still dispatched |
| Live smoke baselines | `docs/reports/*_live_smoke_2026_03_22.md` | pre-run evidence only |

## Live Evidence Baseline

These source lanes were already proven live before this report:

- UniProt anchor retrieval for `P69905`
- InterPro enrichment for `P69905` with `6` returned entries
- Reactome mapping for `P69905` with `6` returned pathway rows
- BindingDB ligand acquisition for `P31749`
- IntAct PPI acquisition for `P04637` with `3` parsed records in the smoke slice
- RCSB/PDBe experimental structure smoke for `1CBS`
- AlphaFold DB smoke for `P69905`
- Evolutionary/MSA smoke seeded from `P69905`

## Validation Proxy

Command run:

```powershell
python -m pytest tests/integration/test_flagship_pipeline.py tests/integration/test_summary_library_real_corpus.py tests/integration/test_storage_runtime.py tests/integration/test_training_package_materialization.py tests/unit/training/test_multimodal_train.py tests/unit/models/test_fusion_model.py tests/unit/models/test_uncertainty.py tests/unit/evaluation/test_multimodal_metrics.py -q
```

Result:

- `17 passed in 4.01s`

Follow-up lint command:

```powershell
python -m ruff check tests/integration/test_flagship_pipeline.py tests/integration/test_summary_library_real_corpus.py tests/integration/test_storage_runtime.py tests/integration/test_training_package_materialization.py tests/unit/training/test_multimodal_train.py tests/unit/models/test_fusion_model.py tests/unit/models/test_uncertainty.py tests/unit/evaluation/test_multimodal_metrics.py
```

Result:

- `5` existing `E501` line-length violations in the integration test slice.

## Residual Limitations

1. The actual 12-accession corpus bundle is not materialized in-tree, so cohort-level statistics, split counts, and leakage checks could not be computed from a real benchmark run.
2. The package-validation prerequisite is not green yet, so the exact end-to-end launch path remains incomplete.
3. No checkpoint/resume evidence was produced for a week-long unattended benchmark run because the benchmark itself was not launched.
4. The proxy validation covers the landed runtime contracts, but it is not a substitute for corpus-scale coverage reporting.

## Decision

The benchmark is not yet complete as a corpus-scale run. The truthful status is:

- runtime contracts: validated by proxy
- corpus benchmark: blocked
- readiness for next wave: `no`

The exact gap is the missing package-validation path plus the absence of a runnable corpus output tree under `runs/real_data_benchmark/`.
