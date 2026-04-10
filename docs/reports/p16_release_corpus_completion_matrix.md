# P16 Release Corpus Completion Matrix

Date: 2026-03-23  
Task: `P16-A001`

## Bottom Line

The upgraded release corpus is still **fully blocked**, but the blockage is now separable by evidence type.

- `12/12` protein rows are blocked.
- `0/12` rows are release-ready.
- Packet materialization is the universal blocker.
- Pair, ligand, and protein completion gaps are explicit inside the protein rows and do not get collapsed away.

The release ledger is protein-row based, so pair and ligand evidence show up as modality lanes on protein rows rather than as standalone pair/ligand records.

## Matrix Summary By Gap Type

| Gap type | Current state | Highest-value gap(s) | Explicit blocker types |
| --- | --- | --- | --- |
| Protein | All 12 protein rows are blocked | `protein:P69905` is the strongest anchor but still partial; `protein:P68871` is the next deepest row | `packet_not_materialized`, `modalities_incomplete`, `thin_coverage`, `mixed_evidence` |
| Pair | Pair evidence exists only as lanes inside protein rows | `protein:Q9UCM0` is the only explicit unresolved PPI gap; `protein:P68871` is the only mixed probe-backed pair lane | `ppi_gap`, `mixed_evidence`, `thin_coverage` |
| Ligand | Ligand evidence is sparse or bridge/structure-linked for most rows | `protein:P31749` is the only assay-linked ligand anchor; `protein:P69905` and `protein:P68871` carry structure-linked ligand lanes | `ligand_gap`, `modalities_incomplete`, `thin_coverage` |
| Packet | Every row remains partial | `protein:P69905` is the strongest packet, but still incomplete | `packet_not_materialized`, `modalities_incomplete` |

## Protein Gap Ranking

The protein-side completion order should stay conservative:

1. `protein:P69905`
   - strongest multimodal anchor
   - still blocked by packet incompleteness and missing requested modalities
   - evidence lanes: UniProt, InterPro, Reactome, AlphaFold DB, Evolutionary / MSA, PPI, structure-linked ligand

2. `protein:P68871`
   - second strongest row
   - mixed evidence remains explicit
   - still probe-backed rather than direct throughout

3. `protein:P31749`
   - only assay-linked ligand anchor
   - still missing sequence, structure, and PPI modalities

4. `protein:P04637`
   - direct PPI anchor only
   - still thin on sequence, structure, and ligand

5. `protein:Q9UCM0`
   - explicit unresolved PPI gap
   - the only row with a first-class `ppi_gap` blocker

6. `protein:P00387`, `protein:P02042`, `protein:P02100`, `protein:P69892`, `protein:Q2TAC2`, `protein:Q9NZD4`, `protein:P09105`
   - single-lane controls or snapshot-backed thin rows
   - keep them blocked rather than inflating them into deep coverage

## Pair Gap Ranking

Pair coverage is still shallow enough that the pair problem is mostly encoded as blockers inside the protein rows.

1. `protein:Q9UCM0`
   - explicit unresolved pair gap
   - only row carrying `ppi_gap`

2. `protein:P68871`
   - pair lane is present, but it remains probe-backed and mixed
   - the pair signal is useful, but it is not direct-curated pair closure

3. `protein:P04637`, `protein:P00387`, `protein:P02042`, `protein:P02100`, `protein:P69892`, `protein:Q2TAC2`, `protein:Q9NZD4`, `protein:P09105`
   - thin non-release protein rows that currently lack durable pair closure
   - useful for evidence accounting, but still thin as release corpus pair coverage

## Ligand Gap Ranking

Ligand coverage is the clearest depth gap after packet completeness.

1. `protein:P31749`
   - best ligand anchor in the cohort
   - assay-linked ligand evidence is present
   - still partial because the packet is missing sequence, structure, and PPI modalities

2. `protein:P69905`
   - structure-linked ligand lane only
   - still missing ligand completeness and packet closure

3. `protein:P68871`
   - structure-linked ligand lane only
   - remains mixed/probe-backed overall

4. `protein:P04637`, `protein:P00387`, `protein:P02042`, `protein:P02100`, `protein:P69892`, `protein:Q2TAC2`, `protein:Q9NZD4`, `protein:P09105`, `protein:Q9UCM0`
   - held sparse-gap ligand state
   - these rows should stay blocked until a real ligand lane exists

## Packet Gap Ranking

Packet materialization is the universal blocker and should remain the top release-corpus gate.

1. `protein:P69905`
   - best packet, but still partial
   - strongest chance of becoming the first release-ready row once packet completeness lands

2. `protein:P68871`
   - deeper than the single-lane controls, but still partial and mixed

3. `protein:P31749`
   - good ligand anchor, but still packet-incomplete

4. `protein:P04637`
   - direct PPI anchor only, still packet-incomplete

5. `protein:P00387`, `protein:P02042`, `protein:P02100`, `protein:P69892`, `protein:Q2TAC2`, `protein:Q9NZD4`, `protein:P09105`, `protein:Q9UCM0`
   - thin or verified-accession controls
   - keep packet completeness blocked rather than assuming downstream lanes will fill in later

## Release Read

The release corpus is now honest enough to rank completion work by evidence type, but it is still far from release-ready.

- The protein slice is blocked across the board.
- Pair gaps are explicit only in one unresolved accession, with one mixed probe-backed anchor.
- Ligand gaps remain the biggest depth problem after packet materialization.
- Packet incompleteness still blocks every row.

The right next move is not to widen the cohort. It is to close packet materialization first, then deepen ligand and pair coverage on the strongest anchors, and only then revisit the sparse long tail.
