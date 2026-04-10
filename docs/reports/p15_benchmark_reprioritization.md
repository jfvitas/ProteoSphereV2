# P15 Benchmark Reprioritization

Date: 2026-03-22
Task: `P15-A006`

## Verdict

The upgraded cohort slice adds real packet context, but it does **not** make the corpus release-ready. The release ledger still marks all 12 benchmark rows as blocked, with `packet_not_materialized` and `modalities_incomplete` still dominant.

## Ranked Priorities

| Rank | Accession | Ledger Score | Why It Stays Here | Remaining Release-Hardening Gaps |
| --- | --- | --- | --- | --- |
| 1 | `P69905` | `69` | strongest anchor; direct curated PPI plus structure bridge and depth context | packet not materialized; modalities still incomplete |
| 2 | `P68871` | `53` | mixed-evidence hemoglobin anchor; probe-backed but still highly informative | packet not materialized; modalities incomplete; mixed evidence |
| 3 | `P04637` | `42` | empty IntAct lane is offset by real DisProt and structure bridge evidence | packet not materialized; modalities incomplete; thin coverage; ligand gap |
| 4 | `P31749` | `46` | direct curated PPI plus ligand, DisProt, and bridge evidence | packet not materialized; modalities incomplete; thin coverage; SABIO-RK remains empty |
| 5 | `Q9NZD4` | `40` | direct PPI plus DisProt and bridge evidence, but still only sequence depth | packet not materialized; modalities incomplete; thin coverage; ligand gap |
| 6 | `Q2TAC2` | `39` | snapshot-backed direct PPI, but no bridge and no DisProt signal | packet not materialized; modalities incomplete; thin coverage; ligand gap |
| 7 | `P00387` | `38` | direct PPI plus bridge evidence; still missing DisProt support | packet not materialized; modalities incomplete; thin coverage; ligand gap |
| 8 | `P02042` | `37` | direct PPI plus bridge evidence; still missing DisProt support | packet not materialized; modalities incomplete; thin coverage; ligand gap |
| 9 | `P02100` | `36` | direct PPI plus bridge evidence, but still a one-lane sequence control | packet not materialized; modalities incomplete; thin coverage; ligand gap |
| 10 | `P69892` | `35` | direct PPI plus bridge evidence, still partial and non-complete | packet not materialized; modalities incomplete; thin coverage; ligand gap |
| 11 | `P09105` | `35` | verified-accession control; useful as a thin control, not as a depth anchor | packet not materialized; modalities incomplete; thin coverage; ligand gap |
| 12 | `Q9UCM0` | `30` | empty in both IntAct and DisProt, with no bridge target to rescue the lane | packet not materialized; modalities incomplete; thin coverage; ligand gap; ppi gap |

## Key Findings

- `P69905` and `P68871` remain the top two anchors.
- `P04637` is the clearest context gain from P15 uplift because it now has real DisProt and bridge evidence, but its IntAct lane is still empty.
- `P31749` is the strongest multi-lane lift after the top anchors, but SABIO-RK is still a live empty and the packet is still incomplete.
- The snapshot-backed middle rows remain partial even when direct PPI and bridge evidence both exist.
- `Q9UCM0` remains the clearest stop case because both IntAct and DisProt are empty and there is no bridge target.

## Release-Hardening Gaps

- `packet_not_materialized` is still the universal blocker.
- `modalities_incomplete` remains on every row.
- `P68871` still carries `mixed_evidence`.
- `P04637`, `Q2TAC2`, `P00387`, `P02042`, `P02100`, `P69892`, and `P09105` still have thin-coverage or ligand-gap issues.
- `P31749` still has an explicit SABIO-RK no-target-data gap.
- `Q9UCM0` still has the strongest unresolved gap profile with `ppi_gap` on top of the shared blockers.

Source basis:

- `docs/reports/p15_upgraded_cohort_slice.md`
- `runs/real_data_benchmark/full_results/p15_upgraded_cohort_slice.json`
- `runs/real_data_benchmark/full_results/release_corpus_evidence_ledger.json`

Final report path: `docs/reports/p15_benchmark_reprioritization.md`
