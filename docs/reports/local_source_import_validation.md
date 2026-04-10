# Local Source Import Validation

Date: 2026-03-22

## Scope
- Validate the selected local bio-agent-lab import path using the new local source registry, import manifest builder, and local pair/ligand bridge.
- Keep missing and partial states explicit.

## Files Exercised First
- `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\uniprot\uniprot_sprot.dat.gz`
- `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\reactome\UniProt2Reactome_All_Levels.txt`
- `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\biolip\BioLiP_extracted\BioLiP.txt`
- `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\pdbbind\index\INDEX_general_PP.2020R1.lst`
- `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\pdbbind\index\INDEX_general_PL.2020R1.lst`
- `C:\Users\jfvit\Documents\bio-agent-lab\data\raw\rcsb\1FC2.json`
- `C:\Users\jfvit\Documents\bio-agent-lab\data\raw\rcsb\10JU.json`
- `C:\Users\jfvit\Documents\bio-agent-lab\data\extracted\assays\1A00.json`
- `C:\Users\jfvit\Documents\bio-agent-lab\data\processed\rcsb\1FC2.json`

## What Success Proved
- The import manifest builder projected the local source registry without inventing roots or collapsing missing sources away.
- The selected-corpora manifest kept `uniprot` and `pdbbind_pl` partial, `biogrid` missing, and the present sources present.
- The manifest join index preserved anchor visibility for `P69905`, including the missing `biogrid` lane.
- The protein-protein bridge resolved directly from the real `1FC2` raw RCSB payload and preserved canonical pair identity plus provenance.
- The protein-ligand bridge resolved from a real BioLiP row and preserved the ligand identity (`HEM`) plus provenance.
- The processed `1FC2` fallback payload stayed unresolved because it lacked role-specific accessions.

## Commands Run
- `python -m pytest tests\integration\test_local_source_import.py`
- `python -m ruff check tests\integration\test_local_source_import.py`
- `python -m py_compile tests\integration\test_local_source_import.py`

## Outcome
- The integration path is truthful on selected local corpora.
- Partial and missing states remain explicit.
- No blocker was encountered in the local import validation slice.
