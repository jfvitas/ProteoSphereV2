# Real Example Usefulness Evaluation

Date: 2026-03-22
Task: `P12-I008`
Status: `completed`

## Verdict

The real-example usefulness pass scored 12 frozen benchmark examples from actual prototype-run artifacts. 1 example (8.3%) is strong enough to call useful today, while the rest remain conservatively weak rather than promoted beyond the evidence.

This is a prototype-runtime usefulness readout, not a release-grade biological validation claim.

## Aggregate Findings

- Useful examples: `1/12` (8.3%)
- Weak examples: `11/12` (91.7%)
- Blocked examples: `0/12` (0.0%)
- Thin-coverage examples: `10/12` (83.3%)
- Mixed-evidence examples: `1/12` (8.3%)

## Runtime Boundary

- Runtime surface: `local prototype runtime with surrogate modality embeddings and identity-safe resume continuity`
- Backend: `local-prototype-runtime`
- Selected accession count: `12`
- Checkpoint writes / resumes: `2` / `1`
- Resume continuity: `identity-safe`

## Per-Example Judgments

| Accession | Split | Judgment | Evidence | Lanes | Notes |
| --- | --- | --- | --- | --- | --- |
| `P69905` | `train` | `useful` | `direct_live_smoke` | 5 (UniProt, InterPro, Reactome, AlphaFold DB, Evolutionary / MSA) | direct live smoke with multilane, non-thin coverage |
| `P68871` | `train` | `weak` | `live_summary_library_probe` | 2 (UniProt, protein-protein summary library) | probe-backed and mixed evidence |
| `P04637` | `train` | `weak` | `direct_live_smoke` | 1 (IntAct) | single-lane thin coverage |
| `P31749` | `train` | `weak` | `direct_live_smoke` | 1 (BindingDB) | single-lane thin coverage |
| `Q9NZD4` | `train` | `weak` | `in_tree_live_snapshot` | 1 (UniProt) | single-lane thin coverage |
| `Q2TAC2` | `train` | `weak` | `in_tree_live_snapshot` | 1 (UniProt) | single-lane thin coverage |
| `P00387` | `train` | `weak` | `in_tree_live_snapshot` | 1 (UniProt) | single-lane thin coverage |
| `P02042` | `train` | `weak` | `in_tree_live_snapshot` | 1 (UniProt) | single-lane thin coverage |
| `P02100` | `val` | `weak` | `in_tree_live_snapshot` | 1 (UniProt) | single-lane thin coverage |
| `P69892` | `val` | `weak` | `in_tree_live_snapshot` | 1 (UniProt) | single-lane thin coverage |
| `P09105` | `test` | `weak` | `live_verified_accession` | 1 (UniProt) | single-lane thin coverage |
| `Q9UCM0` | `test` | `weak` | `live_verified_accession` | 1 (UniProt) | single-lane thin coverage |

## Evidence Split

Benchmark execution evidence supports statements about what actually ran and what the prototype runtime produced:

- `D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/metrics_summary.json`
- `D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/source_coverage.json`
- `D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/provenance_table.json`

Local-source bridge evidence supports statements about what was importable or joinable from the local bio-agent-lab mirrors, not about benchmark completeness:

- `D:/documents/ProteoSphereV2/docs/reports/local_source_import_validation.md`
- `D:/documents/ProteoSphereV2/docs/reports/local_source_reuse_strategy.md`
- `D:/documents/ProteoSphereV2/artifacts/reviews/p12_i008_local_evidence_join_2026_03_22.md`

## What The Useful Result Actually Means

- `P69905` is the only example with direct live smoke plus multilane, non-thin support across UniProt, InterPro, Reactome, AlphaFold DB, and evolutionary evidence.
- `P68871` remains weak because its pair-aware support is probe-backed and mixed rather than direct assay-grade evidence.
- `P04637` and `P31749` are real direct-live rows, but each remains thin because they only carry one lane.
- The remaining rows are useful as traceable benchmark fixtures, but their current evidence depth is too narrow for a stronger judgment.

## Limits

- The runtime is still the local prototype surface with surrogate modality embeddings.
- The usefulness report is frozen to the 12-accession benchmark cohort and does not widen the corpus.
- Local import validation proves bridgeability on selected real files, not corpus-scale local completeness.
- Machine-readable review artifact: `runs/real_data_benchmark/full_results/usefulness_review.json`
