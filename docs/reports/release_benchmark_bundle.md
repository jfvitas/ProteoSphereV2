# Release Benchmark Bundle

Date: 2026-03-22
Task: `P6-T032`
Status: `assembled_with_blockers`

## Bottom Line

This bundle is a truthful release-facing package for the frozen 12-accession benchmark cohort. It is assembled from pinned in-tree artifacts, and `schema.json` is a required release artifact rather than a supporting convenience pin.

schema.json is a required release artifact.

The bundle is not a release-grade claim. It remains bounded by the local prototype runtime and the existing blocker categories.

## Required Release Artifacts

- `runs/real_data_benchmark/full_results/provenance_table.json`
- `runs/real_data_benchmark/full_results/source_coverage.json`
- `runs/real_data_benchmark/full_results/leakage_audit.json`
- `runs/real_data_benchmark/full_results/metrics_summary.json`
- `runs/real_data_benchmark/full_results/schema.json`
- `docs/reports/release_grade_gap_analysis.md`

## Supporting Pins

- `runs/real_data_benchmark/full_results/run_manifest.json`
- `runs/real_data_benchmark/full_results/run_summary.json`
- `runs/real_data_benchmark/full_results/checkpoint_summary.json`
- `runs/real_data_benchmark/full_results/live_inputs.json`
- `runs/real_data_benchmark/full_results/summary.json`
- `runs/real_data_benchmark/full_results/README.md`
- `runs/real_data_benchmark/full_results/checkpoints/full-cohort-trainer.json`
- `runs/real_data_benchmark/full_results/logs/full_rerun_stdout.log`
- `runs/real_data_benchmark/cohort/cohort_manifest.json`
- `runs/real_data_benchmark/cohort/split_labels.json`

## What The Bundle Shows

- The cohort is frozen at 12 accessions with 12 resolved and 0 unresolved.
- Split hygiene is accession-level only with 8 train, 2 val, and 2 test accessions.
- Leakage audit is clean: no cross-split accessions and no cross-split leakage keys.
- Source coverage is explicit and conservative, but several accessions remain thinly covered.
- The benchmark run completed on the local prototype runtime with identity-safe checkpoint resume.
- The metrics pack records the partial-then-resume execution, the frozen cohort scope, and the prototype runtime boundary.

## Blocker Categories

The bundle preserves the blocker categories from the release gap analysis:

- runtime maturity
- source coverage depth
- provenance/reporting depth

## Truth Boundary

This bundle does not claim:

- production-equivalent runtime
- release-grade provenance
- corpus-scale success beyond the frozen benchmark artifacts currently in tree
- silent widening of the cohort or hidden leakage across splits

## Bundle Notes

- `schema.json` is a required release artifact and should be treated as part of the bundle contract.
- The completed provenance and leakage artifacts are treated as pinned evidence, not as a replacement for a release-grade trainer/runtime.
- The current benchmark surface is still bounded by the in-tree frozen cohort and the locally materialized prototype results.
