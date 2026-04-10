# P15 Upgraded Cohort Slice

Generated: `2026-03-23T02:26:38.006755+00:00`

## Verdict

The upgraded cohort slice is now re-emitted from the real P14/P15 evidence surfaces. It shows concrete context uplift from curated PPI, DisProt, and bridge-positive structure glue, but it does not upgrade any row to release-ready or packet-complete.

## Summary

- Cohort rows: `12`
- Direct curated PPI rows: `10`
- Curated PPI empty rows: `2`
- Protein-depth rows: `12`
- DisProt-positive rows: `3`
- Bridge-positive structure rows: `9`
- Structure-bridge missing rows: `3`
- Assay-gap rows: `1`

## Top Upgrades

| Accession | Split | Signals | Remaining Gap |
| --- | --- | --- | --- |
| `P31749` | `train` | direct curated PPI, DisProt-positive depth, bridge-positive structure glue | SABIO-RK still has no target data. |
| `Q9NZD4` | `train` | direct curated PPI, DisProt-positive depth, bridge-positive structure glue | still partial, but now multi-lane evidence is explicit. |
| `P00387` | `train` | direct curated PPI, bridge-positive structure glue | structure glue is present, DisProt is not. |
| `P02042` | `train` | direct curated PPI, bridge-positive structure glue | bridge-only structure glue remains separate from depth claims. |
| `P04637` | `train` | DisProt-positive depth, bridge-positive structure glue | IntAct stays empty; depth and structure evidence are separate. |

## Remaining Truth Boundary

- No row is release-ready in this slice.
- Bridge-positive structure hits stay bridge-only until packet materialization lands.
- IntAct empties remain explicit and are not backfilled.
- DisProt empties remain explicit empties, not negative biological labels.
- The SABIO-RK gap for `P31749` is still reachable-but-empty, not solved.

## Source Artifacts

- `docs/reports/curated_ppi_cohort_slice.md`
- `docs/reports/protein_depth_candidate_slice.md`
- `runs/real_data_benchmark/full_results/curated_ppi_candidate_slice.json`
- `runs/real_data_benchmark/full_results/protein_depth_candidate_slice.json`
- `docs/reports/p15_empty_probe_followup.md`
