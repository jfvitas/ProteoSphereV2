# P19 Model Portfolio Benchmark

Date: 2026-03-22  
Task: `P19-I007`

## Bottom Line

This benchmark wave is a truthful portfolio readout over real artifacts, not a claim of separate production-grade model sweeps.

The only fully executed runtime surface remains the frozen 12-accession prototype benchmark run from [run_summary.json](/D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/run_summary.json) and [checkpoint_summary.json](/D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/checkpoint_summary.json). The phase-19 baselines are now landed and benchmarkable, but their portfolio comparison is still proxy-derived from real evidence lanes, blocker classes, and the identity-safe replay path.

## What Was Actually Benchmarked

The benchmarked evidence surface is the frozen benchmark cohort and its replay artifacts:

- 12 resolved accessions with accession-level leakage control.
- 8 train, 2 val, 2 test split counts with no cross-split duplicates.
- 1 checkpoint resume over the same checkpoint ref and path.
- 2 checkpoint writes.
- 3 direct live-smoke accessions, 1 probe-backed accession, 6 snapshot-backed accessions, and 2 verified-accession controls.

The runtime stayed inside the current truth boundary:

- local prototype runtime with surrogate modality embeddings,
- identity-safe resume continuity,
- explicit partiality and blocker visibility,
- no release-grade corpus validation claim.

## Candidate Families

These families are ranked from the phase-19 portfolio matrix in [p19_model_portfolio_matrix.md](/D:/documents/ProteoSphereV2/docs/reports/p19_model_portfolio_matrix.md). They are benchmarked here as evidence-aware candidates, not as separate production training runs.

1. Conservative fusion baseline. Sequence + structure + ligand + ppi. Best supported by the current prototype run surface, but still blocked on missing corpus-scale packetization and incomplete PPI depth.
2. Sequence-first with explicit missingness heads. Sequence + missingness metadata. Best fit for thin rows and honest failure preservation.
3. Sequence + structure + PPI direct lane. Best for rich anchors like `P69905`, `P68871`, and `P04637`, but still requires strict bridge-only vs direct-evidence separation.
4. Ligand-anchored subportfolio. Sequence + ligand + PPI. Best fit for `P31749` and other assay-linked examples.
5. Thin-row control portfolio. Sequence-only or sequence + one extra lane. Required for the sparse/control rows.
6. Mixed-evidence stress portfolio. Sequence + PPI + ligand with explicit mixed evidence. Useful for `P68871`-style rows where mixed support is a feature, not a bug.

## Ablation Order

The recommended ablation order remains:

1. Full conservative fusion baseline.
2. Remove ligand lane.
3. Remove PPI lane.
4. Remove structure lane.
5. Sequence-only control.
6. Restore one lane at a time on the strongest anchors.

That ordering is still the cleanest way to preserve interpretability under the current prototype boundary.

## Measurable Results

The measurable results available today are from the completed prototype run, not from independent family-specific training sweeps:

- `run_id`: `multimodal-run:c6ff74a7fb07cdcf`
- `checkpoint_ref`: `checkpoint://multimodal-run:c6ff74a7fb07cdcf/package-real-data-benchmark-full-2026-03-22-2026-03-22-seed-0019`
- `checkpoint_resume_count`: `1`
- `checkpoint_write_count`: `2`
- `processed_examples`: `12`
- `resolved_accessions`: `12`
- `split_counts`: `8 train / 2 val / 2 test`
- `direct_live_smoke_accessions`: `P69905`, `P04637`, `P31749`
- `probe_backed_accessions`: `P68871`
- `snapshot_backed_accessions`: `Q9NZD4`, `Q2TAC2`, `P00387`, `P02042`, `P02100`, `P69892`
- `verified_accession_controls`: `P09105`, `Q9UCM0`
- `loss_mean_first_run`: `0.07223631432937218`
- `loss_mean_resumed_run`: `0.053861256037867226`

The release corpus evidence ledger stays blocked:

- `release_ready_count`: `0`
- `blocked_count`: `12`
- blocker classes still present: `packet_not_materialized`, `modalities_incomplete`, `thin_coverage`, `ligand_gap`, `ppi_gap`, `mixed_evidence`.

## What Is Proxy-Derived

The following parts are proxy-derived from real artifacts and landed baselines, but not separately executed as independent benchmark runs:

- per-family ranking of the six candidate families,
- the ablation ordering,
- the interpretation of lane depth and blocker visibility as benchmark utility signals,
- the recommendation that the conservative fusion baseline remains the best truth-preserving default.

That proxy derivation is intentional and should stay labeled that way until the separate family sweeps exist.

## What Remains Blocked

- The runtime is still a local prototype, not the production multimodal trainer stack.
- PPI evidence remains sparse and partially sidecar-backed.
- Several rows remain thin or verified-accession only.
- The release corpus ledger is still fully blocked.
- No separate benchmark sweep has been run for each candidate family.

## Recommended Next Move

Keep the phase-19 benchmark program focused on two parallel tracks:

- continue building the real family-specific benchmark runner around the landed baselines,
- keep procuring and materializing the missing evidence lanes so the next benchmark wave can compare families on real runs instead of proxy ordering.

Until then, the right release-safe interpretation is simple: the prototype run is reproducible, the cohort is leakage-ready, and the portfolio ranking is useful for planning, but it is not yet a release-grade benchmark sweep.
