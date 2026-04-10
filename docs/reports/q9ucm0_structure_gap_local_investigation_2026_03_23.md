# Q9UCM0 Local Structure Gap Investigation

Date: 2026-03-23

## Scope

Determine whether `bio-agent-lab` already contains a truthful local structure recovery path for `Q9UCM0`, or whether `Q9UCM0` still requires fresh structure acquisition.

## Checked Paths

Registry and inventory paths:

- `D:\documents\ProteoSphereV2\data\raw\local_registry_runs\LATEST.json`
- `D:\documents\ProteoSphereV2\data\raw\local_registry\20260323T003221Z\import_manifest.json`
- `D:\documents\ProteoSphereV2\data\raw\local_registry\20260323T003221Z\alphafold_db\inventory.json`
- `D:\documents\ProteoSphereV2\data\raw\local_registry\20260323T003221Z\structures_rcsb\inventory.json`
- `D:\documents\ProteoSphereV2\data\raw\local_registry\20260323T003221Z\raw_rcsb\inventory.json`
- `D:\documents\ProteoSphereV2\data\raw\local_registry\20260323T003221Z\uniprot\inventory.json`

Local `bio-agent-lab` paths:

- `C:\Users\jfvit\Documents\bio-agent-lab\master_pdb_repository.csv`
- `C:\Users\jfvit\Documents\bio-agent-lab\data\releases\test_v1\master_pdb_repository.csv`
- `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\alphafold\swissprot_pdb_v6.tar`
- `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\alphafold`
- `C:\Users\jfvit\Documents\bio-agent-lab\data\structures\rcsb`
- `C:\Users\jfvit\Documents\bio-agent-lab\data\raw\rcsb`

Checked and absent:

- `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\catalog\master_pdb_repository.csv` does not exist.

## Findings

### 1. Registry evidence does not show a local structure binding for `Q9UCM0`

`D:\documents\ProteoSphereV2\data\raw\local_registry\20260323T003221Z\import_manifest.json` maps `Q9UCM0` only to:

- `uniprot`

It does not map `Q9UCM0` to:

- `alphafold_db`
- `structures_rcsb`
- `raw_rcsb`
- `extracted_chains`
- `extracted_entry`

This matters because the import manifest is the local registry's accession-to-source index. On the local registry evidence alone, `Q9UCM0` has sequence coverage, not structure coverage.

### 2. AlphaFold local inventory does not expose `Q9UCM0`

`D:\documents\ProteoSphereV2\data\raw\local_registry\20260323T003221Z\alphafold_db\inventory.json` shows:

- present roots:
  - `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\alphafold\swissprot_pdb_v6.tar`
  - `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\alphafold`
- indexed `join_keys`:
  - `P69905`
  - `P68871`

No `Q9UCM0` join key is present in the AlphaFold registry inventory.

I also checked the archive listing for:

- `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\alphafold\swissprot_pdb_v6.tar`

No archive member path containing `Q9UCM0` was found.

I also checked for direct filesystem path hits under:

- `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\alphafold`

No file path containing `Q9UCM0` was found.

### 3. Local RCSB structure mirrors do not expose `Q9UCM0`

`D:\documents\ProteoSphereV2\data\raw\local_registry\20260323T003221Z\structures_rcsb\inventory.json` shows:

- present root:
  - `C:\Users\jfvit\Documents\bio-agent-lab\data\structures\rcsb`
- indexed `join_keys`:
  - `10JU`
  - `4HHB`
  - `9LWP`

`D:\documents\ProteoSphereV2\data\raw\local_registry\20260323T003221Z\raw_rcsb\inventory.json` shows:

- present root:
  - `C:\Users\jfvit\Documents\bio-agent-lab\data\raw\rcsb`
- indexed `join_keys`:
  - `10JU`
  - `4HHB`
  - `9LWP`

No `Q9UCM0` join key is present in either local RCSB structure inventory.

I also checked for direct filesystem path hits under:

- `C:\Users\jfvit\Documents\bio-agent-lab\data\structures\rcsb`

No file path containing `Q9UCM0` was found.

### 4. The local PDB master catalogs do not map `Q9UCM0`

I checked:

- `C:\Users\jfvit\Documents\bio-agent-lab\master_pdb_repository.csv`
- `C:\Users\jfvit\Documents\bio-agent-lab\data\releases\test_v1\master_pdb_repository.csv`

Neither file contains `Q9UCM0`.

That removes the strongest path-based local recovery route for turning a UniProt accession into local PDB-backed structure assets.

### 5. `Q9UCM0` is locally present only in sequence inventory

`D:\documents\ProteoSphereV2\data\raw\local_registry\20260323T003221Z\uniprot\inventory.json` includes `Q9UCM0` in `join_keys`, but that source is category `sequence`, not `structure`.

That is useful as a sequence anchor, but it is not a truthful local structure recovery path.

## Conclusion

`Q9UCM0` remains a true fresh-acquisition structure gap.

The local `bio-agent-lab` evidence does **not** support a truthful claim that a recoverable structure payload already exists for `Q9UCM0`. Specifically:

- the registry index binds `Q9UCM0` only to `uniprot`
- the local AlphaFold inventory does not expose `Q9UCM0`
- the local RCSB inventories do not expose `Q9UCM0`
- the local `master_pdb_repository.csv` copies do not map `Q9UCM0`
- no accession-specific local file path was found under the checked AlphaFold or RCSB roots

Given those facts, the correct operational interpretation is:

- `Q9UCM0` should stay marked as a structure deficit
- generic presence of large local AlphaFold or RCSB mirrors should **not** be treated as recovery
- any future resolution for `Q9UCM0` needs a fresh acquisition or a newly indexed accession-specific local payload
