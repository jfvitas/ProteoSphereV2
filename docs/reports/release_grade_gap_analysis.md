# Release-Grade Benchmark Gap Analysis

Date: 2026-03-22  
Task: `P6-A020`  
Scope: release-grade claim for the real-data benchmark path grounded in the frozen cohort, harnessed rerun, and current benchmark reports.

## Bottom Line

The benchmark is **not release-grade yet**.

The hard execution questions are mostly answered: the frozen cohort is pinned, split leakage is clean, the harnessed 12-accession rerun completed, and resume continuity is identity-safe in the current full-results tree. What still blocks a release-grade benchmark claim is the **depth and completeness of the runtime and reporting surface**:

1. the runtime is still explicitly a local prototype with surrogate modality embeddings,
2. source coverage/reporting is still thinner than the release bar, and
3. the provenance / lineage surface is not yet complete enough for a corpus-scale release claim.

That means the honest label today is **prototype-ready next-wave benchmark**, not release-grade benchmark.

## What Is Already Release-Ready

These pieces are no longer the reason to block the claim:

- The cohort is frozen at `12` accessions with `12` resolved and `0` unresolved.
- Split hygiene is accession-level only, with `8 train / 2 val / 2 test`.
- No duplicate accessions appear across splits.
- The harnessed rerun completed on the frozen cohort.
- Checkpoint resume continuity is identity-safe in the produced results.
- The output schema is pinned in the benchmark results artifacts.

| Area | Evidence | Status |
| --- | --- | --- |
| Frozen cohort | `runs/real_data_benchmark/cohort/cohort_manifest.json` | `12` resolved, `0` unresolved |
| Split hygiene | `runs/real_data_benchmark/cohort/cohort_manifest.json`, `runs/real_data_benchmark/cohort/split_labels.json` | `8/2/2`, no duplicate or cross-split accessions |
| Harnessed execution | `runs/real_data_benchmark/full_results/run_summary.json` | run completed with `2` checkpoint writes and `1` resume |
| Identity-safe resume | `runs/real_data_benchmark/full_results/checkpoint_summary.json` | `resume_continuity: identity-safe` |
| Pinned output schema | `runs/real_data_benchmark/full_results/schema.json` | benchmark result layout is fixed |

## Must-Fix Blockers

### 1. Runtime maturity is still prototype-only

The harnessed benchmark ran on a local prototype runtime, not the final release trainer surface. The results themselves say this directly, and the run manifest still describes surrogate modality embeddings.

Why this blocks the release-grade claim:

- a release-grade benchmark needs results from the intended trainer/runtime contract, not a prototype stand-in,
- the current runtime is good enough to prove orchestration and continuity,
- it is not yet the final evidence source for model quality or operational readiness.

Evidence:

- `runs/real_data_benchmark/full_results/run_manifest.json`
- `runs/real_data_benchmark/full_results/summary.json`
- `runs/real_data_benchmark/full_results/run_summary.json`
- `docs/reports/real_data_benchmark_harnessed_rerun.md`

### 2. Source coverage depth is still incomplete

The harnessed run does not yet provide the full corpus-scale source coverage surface expected for a release-grade benchmark claim. The run summary and blocker summary both say source coverage remains thinner than the final bar, and the explicit sidecar coverage is still narrow.

Why this blocks the release-grade claim:

- a release-grade benchmark needs source-lane coverage that is broad enough to support the frozen cohort truthfully,
- missing lanes must be counted and explained, not inferred away,
- the current results still read like a completed probe / harnessed pass rather than a full benchmark report.

Evidence:

- `runs/real_data_benchmark/full_results/summary.json`
- `runs/real_data_benchmark/full_results/run_summary.json`
- `docs/reports/real_data_benchmark_harnessed_rerun.md`
- `runs/real_data_benchmark/full_results/README.md`

### 3. Provenance and lineage reporting are not yet complete enough

The current artifacts prove the run happened and that resume continuity is identity-safe, but they do not yet provide the full release-grade provenance package: corpus-scale lineage tables, explicit unresolved/conflict accounting, source failure counts, and a complete truth boundary for every retained record.

Why this blocks the release-grade claim:

- the benchmark must be auditable end to end,
- provenance must stay attached to the cohort and each output lane,
- unresolved or conflicting cases must remain explicit in the final report, not only in supporting notes.

Evidence:

- `runs/real_data_benchmark/full_results/checkpoint_summary.json`
- `runs/real_data_benchmark/full_results/run_summary.json`
- `docs/reports/real_data_benchmark_harnessed_rerun.md`
- `artifacts/reviews/p6_i012_provenance_review_2026_03_22.md`

## Nice-To-Have, But Not Release Gates

These items would improve confidence and usability, but they do not change the current blocker ranking:

- richer operator-facing summaries for the benchmark run tree,
- broader source-lane exemplars beyond the current hemoglobin-centered sidecar evidence,
- additional stress or endurance passes after the first truthful corpus run,
- more polished reporting around source-by-source retries and failure classes.

## Ranked Blocker List

| Rank | Severity | Blocker | Why It Matters |
| --- | --- | --- | --- |
| 1 | Must-fix | Runtime maturity | The benchmark still runs on a prototype runtime with surrogate embeddings, so the evidence is not yet release-grade. |
| 2 | Must-fix | Source coverage depth | The output surface is still thinner than the release bar and does not yet read as a fully reported benchmark corpus. |
| 3 | Must-fix | Provenance / lineage reporting | The final evidence package still needs auditable corpus-scale provenance, unresolved/conflict surfacing, and failure accounting. |
| 4 | Nice-to-have | Broader operator/report polish | Useful for maintainability, but not a blocker once the three must-fix items are closed. |

## Final Readiness Call

**Release-grade benchmark claim: no.**

**Current best label: prototype-ready next-wave benchmark with a truthful frozen cohort and a completed harnessed rerun, but not yet a release-grade corpus claim.**

The benchmark is now far enough along that the next work should focus on closing the remaining evidence gaps, not re-litigating cohort truthfulness or split hygiene.
