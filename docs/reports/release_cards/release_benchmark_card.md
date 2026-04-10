# Release Benchmark Card

- Status: `report-only`
- Bundle ID: `release-benchmark-bundle-2026-03-22`
- Bundle status: `assembled_with_blockers`
- Support bundle tag: `release-notes:release-benchmark-bundle-2026-03-22@v1`
- Runtime surface: `local prototype runtime with surrogate modality embeddings and identity-safe resume continuity`
- Cohort size: `12`
- Split counts: `{"test": 2, "train": 8, "val": 2}`
- Leakage free: `true`
- Coverage/validation boundary: `true`
- Release-grade corpus validation: `false`
- Ledger release-ready count: `0`
- Ledger blocked count: `12`
- Benchmark readiness: `no_go`

## Evidence Sources
- `release_bundle_manifest`: `D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/release_bundle_manifest.json`
- `release_support_manifest`: `D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/release_support_manifest.json`
- `source_coverage`: `D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/source_coverage.json`
- `release_corpus_evidence_ledger`: `D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/release_corpus_evidence_ledger.json`
- `model_portfolio_benchmark`: `D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/model_portfolio_benchmark.json`
- `metrics_summary`: `D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/metrics_summary.json`
- `run_summary`: `D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/run_summary.json`

## Observed Coverage
- Validation class counts: `{"direct_live_smoke": 3, "probe_backed": 1, "snapshot_backed": 6, "verified_accession": 2}`
- Evidence mode counts: `{"direct_live_smoke": 3, "in_tree_live_snapshot": 6, "live_summary_library_probe": 1, "live_verified_accession": 2}`
- Lane depth counts: `{"1": 10, "2": 1, "5": 1}`
- Direct live smoke accessions: `P69905`, `P04637`, `P31749`
- Probe-backed accessions: `P68871`
- Snapshot-backed accessions: `Q9NZD4`, `Q2TAC2`, `P00387`, `P02042`, `P02100`, `P69892`
- Verified accession controls: `P09105`, `Q9UCM0`

## What This Card Supports
- A report-only inventory of the frozen 12-accession benchmark cohort.
- Accessions are tracked at accession granularity only; no silent cohort widening.
- Coverage is described as evidence coverage, not corpus-scale validation.
- Mixed evidence remains explicitly mixed evidence.

## What This Card Does Not Claim
- production-equivalent runtime
- release-grade corpus validation
- full corpus success without pinned outputs
- silent cohort widening
- silent leakage across splits
- separate independent family sweeps

## Blockers
- runtime maturity
- source coverage depth
- provenance/reporting depth

## Truth Boundary
- Allowed statuses: `["assembled_with_blockers", "blocked"]`
- Forbidden overclaims: `["production-equivalent runtime", "release-grade provenance without blocker categories", "full corpus success without pinned outputs", "silent cohort widening", "silent leakage across splits"]`
- Coverage not validation: `true`
