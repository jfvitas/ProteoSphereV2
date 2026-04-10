# Release Model Card

- Status: `report-only`
- Benchmark kind: `truthful_portfolio_inventory_over_real_artifacts`
- Runtime surface: `local prototype runtime with surrogate modality embeddings and identity-safe resume continuity`
- Benchmark truth boundary: `{"coverage_not_validation": true, "forbidden_overclaims": ["production-equivalent runtime", "separate independent family sweeps", "full corpus success without output artifacts", "silent cohort widening", "silent leakage across splits"], "identity_safe_resume": true, "prototype_runtime": true, "release_grade_corpus_validation": false}`
- Release readiness: `no_go`
- Release ready count: `0`
- Blocked count: `12`

## Evidence Sources
- `release_bundle_manifest`: `D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/release_bundle_manifest.json`
- `release_support_manifest`: `D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/release_support_manifest.json`
- `release_corpus_evidence_ledger`: `D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/release_corpus_evidence_ledger.json`
- `source_coverage`: `D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/source_coverage.json`

## Candidate Families
| Rank | Family | Status | Observed fit | Blockers |
| --- | --- | --- | --- | --- |
| 1 | conservative_fusion_baseline | proxy_derived | best match for the current prototype runtime and frozen cohort | packet_not_materialized; modalities_incomplete; ligand_gap; ppi_gap |
| 2 | sequence_first_with_missingness_heads | proxy_derived | best for thin and blocked rows because it preserves explicit failure states | thin_coverage; packet_not_materialized |
| 3 | sequence_structure_ppi_direct_lane | proxy_derived | useful for rich anchors, but bridge-only evidence must stay bridge-only | bridge_only_evidence; packet_not_materialized |
| 4 | ligand_anchored_subportfolio | proxy_derived | best fit for assay-linked examples such as P31749 | ligand_gap; packet_not_materialized |
| 5 | thin_row_control_portfolio | proxy_derived | required to measure honest failure on sparse and verified-accession rows | thin_coverage; packet_not_materialized |
| 6 | mixed_evidence_stress_portfolio | proxy_derived | best for mixed-evidence rows like P68871, provided the mixed state stays explicit | mixed_evidence; packet_not_materialized |

## Ablation Order
- Step 1: `full_conservative_fusion_baseline`
- Step 2: `remove_ligand_lane`
- Step 3: `remove_ppi_lane`
- Step 4: `remove_structure_lane`
- Step 5: `sequence_only_control`
- Step 6: `restore_one_lane_at_a_time_on_strong_anchors`

## Measurable Results
- Direct live smoke accessions: `P69905`, `P04637`, `P31749`
- Probe-backed accessions: `P68871`
- Snapshot-backed accessions: `Q9NZD4`, `Q2TAC2`, `P00387`, `P02042`, `P02100`, `P69892`
- Verified accession controls: `P09105`, `Q9UCM0`

## Truth Boundary
- production-equivalent runtime
- release-grade corpus validation
- full corpus success without pinned outputs
- silent cohort widening
- silent leakage across splits
- separate independent family sweeps
- The portfolio is proxy-derived, not production-equivalent.
- The benchmark is an inventory over real artifacts, not corpus-scale validation.
- The current recommendation is `no_go`.

## Supporting Context
- Coverage not validation: `true`
- Ledger release-ready count: `0`
