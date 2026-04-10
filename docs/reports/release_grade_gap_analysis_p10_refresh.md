# Release-Grade Gap Analysis Refresh

Date: 2026-03-22  
Scope: post-`P11-T001`, `P11-T002`, and `P11-T005` refresh

## Bottom Line

The release-grade benchmark claim is still **not** justified, but the blocker picture is narrower and more specific than it was in the original gap analysis.

The current artifacts now prove three important things:

- checkpoint/resume identity is fail-closed and stable,
- the experiment registry preserves executable runtime identity instead of collapsing it back to plan-only defaults,
- the operator surface now exposes a real materialized summary library when the artifact actually exists.

Those landings remove the older operator/registry ambiguity from the top of the list. What remains blocking is the benchmark evidence itself: runtime maturity, source coverage depth, and corpus-scale evidence completeness.

## What Changed Since the Original Analysis

- [P11-T001](/D:/documents/ProteoSphereV2/artifacts/status/P11-T001.json) hardened checkpoint persistence and identity checks.
- [P11-T002](/D:/documents/ProteoSphereV2/artifacts/status/P11-T002.json) now preserves executable runtime identity in the experiment registry.
- [P11-T005](/D:/documents/ProteoSphereV2/artifacts/status/P11-T005.json) now reports the materialized summary library as a concrete artifact-backed object instead of a readiness placeholder.
- [P11-I003](/D:/documents/ProteoSphereV2/docs/reports/flagship_executable_runtime_regression.md) confirms the flagship runtime path is identity-safe and fail-closed on resume mismatch.

## Updated Blocker Ordering

| Rank | Severity | Blocker | Why It Still Matters |
| --- | --- | --- | --- |
| 1 | Must-fix | Runtime maturity and corpus-scale execution completeness | The benchmark still runs on the local prototype surface with surrogate modality embeddings, and the current corpus rerun remains partial rather than a production-equivalent benchmark execution. |
| 2 | Must-fix | Source coverage depth | The coverage artifact is conservative and truthful, but most accessions remain thinly covered, so the benchmark cannot claim release-grade corpus validation yet. |
| 3 | Must-fix | Corpus-scale evidence completeness | The current benchmark artifacts still read as a frozen, launchable, truth-preserving corpus package with partial rerun evidence, not a fully auditable release corpus with complete lineage and failure accounting. |
| 4 | Follow-up | Operator/library parity follow-through | The materialized summary library now exists in the operator contract, so this is no longer a release blocker, but parity validation should continue as a supporting regression gate. |

## Evidence For the Top Three

### 1. Runtime maturity and corpus-scale execution completeness

The benchmark outputs still describe a prototype execution surface rather than the release trainer stack:

- [runs/real_data_benchmark/full_results/run_summary.json](/D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/run_summary.json)
- [runs/real_data_benchmark/full_results/checkpoint_summary.json](/D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/checkpoint_summary.json)
- [runs/real_data_benchmark/full_results/run_manifest.json](/D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/run_manifest.json)

The current benchmark summary still says the runtime surface is a local prototype with surrogate modality embeddings and identity-safe resume continuity, and the full-results tree remains bounded by the frozen cohort rather than a production trainer stack.

### 2. Source coverage depth

The coverage matrix is now explicit about its semantics, which is good, but it is still an inventory rather than release-grade validation:

- [runs/real_data_benchmark/full_results/source_coverage.json](/D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/source_coverage.json)
- [docs/reports/release_artifact_hardening.md](/D:/documents/ProteoSphereV2/docs/reports/release_artifact_hardening.md)

The matrix still concentrates most accessions into single-lane rows. The only deep anchor is `P69905`, with `P68871` remaining probe-backed and ten accessions still effectively thin. That is enough for a truthful benchmark inventory, but not enough for a release-grade coverage claim.

### 3. Corpus-scale evidence completeness

The current bundle is now honest and launchable, but it still does not read like a complete release corpus:

- [docs/reports/benchmark_release_validation.md](/D:/documents/ProteoSphereV2/docs/reports/benchmark_release_validation.md)
- [docs/reports/release_artifact_hardening.md](/D:/documents/ProteoSphereV2/docs/reports/release_artifact_hardening.md)
- [artifacts/reviews/p11_i003_regression_prep_2026_03_22.md](/D:/documents/ProteoSphereV2/artifacts/reviews/p11_i003_regression_prep_2026_03_22.md)

The remaining gap is not a single missing file. It is the absence of a corpus-wide provenance/failure accounting surface that would let us treat the benchmark as a release corpus rather than a truthful but partial benchmark package.

## What Is No Longer a Top-Level Blocker

- The experiment registry no longer collapses executable runs back into prototype-only defaults. See [artifacts/reviews/p11_t002_experiment_registry_review_2026_03_22.md](/D:/documents/ProteoSphereV2/artifacts/reviews/p11_t002_experiment_registry_review_2026_03_22.md) and [training/runtime/experiment_registry.py](/D:/documents/ProteoSphereV2/training/runtime/experiment_registry.py).
- The operator surface no longer needs to pretend the materialized summary library is only a readiness hint. See [P11-T005](/D:/documents/ProteoSphereV2/artifacts/status/P11-T005.json).

## Updated Readiness Call

**Release-grade benchmark claim: still no.**

The strongest honest label is now:

> truthful frozen benchmark package with executable runtime identity, materialized library visibility, and conservative source coverage semantics, but still not a release-grade corpus benchmark.

## Next Steps

1. Finish the corpus-scale execution story so the benchmark is no longer only a prototype runtime plus partial rerun evidence.
2. Deepen the thin source lanes, especially the single-lane rows and the probe-backed `P68871` row, so the coverage matrix can support stronger claims.
3. Add corpus-wide provenance and failure-accounting reporting that names unresolved or partially supported evidence explicitly.
4. Keep the operator/library parity regression in place as a supporting gate, but do not treat it as the primary blocker anymore.

