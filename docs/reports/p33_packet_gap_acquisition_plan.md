# P33 Packet Gap Acquisition Plan

This slice ranks the next concrete acquisitions for the remaining packet gaps using only the current packet deficit dashboard, the refreshed local registry, and the procurement status board.

## What We Should Run Next

| Rank | Accession | Gap | Best next acquisition | Why now |
| --- | --- | --- | --- | --- |
| 1 | P00387 | ligand | ChEMBL rescue brief | It is already locally available, ligand-focused, and the brief reports 93 activities and 93 assays. |
| 2 | P09105 | ligand | Structure-linked extraction from `extracted_bound_objects` | Structure and PPI are already present, so this is the strongest present-source rescue. |
| 3 | Q2TAC2 | ligand | Structure-linked extraction from `extracted_bound_objects` | Same pattern as P09105, with a canonical accession and a local structure packet. |
| 4 | Q9NZD4 | ligand | Structure-linked extraction from `extracted_bound_objects` | Structure and PPI are present, so local extraction should be tried before any external fallback. |
| 5 | Q9UCM0 | structure | AlphaFold DB explicit accession probe | This accession is still missing structure, ligand, and PPI, and the proof artifact says UniProt is the only current join key. |

## Evidence Base

The current packet deficit dashboard says the five remaining high-leverage fixes are `ligand:P00387`, `ligand:P09105`, `ligand:Q2TAC2`, `ligand:Q9NZD4`, `ligand:Q9UCM0`, plus `ppi:Q9UCM0` and `structure:Q9UCM0`. The procurement board confirms the strong lanes are structure and ligand, while interaction networks remain weak and the live registry still marks `biogrid` and `string` as missing. The latest local registry refresh shows 57 selected and imported sources, so the execution plan should stay grounded in present sources rather than speculative procurement.

For `Q9UCM0`, the acquisition proof is still explicit: structure, ligand, and PPI are unresolved; the current bindingdb snapshot is empty; IntAct is alias-only; and BioGRID/STRING are deferred because they are not locally present.

## Execution Order

1. Run the P00387 ChEMBL rescue brief first.
2. Run `extracted_bound_objects` for P09105, Q2TAC2, and Q9NZD4 in that order.
3. Run the Q9UCM0 AlphaFold DB probe next.
4. If Q9UCM0 remains incomplete, re-probe RCSB/PDBe, then try structure-linked ligand extraction, then IntAct.
5. Keep BioGRID and STRING as deferred procurement because the registry still reports both as missing.

## Guardrails

- Treat null results as valid if the source was actually probed.
- Do not collapse alias-only or partner-only evidence into a fill.
- Do not move missing network sources into the immediate queue just because the cohort still needs PPI breadth.
- Preserve provenance for every returned payload and every null result.

## Short Version

The fastest, most grounded next wave is ligand rescue for `P00387`, `P09105`, `Q2TAC2`, and `Q9NZD4`, followed by the structure rescue for `Q9UCM0`. The later PPI work for `Q9UCM0` is real, but it should wait until the present-source structure and ligand lanes have been exhausted.
