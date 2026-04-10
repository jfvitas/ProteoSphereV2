# Cohort Lane Coverage Analysis

Date: 2026-03-22
Scope: frozen 12-accession benchmark cohort
Primary inputs: `runs/real_data_benchmark/full_results/source_coverage.json`, `runs/real_data_benchmark/cohort/cohort_manifest.json`, `runs/real_data_benchmark/full_results/live_inputs.json`

## Verdict

The frozen cohort is release-usable as an accession-level benchmark set, but its lane depth is highly skewed. Only 2 of 12 accessions have more than one source lane, and only 1 accession reaches the five-lane level that looks genuinely multimodal. The rest are single-lane or probe-backed placeholders that are useful for truthfulness and leakage control, but not for claiming broad multimodal source depth.

## Coverage Snapshot

| Lane depth | Accessions | Share |
| --- | ---: | ---: |
| 5 lanes | 1 | 8.3% |
| 2 lanes | 1 | 8.3% |
| 1 lane | 10 | 83.3% |

| Evidence class | Accessions |
| --- | ---: |
| direct_live_smoke | 4 |
| probe_backed | 1 |
| snapshot_backed | 5 |
| verified_accession | 2 |

The cohort remains clean at accession granularity:

- total accessions: 12
- resolved accessions: 12
- unresolved accessions: 0
- train / val / test: 8 / 2 / 2

## Strongest Lanes

- `P69905` is the only clearly deep lane profile in the cohort. It carries five source lanes: UniProt, InterPro, Reactome, AlphaFold DB, and Evolutionary / MSA.
- `P68871` is the only other multi-lane accession. It is two-lane, but one lane is a summary-library probe rather than a direct live assay, so it should be treated as supportive rather than fully equivalent to direct smoke evidence.

## Weak Lanes

The main weakness is not leakage or resolution. It is depth.

- `P04637` is single-lane and only IntAct-backed.
- `P31749` is single-lane and only BindingDB-backed.
- `Q9NZD4`, `Q2TAC2`, `P00387`, `P02042`, `P02100`, `P69892`, `P09105`, and `Q9UCM0` are all single-lane UniProt-backed accessions.

These lanes are acceptable for frozen-cohort bookkeeping and release gating, but they should not be overstated as deep source coverage.

## Release-Oriented Interpretation

The matrix supports three distinct claims:

1. The cohort is frozen, accession-level only, and leakage-ready.
2. The benchmark has a small number of strong evidence anchors.
3. Most accessions are intentionally thin and must be reported as such.

For release language, the safe framing is:

- "The benchmark cohort is pinned and traceable."
- "The cohort contains one high-depth anchor and one moderate-depth probe-backed anchor."
- "The remainder of the cohort is deliberately thin and serves as control or lower-depth coverage."

What should not be claimed:

- that the benchmark has broadly deep multimodal coverage across most accessions
- that the probe-backed or snapshot-backed lanes are equivalent to direct live smoke evidence
- that single-lane UniProt entries represent rich cross-source integration

## Evidence Notes

The source coverage matrix explicitly separates:

- `direct_live_smoke`
- `probe_backed`
- `snapshot_backed`
- `verified_accession`

That separation is important for downstream release notes and benchmark interpretation. The matrix is honest about lane depth, and it avoids silently widening the cohort or inflating thin lanes into stronger evidence classes.

## Bottom Line

The frozen cohort is good enough for a truthful benchmark launch, but not for a claim of uniformly rich source coverage. The weakest lanes are the single-lane accessions, especially the UniProt-only ones, while the strongest lane is `P69905` and the only other multi-lane accession is `P68871`.
