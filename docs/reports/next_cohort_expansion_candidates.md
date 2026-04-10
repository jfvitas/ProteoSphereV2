# Next Cohort Expansion Candidates

Date: 2026-03-22
Task: `P13-A009`

## Bottom Line

The next cohort-expansion candidates should be ranked by the amount of real source depth they can absorb without weakening join quality. The frozen 12-accession cohort is still thin overall, but the best expansion path is concentrated: remove the probe-backed weakness first, then deepen the strongest single-lane anchors, then widen the accession-clean controls.

The useful benchmark facts are still:

- `1` useful example, `11` weak examples
- `10` thin-coverage examples
- `1` mixed-evidence example
- all `12` packets are still `partial`

That means the right ranking is about truth-preserving depth gain, not about widening the corpus or relabeling weak evidence as strong.

## Ranked Candidates

1. `P68871`
   - Highest priority because it is the only mixed-evidence row and the only probe-backed lane in the cohort.
   - Best next gain: replace the summary-library dependence with direct curated PPI evidence, then add any stable structural or context lanes that fit the accession.
   - Why first: it is already multi-lane, so upgrading it gives the biggest truth-preserving improvement.

2. `P04637`
   - Strong curated PPI anchor, but still single-lane.
   - Best next gain: add structure and context lanes so the row stops reading like a thin PPI-only control.
   - Why here: the current real packet audit shows PPI is still missing for most rows, so this is a high-value place to deepen curated interaction evidence.

3. `P31749`
   - Strong ligand-side anchor, but still single-lane.
   - Best next gain: add structure or curated pair context where a real accession-level hit exists.
   - Why here: the ligand lane is already locally strong, but this accession is still only one lane deep, so it remains a good expansion target if the join is accession-clean.

4. `Q9NZD4`, `Q2TAC2`, `P00387`, `P02042`
   - Best snapshot-backed UniProt-only rows to deepen next.
   - Best next gain: one additional structural, pathway, or annotation lane each, if a real accession-scoped source exists.
   - Why here: these rows already prove identity cleanly, so they are the best thin controls to turn into more informative multimodal examples.

5. `P69892`
   - Another snapshot-backed UniProt-only control that can move up if an actual second lane is available.
   - Why lower than the four rows above: it is still thin, but it is less central than the other snapshot-backed controls for proving broader coverage depth.

6. `P09105`, `Q9UCM0`
   - Lowest-priority controls in the current cohort because they are verified-accession only.
   - Best next gain: any stable structure, annotation, or curated interaction lane that does not introduce ambiguity.

## What Not To Rank Up

- `P69905` is already the strongest row and should stay the reference anchor, not the first expansion target.
- `P68871` must stay explicitly probe-backed until direct curated evidence lands.
- `P31749` should not be promoted on the strength of `SABIO-RK`; the live probe matrix returned no data for that accession.

## Assumptions

- The cohort stays frozen at 12 accessions.
- Expansion should add real source depth, not new cohort members.
- Online additions must remain accession-first and role-preserving.
- Probe-backed, snapshot-backed, and verified-accession rows must stay in their current evidence class until the source evidence actually changes.

## Blockers And Dependencies

- The benchmark runtime is still prototype-class, so this ranking is not a release-grade claim.
- The packet audit shows every row is still partial, so even the best candidates are depth-improvement targets, not finished packets.
- The live probe matrix separates structured, rankable sources from surface-only sources:
  - rankable now: `IntAct`, `STRING`, `RCSB/PDBe bridge`, `EMDB`
  - surface-only follow-ons: `BioGRID`, `PROSITE`, `ELM`, `MegaMotifBase`, `Motivated Proteins`
- `DisProt` returned an empty result for `P69905`, so it should not be generalized into a broad protein-depth win without a populated accession.
- `SABIO-RK` returned no data for `P31749`, so assay-depth expansion for that accession is still blocked until a better anchor is found.

## Recommended Priority Order

`P68871` -> `P04637` -> `P31749` -> `Q9NZD4` / `Q2TAC2` / `P00387` / `P02042` -> `P69892` -> `P09105` / `Q9UCM0`

That order gives the biggest truthful gain first: remove the mixed probe-backed row, deepen the curated PPI anchor, then widen the thin but accession-clean controls.
