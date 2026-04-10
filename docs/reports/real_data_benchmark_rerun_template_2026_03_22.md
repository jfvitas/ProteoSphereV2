# Real Data Benchmark Rerun Report Template

Date: 2026-03-22
Task: `P6-I009`
Manifest: `benchmark-corpus-manifest-2026-03-22`
Plan: `docs/reports/real_data_benchmark_plan_2026_03_22.md`
Prep: `artifacts/reviews/real_data_benchmark_rerun_prep_2026_03_22.md`

Use this template only for a truthful corpus-scale rerun. Keep selected-accession scope fixed, keep provenance explicit, and do not collapse unresolved or conflicting records into clean success.

## 1. Run Summary

| Field | Value |
| --- | --- |
| Run ID | [fill in] |
| Start time | [fill in] |
| End time | [fill in] |
| Wall-clock runtime | [fill in] |
| Pipeline commit / branch | [fill in] |
| Manifest ID | `benchmark-corpus-manifest-2026-03-22` |
| Cohort size | [fill in, expected 12] |
| Split policy | accession-level only |
| Split counts | train: [fill in], val: [fill in], test: [fill in] |
| Overall status | [pass / partial / blocked / failed] |

## 2. Preconditions

Record the exact launch prerequisites and whether each was met.

| Prerequisite | Required value | Met? | Notes |
| --- | --- | --- | --- |
| `P5-T015` | complete and green | [yes / no] | [fill in] |
| `P6-T008` | complete and green | [yes / no] | [fill in] |
| `P5-I013` | green | [yes / no] | [fill in] |
| `P5-I012` | green | [yes / no] | [fill in] |
| `P6-I004` | green | [yes / no] | [fill in] |
| Corpus manifest | frozen and matching `benchmark-corpus-manifest-2026-03-22` | [yes / no] | [fill in] |
| Cohort bundle | pinned 12-accession bundle present | [yes / no] | [fill in] |
| Results tree | writable `runs/real_data_benchmark/results/` | [yes / no] | [fill in] |
| Launch checklist | `runs/real_data_benchmark/checklist_2026_03_22.md` satisfied | [yes / no] | [fill in] |

## 3. Inputs And Pins

| Input | Pinned value | Notes |
| --- | --- | --- |
| Benchmark plan | `docs/reports/real_data_benchmark_plan_2026_03_22.md` | scope, statistics, failure criteria |
| Corpus manifest | `runs/real_data_benchmark/manifest.json` | frozen accession bundle and split target |
| Launch checklist | `runs/real_data_benchmark/checklist_2026_03_22.md` | launch gates and stop conditions |
| Package validation gate | `P5-I013` | must remain explicit if still required |
| Flagship pipeline gate | `P5-I012` | must remain explicit |
| Benchmark corpus bundle gate | `P6-T008` | must remain explicit |
| Trainer runtime gate | `P5-T015` | must remain explicit |
| Live smoke baselines | `docs/reports/*_live_smoke_2026_03_22.md` | pre-run evidence only |

## 4. Live Evidence Baseline

Show which lanes were already proven before the rerun.

| Source lane | Live anchor used in smoke | Smoke result | Rerun role |
| --- | --- | --- | --- |
| UniProt | `P69905` | [fill in] | accession spine |
| InterPro | `P69905` | [fill in] | domain / family enrichment |
| Reactome | `P69905` | [fill in] | pathway mapping lane |
| BindingDB | `P31749` | [fill in] | ligand-positive lane |
| IntAct / PPI | `P04637` | [fill in] | interaction lane |
| RCSB / PDBe | `1CBS` | [fill in] | experimental structure lane |
| AlphaFold DB | `P69905` | [fill in] | predicted structure lane |
| Evolutionary / MSA | `P69905` | [fill in] | conservation / redundancy lane |

## 5. Cohort Snapshot

### 5.1 Cohort composition

| Bucket | Planned accessions | Resolved accessions | Missing / partial | Example accessions | Notes |
| --- | --- | --- | --- | --- | --- |
| Rich coverage | [fill in, expected 4] | [fill in] | [fill in] | [fill in] | InterPro + Reactome present |
| Moderate coverage | [fill in, expected 4] | [fill in] | [fill in] | [fill in] | at least one missing layer expected |
| Sparse / control | [fill in, expected 4] | [fill in] | [fill in] | [fill in] | missingness must stay explicit |
| Ligand-positive lane | [fill in, optional] | [fill in] | [fill in] | `P31749` if included | only if ligand coverage is enabled |

### 5.2 Split hygiene

| Split | Accessions | Count | Rich | Moderate | Sparse | Leakage check |
| --- | --- | --- | --- | --- | --- | --- |
| Train | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] |
| Val | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] |
| Test | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] |

Record any accession-level leakage here:

- [fill in, or `none`]

## 6. Source Coverage

Report coverage and yield by source lane.

| Source | Planned accessions | Resolved | Missing | Partial | Ambiguous | Explicit unresolved | Mean records / protein | Median | p90 | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| UniProt | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] |
| InterPro | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] |
| Reactome | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] |
| BindingDB | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] |
| IntAct / PPI | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] |
| RCSB / PDBe | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] |
| AlphaFold DB | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] |
| Evolutionary / MSA | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] |

## 7. Provenance And Lineage

| Metric | Value | How measured | Notes |
| --- | --- | --- | --- |
| Records with complete provenance | [fill in] | count / total retained records | [fill in] |
| Records preserving UniProt accession spine | [fill in] | count / total protein-bearing records | [fill in] |
| Records with source-native IDs retained | [fill in] | count / total retained records | [fill in] |
| Explicit unresolved records surfaced | [fill in] | count of unresolved rows / sidecars | [fill in] |
| Explicit conflicts surfaced | [fill in] | count of conflict rows / sidecars | [fill in] |
| Partially mapped records | [fill in] | count of partial joins / partial bundles | [fill in] |
| Records with lazy materialization refs | [fill in] | count of records carrying deferred asset pointers | [fill in] |

List any provenance regressions here:

- [fill in, or `none`]

## 8. Run Health

| Metric | Value | Notes |
| --- | --- | --- |
| Checkpoint writes | [fill in] | include bundle granularity if available |
| Checkpoint resumes | [fill in] | include any successful resume after interruption |
| Retry counts by source | [fill in] | summarize by source lane and error class |
| Retry exhaustion events | [fill in] | include source and accession |
| Dispatch cycles | [fill in] | if relevant to the run harness |
| Failure classes observed | [fill in] | network, schema drift, parser normalization, etc. |
| Peak runtime pressure | [fill in] | note any capacity or GPU-related bottlenecks |

## 9. Failure Summary

Use one row per distinct failure mode. Keep the source, error class, and impact visible.

| Source | Error class | Count | Example accession / record | Impact | Root cause | Action |
| --- | --- | --- | --- | --- | --- | --- |
| UniProt | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] |
| InterPro | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] |
| Reactome | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] |
| BindingDB | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] |
| IntAct / PPI | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] |
| RCSB / PDBe | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] |
| AlphaFold DB | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] |
| Evolutionary / MSA | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] |

### Failure classes to use

- endpoint unavailable
- parser normalization
- schema drift
- provenance loss
- split leakage
- unresolved join
- conflict collapse
- retry exhaustion
- checkpoint failure
- capacity / scheduling issue

## 10. Unresolved And Partial Cases

Keep every unresolved or partial case visible.

| Record or accession | Source | Why unresolved | Candidate IDs / refs | Provenance preserved | Follow-up |
| --- | --- | --- | --- | --- | --- |
| [fill in] | [fill in] | [fill in] | [fill in] | yes / no | [fill in] |

## 11. Key Findings

Write the shortest truthful summary here.

- [fill in]
- [fill in]
- [fill in]

## 12. Reproducibility And Artifacts

| Path | Purpose |
| --- | --- |
| `artifacts/status/benchmark_corpus_manifest_2026_03_22.json` | corpus manifest completion artifact |
| `artifacts/status/real_data_benchmark_plan_2026_03_22.json` | benchmark plan completion artifact |
| `artifacts/reviews/real_data_benchmark_rerun_prep_2026_03_22.md` | rerun prerequisites and stop conditions |
| `docs/reports/live_source_smoke_2026_03_22.md` | structure / sequence / prediction smoke evidence |
| `docs/reports/ppi_live_smoke_2026_03_22.md` | PPI smoke evidence |
| `docs/reports/annotation_pathway_live_smoke_2026_03_22.md` | InterPro / Reactome smoke evidence |
| `docs/reports/bindingdb_live_smoke_2026_03_22.md` | BindingDB smoke evidence |
| `docs/reports/evolutionary_live_smoke_2026_03_22.md` | evolutionary / MSA smoke evidence |
| `runs/real_data_benchmark/results/` | rerun outputs, logs, and checkpoints |

## 13. Decision

| Decision | Value | Notes |
| --- | --- | --- |
| Benchmark ready for next wave | [yes / no] | [fill in] |
| Remaining blockers | [fill in] | [fill in] |
| Safe follow-up change | [fill in] | [fill in] |

If the rerun is partial or failed, the report must state whether the issue is a source problem, a parser problem, a provenance problem, or a benchmark-setup problem. Do not hide the category.
