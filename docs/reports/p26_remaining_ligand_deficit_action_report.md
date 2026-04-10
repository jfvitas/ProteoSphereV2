# P26 Remaining Ligand Deficit Action Report

Date: 2026-03-23  
Scope: accession-specific source hunt for the remaining ligand deficits `P00387`, `P09105`, `Q2TAC2`, `Q9NZD4`, and `Q9UCM0`, using current packet truth plus verified `bio-agent-lab` assets.

## Current Truth

These five rows are still ligand-missing in the live packet deficit artifact:

- `ligand:P00387`
- `ligand:P09105`
- `ligand:Q2TAC2`
- `ligand:Q9NZD4`
- `ligand:Q9UCM0`

Source of truth: [packet_deficit_dashboard.json](/D:/documents/ProteoSphereV2/artifacts/status/packet_deficit_dashboard.json)

## Ranked Recovery Order

| Rank | Accession | Classification | Why |
| --- | --- | --- | --- |
| 1 | `Q9NZD4` | likely local recovery | exact local structure and bound-object evidence already exists |
| 2 | `P00387` | likely local bulk-assay recovery | strong local ChEMBL target evidence exists, but exact local structure-ligand files do not |
| 3 | `P09105` | fresh-acquisition gap | no verified local structure-ligand or bulk-assay evidence found |
| 4 | `Q2TAC2` | fresh-acquisition gap | no verified local structure-ligand or bulk-assay evidence found |
| 5 | `Q9UCM0` | true hard gap | no verified local structure, ligand, BindingDB, or ChEMBL support found |

## Accession Actions

### 1. `Q9NZD4`

Classification: likely local recovery

Verified local evidence:

- [master_pdb_repository.csv](/C:/Users/jfvit/Documents/bio-agent-lab/master_pdb_repository.csv) contains exact structure entries linking `Q9NZD4` to:
  - `1Y01` with ligand components `CHK; HEM; OXY`
  - `1Z8U` with ligand component `HEM`
- local structure and extracted files exist for both:
  - [1Y01.cif](/C:/Users/jfvit/Documents/bio-agent-lab/data/structures/rcsb/1Y01.cif)
  - [1Y01 bound_objects](/C:/Users/jfvit/Documents/bio-agent-lab/data/extracted/bound_objects/1Y01.json)
  - [1Z8U.cif](/C:/Users/jfvit/Documents/bio-agent-lab/data/structures/rcsb/1Z8U.cif)
  - [1Z8U bound_objects](/C:/Users/jfvit/Documents/bio-agent-lab/data/extracted/bound_objects/1Z8U.json)
- exact bound-object read:
  - `1Y01` contains `CHK` as `small_molecule`
  - `1Z8U` contains only `HEM` as `cofactor`

Honest read:

- `Q9NZD4` is the best local ligand-recovery candidate in the remaining set.
- `1Y01` is the key recovery structure, not `1Z8U`, because `1Y01` has a true `small_molecule` row while `1Z8U` only confirms a cofactor.

Recommended order:

1. materialize `Q9NZD4` ligand from [1Y01 bound_objects](/C:/Users/jfvit/Documents/bio-agent-lab/data/extracted/bound_objects/1Y01.json)
2. validate accession and chain lineage against [1Y01 entry](/C:/Users/jfvit/Documents/bio-agent-lab/data/extracted/entry/1Y01.json) and [1Y01 raw](/C:/Users/jfvit/Documents/bio-agent-lab/data/raw/rcsb/1Y01.json)
3. keep `1Z8U` as structural corroboration only

### 2. `P00387`

Classification: likely local bulk-assay recovery

Verified local evidence:

- local BioLiP hints exist for `P00387` through `1UMK` in `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\biolip\BioLiP.txt`
- the exact `1UMK` local structure/extracted files are not present under:
  - `C:\Users\jfvit\Documents\bio-agent-lab\data\raw\rcsb`
  - `C:\Users\jfvit\Documents\bio-agent-lab\data\structures\rcsb`
  - `C:\Users\jfvit\Documents\bio-agent-lab\data\extracted\bound_objects`
- local BindingDB bulk index has `0` rows for `P00387` in:
  - `C:\Users\jfvit\Documents\bio-agent-lab\metadata\source_indexes\bindingdb_bulk_index.sqlite`
- local ChEMBL has a real target match for `P00387`:
  - accession `P00387`
  - target `CHEMBL2146`
  - pref name `NADH-cytochrome b5 reductase`
  - `93` linked activity rows
  - source DB: [chembl_36.db](/C:/Users/jfvit/Documents/bio-agent-lab/data_sources/chembl/chembl_36_sqlite/chembl_36/chembl_36_sqlite/chembl_36.db)

Honest read:

- `P00387` does not currently have a verified exact local structure-ligand path.
- It does have a strong local ChEMBL recovery lane, which makes it materially better than the pure fresh-acquisition rows.

Recommended order:

1. query ChEMBL first using [chembl_36.db](/C:/Users/jfvit/Documents/bio-agent-lab/data_sources/chembl/chembl_36_sqlite/chembl_36/chembl_36_sqlite/chembl_36.db)
2. only if needed, reacquire `1UMK` as a structure-backed secondary lane
3. do not wait on BindingDB for this row because the local BindingDB index is already empty on accession

### 3. `P09105`

Classification: fresh-acquisition gap

Verified local evidence:

- no hit in [master_pdb_repository.csv](/C:/Users/jfvit/Documents/bio-agent-lab/master_pdb_repository.csv)
- no local BindingDB bulk index rows in:
  - `C:\Users\jfvit\Documents\bio-agent-lab\metadata\source_indexes\bindingdb_bulk_index.sqlite`
- no local ChEMBL target rows in:
  - [chembl_36.db](/C:/Users/jfvit/Documents/bio-agent-lab/data_sources/chembl/chembl_36_sqlite/chembl_36/chembl_36_sqlite/chembl_36.db)
- no direct sampled BioLiP hit in:
  - `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\biolip\BioLiP.txt`

Honest read:

- `P09105` currently has no verified local ligand-recovery lane.

Recommended order:

1. fresh external structure bridge search
2. fresh external BindingDB and ChEMBL acquisition
3. only after a real hit, mirror into local raw and extracted layers

### 4. `Q2TAC2`

Classification: fresh-acquisition gap

Verified local evidence:

- no hit in [master_pdb_repository.csv](/C:/Users/jfvit/Documents/bio-agent-lab/master_pdb_repository.csv)
- no local BindingDB bulk index rows in:
  - `C:\Users\jfvit\Documents\bio-agent-lab\metadata\source_indexes\bindingdb_bulk_index.sqlite`
- no local ChEMBL target rows in:
  - [chembl_36.db](/C:/Users/jfvit/Documents/bio-agent-lab/data_sources/chembl/chembl_36_sqlite/chembl_36/chembl_36_sqlite/chembl_36.db)
- no direct sampled BioLiP hit in:
  - `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\biolip\BioLiP.txt`

Honest read:

- `Q2TAC2` is currently a true acquisition-led ligand gap.

Recommended order:

1. fresh external structure bridge search
2. fresh external BindingDB and ChEMBL acquisition
3. if both stay empty, keep explicit fail-closed state

### 5. `Q9UCM0`

Classification: true hard gap

Verified local evidence:

- no hit in [master_pdb_repository.csv](/C:/Users/jfvit/Documents/bio-agent-lab/master_pdb_repository.csv)
- no local BindingDB bulk index rows in:
  - `C:\Users\jfvit\Documents\bio-agent-lab\metadata\source_indexes\bindingdb_bulk_index.sqlite`
- no local ChEMBL target rows in:
  - [chembl_36.db](/C:/Users/jfvit/Documents/bio-agent-lab/data_sources/chembl/chembl_36_sqlite/chembl_36/chembl_36_sqlite/chembl_36.db)
- no direct sampled BioLiP hit in:
  - `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\biolip\BioLiP.txt`
- no local AlphaFold member in the large local tar was previously found for `Q9UCM0`

Honest read:

- `Q9UCM0` is the hardest remaining ligand row because it is also the hardest remaining structure row.
- There is no verified local evidence path to exploit first.

Recommended order:

1. fresh external AlphaFold DB and structure bridge acquisition
2. fresh external BindingDB and ChEMBL acquisition
3. do not attempt a local-only rescue first

## Path Priority By Accessions

### Local-first

- `Q9NZD4`
- `P00387`

### Fresh-acquisition-first

- `P09105`
- `Q2TAC2`
- `Q9UCM0`

## Bottom Line

These five ligand deficits should not be treated as one batch.

- `Q9NZD4` is the clear best local rescue.
- `P00387` has a credible local ChEMBL recovery path, but not yet a verified local structure-ligand path.
- `P09105` and `Q2TAC2` are honest acquisition gaps.
- `Q9UCM0` is the true hard stop row and should remain explicitly blocked until fresh structure and ligand evidence is acquired.
