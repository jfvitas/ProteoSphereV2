# Data Inventory Audit

- Generated at: `2026-03-23T01:22:19.465422+00:00`
- Raw online sources mirrored: `6/6`
- Raw online files mirrored: `34`
- Local sources registered: `39`
- Local registered bytes: `153604410274`
- Canonical status: `ready`
- Canonical run id: `raw-bootstrap-canonical-20260323c`
- Effective source availability: `{'missing': 7, 'partial': 2, 'present': 33}`

## Storage

- Online snapshots: `data/raw`
- Local mirror registry: `data/raw/local_registry`
- Canonical records: `data/canonical`
- Training packages: `data/packages`
- Planning index: `data/planning_index`

## Canonical

- Proteins: `2`
- Ligands: `4124`
- Assays: `5138`
- Structures: `2`
- Store total: `9273`
- Sequence lane: `ready`
- Structure lane: `resolved`
- Assay lane: `resolved`
- Assay unresolved cases: `0`

## Largest Local Sources

- `alphafold_db` (structure, 2 files, 57160101888 bytes)
- `chembl` (protein_ligand, 2 files, 35351586711 bytes)
- `pfam` (pathway_annotation, 2 files, 23811538682 bytes)
- `structures_rcsb` (structure, 19354 files, 23681461165 bytes)
- `pdbbind_pp` (protein_protein, 2800 files, 3163720722 bytes)
- `bindingdb` (protein_ligand, 6972 files, 2984467160 bytes)
- `biolip` (protein_ligand, 3 files, 1175616328 bytes)
- `pdbbind_p_na` (protein_ligand, 1034 files, 901992851 bytes)
- `raw_rcsb` (structure, 39318 files, 211675742 bytes)
- `extracted_interfaces` (protein_protein, 19416 files, 206648796 bytes)

## Online Source Status

- `alphafold` status=`ok` files=`16` release=`2026-03-23`
- `bindingdb` status=`ok` files=`2` release=`2026-03-23`
- `intact` status=`ok` files=`4` release=`2026-03-23`
- `pdbbind` status=`ok` files=`0` release=`2026-03-23`
- `rcsb_pdbe` status=`ok` files=`6` release=`2026-03-23`
- `uniprot` status=`ok` files=`6` release=`2026-03-23`

## Effective Availability

- Online-only sources: `alphafold`, `intact`, `pdbbind`, `rcsb_pdbe`
- Local-only sources: `alphafold_db`, `audit`, `biolip`, `catalog`, `cath`, `chembl`, `extracted_assays`, `extracted_bound_objects`, `extracted_chains`, `extracted_entry`
- Dual-available sources: `bindingdb`, `uniprot`
