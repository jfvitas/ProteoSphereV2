# Release Data Card

- Status: `report-only`
- Registry ID: `release-cohort:prototype-frozen-12`
- Release version: `0.9.0-prototype`
- Freeze state: `draft`
- Ledger entry count: `12`
- Included count: `12`
- Blocked count: `12`
- Release-ready count: `0`
- Coverage not validation: `true`

## Evidence Sources
- `release bundle manifest`: `D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/release_bundle_manifest.json`
- `release support manifest`: `D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/release_support_manifest.json`
- `release corpus evidence ledger`: `D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/release_corpus_evidence_ledger.json`
- `source_coverage`: `D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/source_coverage.json`
- `metrics_summary`: `D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/metrics_summary.json`
- `run_summary`: `D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/run_summary.json`

## Coverage Classes
| Validation class | Count |
| --- | --- |
| direct_live_smoke | 3 |
| probe_backed | 1 |
| snapshot_backed | 6 |
| verified_accession | 2 |

## Data Inventory
- Evidence mode counts: `{"direct_live_smoke": 3, "in_tree_live_snapshot": 6, "live_summary_library_probe": 1, "live_verified_accession": 2}`
- Lane depth counts: `{"1": 10, "2": 1, "5": 1}`
- Thin coverage accessions: `P04637`, `P31749`, `Q9NZD4`, `Q2TAC2`, `P00387`, `P02042`, `P02100`, `P69892`, `P09105`, `Q9UCM0`
- Mixed evidence accessions: `P68871`
- Verified accession accessions: `P09105`, `Q9UCM0`

## What This Card Supports
- A blocked-only evidence ledger for the frozen cohort.
- Coverage accounting by validation class and lane depth.
- Conservative provenance and reporting depth checks.

## What This Card Does Not Claim
- production-equivalent runtime
- release-grade corpus validation
- full corpus success without pinned outputs
- silent cohort widening
- silent leakage across splits
- separate independent family sweeps
- No row is promoted to release-ready in this ledger.
- Coverage is intentionally not treated as validation.

## Truth Boundary
- Release-grade corpus validation: `false`
- Ledger blocked count: `12`
- Ledger release-ready count: `0`
