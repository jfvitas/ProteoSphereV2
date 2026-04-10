# Q9UCM0 Acquisition Brief

Date: 2026-03-23

## Current Truth

`Q9UCM0` remains unresolved for:

- `structure`
- `ppi`
- `ligand`

It still has only sequence coverage in the current pipeline state.

## Exact Evidence

Local `bio-agent-lab` evidence does not provide a structure or PPI rescue:

- [import_manifest.json](/D:/documents/ProteoSphereV2/data/raw/local_registry/20260323T003221Z/import_manifest.json)
  `Q9UCM0` maps only to `uniprot`
- [alphafold inventory](/D:/documents/ProteoSphereV2/data/raw/local_registry/20260323T003221Z/alphafold_db/inventory.json)
  no `Q9UCM0` join key
- [structures_rcsb inventory](/D:/documents/ProteoSphereV2/data/raw/local_registry/20260323T003221Z/structures_rcsb/inventory.json)
  no `Q9UCM0` join key
- [raw_rcsb inventory](/D:/documents/ProteoSphereV2/data/raw/local_registry/20260323T003221Z/raw_rcsb/inventory.json)
  no `Q9UCM0` join key
- [master_pdb_repository.csv](/C:/Users/jfvit/Documents/bio-agent-lab/master_pdb_repository.csv)
  no `Q9UCM0` row
- local AlphaFold tar `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\alphafold\swissprot_pdb_v6.tar`
  archive probe returned `found=0`

Current online-mirror artifacts also do not rescue it:

- [Q9UCM0.best_structures.json](/D:/documents/ProteoSphereV2/data/raw/rcsb_pdbe/20260323T154140Z/Q9UCM0/Q9UCM0.best_structures.json)
  empty list
- [Q9UCM0.interactor.json](/D:/documents/ProteoSphereV2/data/raw/intact/20260323T154140Z/Q9UCM0/Q9UCM0.interactor.json)
  reachable, but not a direct canonical `Q9UCM0` pair rescue
- [Q9UCM0.psicquic.tab25.txt](/D:/documents/ProteoSphereV2/data/raw/intact/20260323T154140Z/Q9UCM0/Q9UCM0.psicquic.tab25.txt)
  includes `Q9UCM0` only as alternate ID noise on `P69905` lines
- [p15_upgraded_cohort_slice.json](/D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/p15_upgraded_cohort_slice.json)
  `bridge.state = "missing"` and `curated_ppi.empty_state = "reachable_empty"`
- [packet_deficit_dashboard.json](/D:/documents/ProteoSphereV2/artifacts/status/packet_deficit_dashboard.json)
  still missing `structure:Q9UCM0`, `ppi:Q9UCM0`, and `ligand:Q9UCM0`

## Required New Acquisitions

### 1. AlphaFold DB fresh acquisition

Goal:
- determine whether a current AlphaFold prediction exists for `Q9UCM0`

Required output:
- accession-scoped prediction JSON
- structure asset (`.pdb`, `.cif`, or `.bcif`)
- frozen raw manifest entry if present

Stop condition:
- no current AlphaFold prediction resolves for `Q9UCM0`

### 2. RCSB/PDBe fresh re-probe

Goal:
- determine whether a current experimental structure bridge now exists for `Q9UCM0`

Required output:
- fresh best-structures mapping
- entry payload for any returned PDB target
- local mmCIF if a target exists

Stop condition:
- best-structures probe still returns no target

### 3. Guarded BioGRID procurement

Goal:
- expand beyond the current weak IntAct mirror and test whether curated PPI coverage exists for `Q9UCM0`

Required output:
- frozen guarded BioGRID raw snapshot
- parsed MITAB rows for any `Q9UCM0` interactor hits
- direct pair candidates, not alias-only references

Stop condition:
- no direct `Q9UCM0` interactor rows after guarded validation

### 4. Guarded STRING procurement

Goal:
- provide broader network evidence if curated interaction sources remain empty

Required output:
- frozen guarded STRING snapshot
- alias/info joins supporting a direct `Q9UCM0` node
- network edges attributable to `Q9UCM0`

Stop condition:
- no direct STRING node/edge mapping after guarded validation

## Recommended Order

1. AlphaFold DB accession fetch for `Q9UCM0`
2. RCSB/PDBe re-probe for `Q9UCM0`
3. BioGRID guarded run
4. STRING guarded run

This order keeps the cheapest direct structure checks first and only then opens heavier guarded PPI procurement.
