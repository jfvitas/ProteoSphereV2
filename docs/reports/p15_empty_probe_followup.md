# P15 Empty Probe Follow-Up

Date: 2026-03-22
Task: `P15-A004`

## Scope

This ranking uses only the real P14 outputs:

- `docs/reports/curated_ppi_cohort_slice.md`
- `docs/reports/protein_depth_candidate_slice.md`
- `runs/real_data_benchmark/full_results/curated_ppi_candidate_slice.json`
- `runs/real_data_benchmark/full_results/protein_depth_candidate_slice.json`
- `docs/reports/p14_next_execution_wave.md`
- `docs/reports/missing_source_live_probe_matrix.md`

The goal is to separate empty-hit cases into three truthful outcomes:

- `retry`: try the same source again once because the accession is high-value and the empty hit is plausibly query-specific
- `alternate-source`: stop probing that source for now and move to a different lane with better yield
- `stop`: do not keep probing the same empty lane; the P14 outputs already show it is low-yield for this cohort

## Ranked Follow-Up Matrix

| Rank | Accession / Source | Action | Why |
| --- | --- | --- | --- |
| 1 | `P04637` / `IntAct` | `retry` | This is the strongest retry candidate. The curated PPI slice says `IntAct` was reachable but empty for this accession, while the broader P14 slice still shows `P04637` as a real cohort accession with other usable context. A single canonical-identifier retry is justified. |
| 2 | `P31749` / `SABIO-RK` | `alternate-source` | The live probe matrix already returned `no data found` for this accession, so repeated SABIO-RK probing is not the best use of effort. Move to another assay or bridge lane instead. |
| 3 | `Q2TAC2` / `DisProt` | `alternate-source` | Thin snapshot-backed accession. The DisProt empty is useful as a blocker, but the next depth attempt should move to structure, curated PPI, or another accession-scoped lane rather than repeating DisProt. |
| 4 | `P00387` / `DisProt` | `alternate-source` | Same reasoning as `Q2TAC2`: the accession is thin, so the right next step is a different lane, not another empty DisProt probe. |
| 5 | `P02042` / `DisProt` | `alternate-source` | Thin snapshot-backed row; keep the empty explicit and pivot to a better source class. |
| 6 | `P02100` / `DisProt` | `alternate-source` | Verified in the cohort but still thin; use a different lane if more depth is needed. |
| 7 | `P69892` / `DisProt` | `alternate-source` | Same as the other thin snapshot-backed rows: the empty DisProt hit is a signal to switch lanes, not to keep probing. |
| 8 | `P69905` / `DisProt` | `stop` | This accession is already the strongest benchmark anchor. The DisProt empty should stay explicit, but it does not justify continued DisProt retries. |
| 9 | `P68871` / `DisProt` | `stop` | This accession is already mixed-evidence and probe-backed on the PPI side. The DisProt empty should not be chased further. |
| 10 | `P09105` / `DisProt` | `stop` | Verified-accession-only control. The empty hit is expected enough that it should not keep consuming probe budget. |
| 11 | `Q9UCM0` / `IntAct` | `stop` | The curated PPI slice already records IntAct as reachable but empty for this accession, and the protein-depth slice does not add a stronger counter-signal. Stop unless the accession mapping itself changes. |
| 12 | `Q9UCM0` / `DisProt` | `stop` | Empty on both IntAct and DisProt in the P14 outputs. This is the clearest no-repeat case. |

## Assumptions

- The P14 slice outputs are the authority for this matrix.
- `P04637` is worth one retry because it is a meaningful curated-PPI target, not because the source is generally trusted to fill later.
- `DisProt` empties on the strong or mixed anchors are not a reason to downgrade those accessions; they only mean DisProt is not the next best lane.
- Bridge-only structure glue and direct curated evidence should stay separate from empty-hit handling.

## Blockers

- The benchmark corpus is still prototype-class and partial, so this matrix is a follow-up ranking, not a release-readiness claim.
- `P31749` on `SABIO-RK` already returned `no data found`, so the blocker is the accession/source pairing, not just the query syntax.
- `Q9UCM0` is the strongest stop case because it is empty in both the curated-PPI and protein-depth follow-up outputs.

## Concrete Ranking

`P04637 / IntAct` -> `P31749 / SABIO-RK` -> `Q2TAC2 / DisProt` -> `P00387 / DisProt` -> `P02042 / DisProt` -> `P02100 / DisProt` -> `P69892 / DisProt` -> `P69905 / DisProt` -> `P68871 / DisProt` -> `P09105 / DisProt` -> `Q9UCM0 / IntAct` -> `Q9UCM0 / DisProt`

Final report path: `docs/reports/p15_empty_probe_followup.md`
