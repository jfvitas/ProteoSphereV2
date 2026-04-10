# Q9UCM0 Acquisition Proof

- Generated at: `2026-03-23T19:25:28.390474+00:00`
- Status: `unresolved_requires_new_acquisition`
- Truth: `structure=missing`, `ligand=missing`, `ppi=missing`
- Sequence reference: `present` via `['uniprot']`

## What Was Checked

- Online raw snapshots: `structure`, `ligand`, `ppi`
- Registered local sources: `uniprot`, `alphafold_db`, `raw_rcsb`, `structures_rcsb`, `extracted_entry`, `extracted_interfaces`, `bindingdb`, `chembl`, `biolip`, `extracted_assays`, `extracted_bound_objects`, `intact`, `biogrid`, `string`, `pdbbind_pp`
- Local registry run: `D:\documents\ProteoSphereV2\data\raw\local_registry_runs\LATEST.json`
- Import manifest: `D:\documents\ProteoSphereV2\data\raw\local_registry\20260323T003221Z\import_manifest.json`

## Summary

| Modality | Online snapshot | Registered local sources | State | Next action |
| --- | --- | --- | --- | --- |
| structure | empty best-structures list | uniprot:partial [P69905, P68871, P09105, Q9UCM0]; alphafold_db:present [P69905, P68871]; raw_rcsb:present [10JU, 4HHB, 9LWP]; structures_rcsb:present [10JU, 4HHB, 9LWP]; extracted_entry:present [10JU, 4HHB]; extracted_interfaces:present [10JU, 4HHB] | missing | AlphaFold DB explicit accession probe |
| ligand | bindingdb hit count is zero | uniprot:partial [P69905, P68871, P09105, Q9UCM0]; bindingdb:present [1BB0, 5Q16, 5TQF]; chembl:present [5JJM, P31749]; biolip:present [4HHB, 9S6C]; extracted_assays:present [10JU, 1A00]; extracted_bound_objects:present [10JU, 1A00] | missing | BindingDB / ChEMBL accession probe |
| ppi | IntAct resolves to a partner accession and alias-only row(s) | uniprot:partial [P69905, P68871, P09105, Q9UCM0]; intact:missing [P69905, P09105]; biogrid:missing [P69905, P09105]; string:missing [P69905, P09105]; pdbbind_pp:present [9LWP, 9QTN, 9SYV]; extracted_interfaces:present [10JU, 4HHB] | missing | BioGRID guarded procurement first wave |

## Findings

### `structure:Q9UCM0`

- Online raw snapshot: `D:\documents\ProteoSphereV2\data\raw\rcsb_pdbe\20260323T182231Z\Q9UCM0\Q9UCM0.best_structures.json`
- Online state: `empty`
- Absent: current online structure snapshot is empty, local registry maps Q9UCM0 only to uniprot, not to a structure source, registered local structure sources checked: alphafold_db, raw_rcsb, structures_rcsb, extracted_entry, extracted_interfaces
- Next acquisition action: `AlphaFold DB explicit accession probe`

Checked local sources:
- `uniprot` -> `partial`; join_keys=['P69905', 'P68871', 'P09105', 'Q9UCM0']; contains_Q9UCM0=`True`
- `alphafold_db` -> `present`; join_keys=['P69905', 'P68871']; contains_Q9UCM0=`False`
- `raw_rcsb` -> `present`; join_keys=['10JU', '4HHB', '9LWP']; contains_Q9UCM0=`False`
- `structures_rcsb` -> `present`; join_keys=['10JU', '4HHB', '9LWP']; contains_Q9UCM0=`False`
- `extracted_entry` -> `present`; join_keys=['10JU', '4HHB']; contains_Q9UCM0=`False`
- `extracted_interfaces` -> `present`; join_keys=['10JU', '4HHB']; contains_Q9UCM0=`False`

### `ligand:Q9UCM0`

- Online raw snapshot: `D:\documents\ProteoSphereV2\data\raw\bindingdb\20260323T182231Z\Q9UCM0\Q9UCM0.bindingdb.json`
- Online state: `empty`
- Absent: current online ligand snapshot is empty, local registry does not expose a Q9UCM0 ligand join key, registered local ligand sources checked: bindingdb, chembl, biolip, extracted_assays, extracted_bound_objects
- Next acquisition action: `BindingDB / ChEMBL accession probe`

Checked local sources:
- `uniprot` -> `partial`; join_keys=['P69905', 'P68871', 'P09105', 'Q9UCM0']; contains_Q9UCM0=`True`
- `bindingdb` -> `present`; join_keys=['1BB0', '5Q16', '5TQF']; contains_Q9UCM0=`False`
- `chembl` -> `present`; join_keys=['5JJM', 'P31749']; contains_Q9UCM0=`False`
- `biolip` -> `present`; join_keys=['4HHB', '9S6C']; contains_Q9UCM0=`False`
- `extracted_assays` -> `present`; join_keys=['10JU', '1A00']; contains_Q9UCM0=`False`
- `extracted_bound_objects` -> `present`; join_keys=['10JU', '1A00']; contains_Q9UCM0=`False`

### `ppi:Q9UCM0`

- Online raw snapshot: `D:\documents\ProteoSphereV2\data\raw\intact\20260323T182231Z\Q9UCM0\Q9UCM0.interactor.json`
- Online state: `alias_only`
- Absent: local registry does not expose a Q9UCM0 PPI join key, registered local ppi sources checked: intact, biogrid, string, pdbbind_pp, extracted_interfaces
- Next acquisition action: `BioGRID guarded procurement first wave`

Checked local sources:
- `uniprot` -> `partial`; join_keys=['P69905', 'P68871', 'P09105', 'Q9UCM0']; contains_Q9UCM0=`True`
- `intact` -> `missing`; join_keys=['P69905', 'P09105']; contains_Q9UCM0=`False`
- `biogrid` -> `missing`; join_keys=['P69905', 'P09105']; contains_Q9UCM0=`False`
- `string` -> `missing`; join_keys=['P69905', 'P09105']; contains_Q9UCM0=`False`
- `pdbbind_pp` -> `present`; join_keys=['9LWP', '9QTN', '9SYV']; contains_Q9UCM0=`False`
- `extracted_interfaces` -> `present`; join_keys=['10JU', '4HHB']; contains_Q9UCM0=`False`

## Next Acquisition Order

- `AlphaFold DB explicit accession probe`
- `RCSB/PDBe fresh best-structures re-probe`
- `BioGRID guarded procurement first wave`
- `STRING guarded procurement first wave`
- `BindingDB / ChEMBL accession probe`