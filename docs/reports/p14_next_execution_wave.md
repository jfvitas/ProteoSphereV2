# P14 Next Execution Wave

Date: 2026-03-22
Task: `P14-A008`
Status: `completed`

## Bottom Line

The highest-yield next wave is no longer hypothetical. It is defined by the real acquisition results from the `P14-I006` curated-PPI slice and the `P14-I007` protein-depth slice:

- Curated PPI slice: `10` direct IntAct accession slices, `2` reachable-empty rows, `0` blocked rows
- Curated PPI truth boundary: `0/10` direct rows have complete canonical interaction lineage because the live PSICQUIC surface still lacks stable interaction AC or IMEx identifiers in this slice
- Protein-depth slice: `3` DisProt positives, `9` bridge-only structure hits, `10` empty hits, `0` blocked rows

That means the next execution wave should focus on upgrading real signal into stronger canonical packets, not on widening source coverage blindly.

## What The Real Yield Says

### PPI Lane

- The live IntAct lane is productive enough to justify deeper work now.
- The best current direct curated accessions are:
  - `P69905`
  - `P68871`
  - `P31749`
  - `Q9NZD4`
  - `Q2TAC2`
  - `P00387`
  - `P02042`
  - `P02100`
  - `P69892`
  - `P09105`
- The two current IntAct empty slices are:
  - `P04637`
  - `Q9UCM0`
- The critical limitation is not reachability anymore. It is canonical lineage. The current live slice is still participant-usable but interaction-key incomplete.

### Protein-Depth Lane

- The highest-yield DisProt positives are:
  - `P04637`
  - `P31749`
  - `Q9NZD4`
- The strongest bridge-positive structure set is:
  - `P69905`
  - `P68871`
  - `P04637`
  - `P31749`
  - `Q9NZD4`
  - `P00387`
  - `P02042`
  - `P02100`
  - `P69892`
- The highest-value bridge-plus-depth intersection is:
  - `P04637`
  - `P31749`
  - `Q9NZD4`
- The current explicit empty or blocked follow-up set is:
  - IntAct empty: `P04637`, `Q9UCM0`
  - DisProt empty: `P69905`, `P68871`, `Q2TAC2`, `P00387`, `P02042`, `P02100`, `P69892`, `P09105`, `Q9UCM0`
  - SABIO-RK empty: `P31749`

## Ranked Next Wave

1. Canonical IntAct export hardening
   - Why first: it upgrades the strongest current PPI yield from partial participant slices into canonical interaction evidence.
   - Best accessions to target first: `P69905`, `P68871`, `P31749`, `Q9NZD4`.

2. Bridge-positive structure packet materialization
   - Why second: the bridge-positive set is already real, but it is still bridge-only glue rather than packet-ready structure depth.
   - Highest-return subset: `P04637`, `P31749`, `Q9NZD4`, then `P68871` and `P69905`.

3. DisProt-positive lane integration
   - Why third: these are the only accession-scoped disorder positives in the frozen cohort, so they can deepen packets immediately without inventing coverage.
   - Positive set: `P04637`, `P31749`, `Q9NZD4`.

4. Empty-hit follow-up matrix
   - Why fourth: the empty set is now concrete and should drive targeted retries or source substitutions instead of repeated broad probing.
   - Most important empty cases: IntAct on `P04637` and `Q9UCM0`, DisProt on `P69905` and `P68871`, SABIO-RK on `P31749`.

5. Re-emit upgraded cohort slice and reprioritize
   - Why fifth: once the stronger canonical and packet lanes land, the benchmark should be reranked from updated real yield rather than the older probe-era assumptions.

## What Not To Prioritize Yet

- Do not prioritize more BioGRID breadth work ahead of a pinned row export.
- Do not treat bridge-only structure hits as finished structural packets.
- Do not upgrade `P31749` on the strength of SABIO-RK until the empty-target issue is resolved.
- Do not widen the cohort before the strongest current 12-accession rows are upgraded.

## Recommended P15 Ownership

- `P15-T001`: canonical IntAct export cohort slice
- `P15-T002`: bridge-positive structure packet materialization
- `P15-T003`: DisProt-positive lane integration
- `P15-A004`: empty-hit follow-up matrix
- `P15-I005`: upgraded cohort slice emission
- `P15-A006`: post-upgrade benchmark reprioritization

## Evidence Basis

- `runs/real_data_benchmark/full_results/curated_ppi_candidate_slice.json`
- `docs/reports/curated_ppi_cohort_slice.md`
- `runs/real_data_benchmark/full_results/protein_depth_candidate_slice.json`
- `docs/reports/protein_depth_candidate_slice.md`
- `docs/reports/next_cohort_expansion_candidates.md`
- `docs/reports/missing_source_live_probe_matrix.md`
