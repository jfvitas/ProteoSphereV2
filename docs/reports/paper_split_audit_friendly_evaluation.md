# Audit-Friendly Paper Split Evaluation

- Generated at: 2026-04-13T19:09:22.644307+00:00
- Warehouse root: `D:\ProteoSphere\reference_library`
- Default view: `best_evidence`

## Summary Table

| Paper | Auditability | Verdict | Benchmark family | Policy |
| --- | --- | --- | --- | --- |
| `szymborski2022rapppid` | `high` | faithful and acceptable as-is | `rapppid_c123` | `uniref_grouped` |
| `graphppis2021` | `high` | faithful and acceptable as-is | `ppis_train335_family` | `paper_faithful_external` |
| `equippis2023` | `medium` | audit-useful but non-canonical | `ppis_train335_family` | `paper_faithful_external` |
| `agat_ppis2023` | `high` | faithful and acceptable as-is | `ppis_train335_family` | `paper_faithful_external` |
| `ghgpr_ppis2023` | `high` | faithful and acceptable as-is | `ppis_train335_family` | `paper_faithful_external` |
| `gact_ppis2024` | `medium` | audit-useful but non-canonical | `ppis_train335_family` | `paper_faithful_external` |
| `gte_ppis2025` | `high` | faithful and acceptable as-is | `ppis_train335_family` | `paper_faithful_external` |
| `asce_ppis2025` | `high` | faithful and acceptable as-is | `ppis_train335_family` | `paper_faithful_external` |
| `sledzieski2021dscript` | `high` | faithful and acceptable as-is | `dscript_human_plus_species_holdout` | `paper_faithful_external` |
| `topsy_turvy2022` | `medium` | audit-useful but non-canonical | `topsy_turvy_edgelists` | `accession_grouped` |
| `tt3d2023` | `medium` | audit-useful but non-canonical | `dscript_benchmark_family` | `paper_faithful_external` |
| `ppitrans2024` | `medium` | audit-useful but non-canonical | `dscript_benchmark_family` | `paper_faithful_external` |
| `tuna2024` | `high` | audit-useful but non-canonical | `bernett_plus_cross_species` | `uniref_grouped` |
| `plm_interact2025` | `high` | faithful and acceptable as-is | `bernett_plus_species_holdout` | `uniref_grouped` |
| `egcppis2025` | `high` | faithful and acceptable as-is | `ppis_train335_family` | `paper_faithful_external` |
| `mvso_ppis2025` | `high` | faithful and acceptable as-is | `ppis_train335_family` | `paper_faithful_external` |
| `hssppi2025` | `medium` | audit-useful but non-canonical | `hssppi_public_tasks` | `paper_faithful_external` |
| `mippis2024` | `medium` | audit-useful but non-canonical | `ppis_train335_family` | `paper_faithful_external` |
| `seq_insite2024` | `medium` | audit-useful but non-canonical | `seq_insite_similarity_guarded_ppis` | `uniref_grouped` |
| `deepppisp2019` | `high` | incomplete because required evidence is missing | `deepppisp_186_72_164` | `accession_grouped` |

## faithful and acceptable as-is

- `szymborski2022rapppid`: Keep this as a `uniref_grouped` audit lane and mirror the exact released roster into the warehouse so direct leakage diagnostics become first-class rather than inferred. Blockers: released split artifacts are published, but the identifiers are not bridged into warehouse-native protein refs.
- `graphppis2021`: Keep this as a `paper_faithful_external` audit lane and mirror the exact released roster into the warehouse so direct leakage diagnostics become first-class rather than inferred. Blockers: benchmark filenames are known, but the exact PPIS roster files were not mirrored into the local audit workspace in this run.
- `agat_ppis2023`: Keep this as a `paper_faithful_external` audit lane and mirror the exact released roster into the warehouse so direct leakage diagnostics become first-class rather than inferred. Blockers: benchmark filenames are known, but the exact PPIS roster files were not mirrored into the local audit workspace in this run.
- `ghgpr_ppis2023`: Keep this as a `paper_faithful_external` audit lane and mirror the exact released roster into the warehouse so direct leakage diagnostics become first-class rather than inferred. Blockers: benchmark filenames are known, but the exact PPIS roster files were not mirrored into the local audit workspace in this run.
- `gte_ppis2025`: Keep this as a `paper_faithful_external` audit lane and mirror the exact released roster into the warehouse so direct leakage diagnostics become first-class rather than inferred. Blockers: benchmark filenames are known, but the exact PPIS roster files were not mirrored into the local audit workspace in this run.
- `asce_ppis2025`: Keep this as a `paper_faithful_external` audit lane and mirror the exact released roster into the warehouse so direct leakage diagnostics become first-class rather than inferred. Blockers: benchmark filenames are known, but the exact PPIS roster files were not mirrored into the local audit workspace in this run.
- `sledzieski2021dscript`: Keep this as a `paper_faithful_external` audit lane and mirror the exact released roster into the warehouse so direct leakage diagnostics become first-class rather than inferred. Blockers: released split artifacts are published, but the identifiers are not bridged into warehouse-native protein refs.
- `plm_interact2025`: Keep this as a `uniref_grouped` audit lane and mirror the exact released roster into the warehouse so direct leakage diagnostics become first-class rather than inferred. Blockers: none.
- `egcppis2025`: Keep this as a `paper_faithful_external` audit lane and mirror the exact released roster into the warehouse so direct leakage diagnostics become first-class rather than inferred. Blockers: benchmark filenames are known, but the exact PPIS roster files were not mirrored into the local audit workspace in this run.
- `mvso_ppis2025`: Keep this as a `paper_faithful_external` audit lane and mirror the exact released roster into the warehouse so direct leakage diagnostics become first-class rather than inferred. Blockers: benchmark filenames are known, but the exact PPIS roster files were not mirrored into the local audit workspace in this run.

## audit-useful but non-canonical

- `equippis2023`: Keep it as a fair shared-benchmark comparison lane, but pair it with at least one out-of-family validation set before using it for strong generalization claims. Blockers: benchmark filenames are known, but the exact PPIS roster files were not mirrored into the local audit workspace in this run.
- `gact_ppis2024`: Keep it as a fair shared-benchmark comparison lane, but pair it with at least one out-of-family validation set before using it for strong generalization claims. Blockers: benchmark filenames are known, but the exact PPIS roster files were not mirrored into the local audit workspace in this run.
- `topsy_turvy2022`: Treat it as a `accession_grouped` audit lane or inherited benchmark family rather than a new canonical split. Blockers: none.
- `tt3d2023`: Treat it as a `paper_faithful_external` audit lane or inherited benchmark family rather than a new canonical split. Blockers: none.
- `ppitrans2024`: Treat it as a `paper_faithful_external` audit lane or inherited benchmark family rather than a new canonical split. Blockers: none.
- `tuna2024`: Treat it as a `uniref_grouped` audit lane or inherited benchmark family rather than a new canonical split. Blockers: none.
- `hssppi2025`: Treat it as a `paper_faithful_external` audit lane or inherited benchmark family rather than a new canonical split. Blockers: none.
- `mippis2024`: Keep it as a fair shared-benchmark comparison lane, but pair it with at least one out-of-family validation set before using it for strong generalization claims. Blockers: benchmark filenames are known, but the exact PPIS roster files were not mirrored into the local audit workspace in this run.
- `seq_insite2024`: Treat it as a `uniref_grouped` audit lane or inherited benchmark family rather than a new canonical split. Blockers: none.

## incomplete because required evidence is missing

- `deepppisp2019`: Do not rely on the paper split alone. Reconstruct a fixed released roster and then reevaluate it under `accession_grouped`. Blockers: benchmark datasets are shipped, but the exact fixed 350/70 train/test membership is not exposed cleanly enough in the release surface.
