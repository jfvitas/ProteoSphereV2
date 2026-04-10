# P58 Structure Variant Next Shortlist

This is a report-only shortlist for the first structure-backed variant bridge beyond globins.

## Bottom Line

The current globin bridge stays excluded here. The next structure-backed variant bridge candidates are `P04637` and `P31749`, in that order.

That ranking is grounded only in already materialized or clearly supported local evidence:

- `P04637` and `P31749` already exist on the materialized variant surface.
- Both have explicit local structure evidence in the repo.
- Neither has a current direct join to the materialized structure-unit surface yet, so this is still a candidate shortlist, not a completed bridge.

## Why These Accessions

The bridge is supposed to be structure-backed, not guessed. These two accessions are the next credible candidates because they combine:

- a materialized protein-variant surface
- clear local RCSB/PDBe structure evidence
- AlphaFold support in the local inventory

That makes them the most honest next step beyond the globin bridge.

## Ranked Shortlist

### 1. `P04637`

- Current materialized surfaces: protein, protein_variant
- Local structure evidence:
  - `data/raw/rcsb_pdbe/20260323T002625Z/P04637/P04637.best_structures.json`
  - `data/raw/rcsb_pdbe/20260323T002625Z/P04637/9R2Q/9R2Q.entry.json`
  - `data/raw/rcsb_pdbe/20260323T002625Z/P04637/9R2Q/9R2Q.cif`
  - `data/raw/alphafold/20260323T002625Z/P04637/P04637.prediction.json`
- Why first: it has the richest variant surface and a clear local structure anchor, so it is the strongest next bridge candidate after globins.

### 2. `P31749`

- Current materialized surfaces: protein, protein_variant
- Local structure evidence:
  - `data/raw/rcsb_pdbe/20260323T002625Z/P31749/P31749.best_structures.json`
  - `data/raw/rcsb_pdbe/20260323T002625Z/P31749/7NH5/7NH5.entry.json`
  - `data/raw/rcsb_pdbe/20260323T002625Z/P31749/7NH5/7NH5.cif`
  - `data/raw/alphafold/20260323T002625Z/P31749/P31749.prediction.json`
- Why second: it is the parallel variant-backed structure candidate and the next accession to queue once `P04637` is handled.

## Exclusions

- `P68871` and `P69905` are not listed here because they already define the globin bridge and belong to the prior shortlist.

## Practical Reading

This shortlist does not claim a completed join. It says only that the next structure-backed variant bridge candidates already have enough local evidence to justify being queued after globins, with `P04637` first and `P31749` second.
