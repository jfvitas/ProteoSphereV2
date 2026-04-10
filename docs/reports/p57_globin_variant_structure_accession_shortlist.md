# P57 Globin Variant-Structure Accessions

This report-only shortlist picks the next structure-backed globin extensions after `P68871` and `P69905`.

## What Is Already True

The current variant summary library is large, but the next globin accessions are not yet materialized there. The strongest local extension candidates are the globin accessions that already have both variant evidence in UniProt and structure evidence in the local RCSB/PDBe mirrors.

## Shortlist

1. `P69892` `HBG2_HUMAN` `Hemoglobin subunit gamma-2`
   - Evidence strength: highest
   - Local variant evidence: 122 variant lines in `data/raw/uniprot/20260323T154140Z/P69892/P69892.txt`
   - Local structure evidence: 12 best-structure entries in `data/raw/rcsb_pdbe/20260323T154140Z/P69892/P69892.best_structures.json`
   - Best structure anchor: `7QU4` chains `G/H`, full coverage, 1.66 Å
   - Truthful next step: materialize accession-scoped variant rows, then join them to the existing local structure evidence

2. `P02042` `HBD_HUMAN` `Hemoglobin subunit delta`
   - Evidence strength: high
   - Local variant evidence: 98 variant lines in `data/raw/uniprot/20260323T154140Z/P02042/P02042.txt`
   - Local structure evidence: 4 best-structure entries in `data/raw/rcsb_pdbe/20260323T154140Z/P02042/P02042.best_structures.json`
   - Best structure anchor: `1SHR` chains `B/D`, 0.993 coverage, 1.88 Å
   - Truthful next step: materialize accession-scoped variant rows and keep the structure-backed extension lane separate from the already-held latest surfaces

3. `P02100` `HBE_HUMAN` `Hemoglobin subunit epsilon`
   - Status: structure-only blocked
   - Local variant evidence: none found in the UniProt text payload
   - Local structure evidence: 2 best-structure entries in `data/raw/rcsb_pdbe/20260323T154140Z/P02100/P02100.best_structures.json`
   - Best structure anchor: `1A9W` chains `E/F`, 0.993 coverage
   - Truthful next step: keep blocked until explicit variant evidence appears

## Why These Two First

`P69892` and `P02042` are the only globin accessions in the local mirror set that combine explicit variant signal with local structure signal. That makes them the safest next extension points after the existing `P68871` and `P69905` materialization.

## Boundary

This is report-only. It does not edit code, and it does not alter the protected latest surfaces.

