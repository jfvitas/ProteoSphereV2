# Real Data Benchmark Report Template

Date: 2026-03-22
Task: `P6-I007`
Manifest: `benchmark-corpus-manifest-2026-03-22`
Plan: `real_data_benchmark_plan_2026_03_22`

This template is for the first full benchmark run over the pinned accession-level corpus. Keep missingness explicit, keep provenance attached, and do not collapse unresolved or partially mapped records into clean success.

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

## 2. Inputs And Pins

| Input | Pinned value | Notes |
| --- | --- | --- |
| Benchmark plan | `docs/reports/real_data_benchmark_plan_2026_03_22.md` | Ground truth for scope and failure criteria |
| Corpus manifest | `artifacts/status/benchmark_corpus_manifest_2026_03_22.json` | Frozen accession bundle and split target |
| Live smoke baseline | `docs/reports/live_source_smoke_2026_03_22.md` | Structure / sequence / prediction smoke evidence |
| PPI smoke baseline | `docs/reports/ppi_live_smoke_2026_03_22.md` | IntAct source-path smoke evidence |
| Annotation / pathway smoke baseline | `docs/reports/annotation_pathway_live_smoke_2026_03_22.md` | InterPro and Reactome smoke evidence |
| Ligand smoke baseline | `docs/reports/bindingdb_live_smoke_2026_03_22.md` | BindingDB smoke evidence |
| Evolutionary smoke baseline | `docs/reports/evolutionary_live_smoke_2026_03_22.md` | MSA / family-context smoke evidence |
| Source join strategy | `docs/reports/source_join_strategies.md` | Canonical join order and unresolved policy |
| Source storage strategy | `docs/reports/source_storage_strategy.md` | Pinning, lazy hydration, and deferred payload rules |

## 3. Live Evidence Baseline

Use this table to remind the reader which lanes were already proven before the full corpus run.

| Source lane | Live anchor used in smoke | Smoke result | Benchmark role |
| --- | --- | --- | --- |
| UniProt | `P69905` | succeeded | accession spine |
| InterPro | `P69905` | succeeded | domain / family enrichment |
| Reactome | `P69905` | succeeded | pathway mapping lane |
| BindingDB | `P31749` | succeeded | ligand-positive lane |
| IntAct | `P04637` | succeeded | protein-protein interaction lane |
| RCSB / PDBe | `1CBS` | succeeded after parser hardening | experimental structure lane |
| AlphaFold DB | `P69905` | succeeded | predicted structure lane |
| Evolutionary / MSA | `P69905` | succeeded | conservation / redundancy lane |

## 4. Cohort Snapshot

### 4.1 Cohort composition

| Bucket | Planned accessions | Resolved accessions | Missing / partial | Example accessions | Notes |
| --- | --- | --- | --- | --- | --- |
| Rich coverage | [fill in, expected 4] | [fill in] | [fill in] | [fill in] | InterPro + Reactome present |
| Moderate coverage | [fill in, expected 4] | [fill in] | [fill in] | [fill in] | At least one missing layer is expected |
| Sparse / control | [fill in, expected 4] | [fill in] | [fill in] | [fill in] | Missingness must remain explicit |
| Ligand-positive lane | [fill in, optional] | [fill in] | [fill in] | `P31749` if included | Only include if the run enables ligand coverage |

### 4.2 Split hygiene

| Split | Accessions | Count | Rich | Moderate | Sparse | Leakage check |
| --- | --- | --- | --- | --- | --- | --- |
| Train | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] |
| Val | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] |
| Test | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] |

Record any accession-level leakage here:

- [fill in, or `none`]

## 5. Source Coverage

Report coverage and yield by source lane. This should be the most complete table in the report.

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

## 6. Provenance And Lineage

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

## 7. Run Health

| Metric | Value | Notes |
| --- | --- | --- |
| Checkpoint writes | [fill in] | include bundle granularity if available |
| Checkpoint resumes | [fill in] | include any successful resume after interruption |
| Retry counts by source | [fill in] | summarize by source lane and error class |
| Retry exhaustion events | [fill in] | include source and accession |
| Dispatch cycles | [fill in] | if relevant to the run harness |
| Failure classes observed | [fill in] | network, schema drift, parser normalization, etc. |
| Peak runtime pressure | [fill in] | note any capacity or GPU-related bottlenecks |

## 8. Failure Summary

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

## 9. Unresolved And Partial Cases

Keep every unresolved or partial case visible.

| Record or accession | Source | Why unresolved | Candidate IDs / refs | Provenance preserved | Follow-up |
| --- | --- | --- | --- | --- | --- |
| [fill in] | [fill in] | [fill in] | [fill in] | yes / no | [fill in] |

## 10. Key Findings

Write the shortest truthful summary here.

- [fill in]
- [fill in]
- [fill in]

## 11. Reproducibility And Artifacts

| Path | Purpose |
| --- | --- |
| `artifacts/status/benchmark_corpus_manifest_2026_03_22.json` | corpus manifest completion artifact |
| `artifacts/status/real_data_benchmark_plan_2026_03_22.json` | benchmark plan completion artifact |
| `docs/reports/live_source_smoke_2026_03_22.md` | structure / sequence / prediction smoke evidence |
| `docs/reports/ppi_live_smoke_2026_03_22.md` | PPI smoke evidence |
| `docs/reports/annotation_pathway_live_smoke_2026_03_22.md` | InterPro / Reactome smoke evidence |
| `docs/reports/bindingdb_live_smoke_2026_03_22.md` | BindingDB smoke evidence |
| `docs/reports/evolutionary_live_smoke_2026_03_22.md` | evolutionary / MSA smoke evidence |
| `runs/real_data_benchmark/` | benchmark outputs, logs, and checkpoints |

## 12. Decision

| Decision | Value | Notes |
| --- | --- | --- |
| Benchmark ready for next wave | [yes / no] | [fill in] |
| Remaining blockers | [fill in] | [fill in] |
| Safe follow-up change | [fill in] | [fill in] |

If the run is partial or failed, the report must state whether the issue is a source problem, a parser problem, a provenance problem, or a benchmark-setup problem. Do not hide the category.
