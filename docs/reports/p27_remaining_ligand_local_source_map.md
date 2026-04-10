# P27 Remaining Ligand Local Source Map

Date: 2026-03-23

Scope: map the remaining ligand-gap accessions `P00387`, `P09105`, `Q2TAC2`, `Q9NZD4`, and `Q9UCM0` to concrete local `bio-agent-lab` datasets that could plausibly feed ProteoSphere ingestion next.

## Checked Local Dataset Families

- Structure bridge index:
  - `C:\Users\jfvit\Documents\bio-agent-lab\master_pdb_repository.csv`
- Local structure and extracted payloads:
  - `C:\Users\jfvit\Documents\bio-agent-lab\data\raw\rcsb`
  - `C:\Users\jfvit\Documents\bio-agent-lab\data\structures\rcsb`
  - `C:\Users\jfvit\Documents\bio-agent-lab\data\extracted\entry`
  - `C:\Users\jfvit\Documents\bio-agent-lab\data\extracted\bound_objects`
- BioLiP ligand hints:
  - `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\biolip\BioLiP.txt`
- ChEMBL bulk assay source:
  - `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\chembl\chembl_36_sqlite\chembl_36\chembl_36_sqlite\chembl_36.db`
- BindingDB bulk source and local index:
  - `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\bindingdb\BDB-mySQL_All_202603_dmp.zip`
  - `C:\Users\jfvit\Documents\bio-agent-lab\metadata\source_indexes\bindingdb_bulk_index.sqlite`
- AlphaFold local archive index:
  - `C:\Users\jfvit\Documents\bio-agent-lab\metadata\source_indexes\alphafold_archive_index.jsonl.gz`

## Source Map

| Accession | Strongest plausible local feed next | Concrete local datasets | Current truth |
| --- | --- | --- | --- |
| `Q9NZD4` | local structure-bridge ingestion | `master_pdb_repository.csv`; `data\\structures\\rcsb\\1Y01.cif`; `data\\raw\\rcsb\\1Y01.json`; `data\\extracted\\entry\\1Y01.json`; `data\\extracted\\bound_objects\\1Y01.json`; secondary corroboration from `1Z8U` and `3OVU` | strongest local recovery candidate |
| `P00387` | local bulk-assay ingestion first, then optional structure backfill | `data_sources\\chembl\\...\\chembl_36.db`; `data_sources\\biolip\\BioLiP.txt`; `data_sources\\bindingdb\\BDB-mySQL_All_202603_dmp.zip` | credible local ChEMBL lane; no exact local structure payload yet |
| `P09105` | no direct ligand lane; only bulk-assay probe plus structure companion | `data_sources\\bindingdb\\BDB-mySQL_All_202603_dmp.zip`; `data_sources\\chembl\\...\\chembl_36.db`; AlphaFold companion in `alphafold_archive_index.jsonl.gz` | local ligand gap; structure companion exists |
| `Q2TAC2` | no direct ligand lane; only bulk-assay probe plus structure companion | `data_sources\\bindingdb\\BDB-mySQL_All_202603_dmp.zip`; `data_sources\\chembl\\...\\chembl_36.db`; AlphaFold companion in `alphafold_archive_index.jsonl.gz` | local ligand gap; structure companion exists |
| `Q9UCM0` | no truthful local feed | no structure-bridge hits; no ChEMBL hits; no BindingDB index hits; no AlphaFold archive hit | true local acquisition gap |

## Accession Detail

### `Q9NZD4`

Verified local bridge hits in `C:\Users\jfvit\Documents\bio-agent-lab\master_pdb_repository.csv`:

- `1Y01`
- `1Z8U`
- `3OVU`

Verified local files:

- `C:\Users\jfvit\Documents\bio-agent-lab\data\raw\rcsb\1Y01.json`
- `C:\Users\jfvit\Documents\bio-agent-lab\data\structures\rcsb\1Y01.cif`
- `C:\Users\jfvit\Documents\bio-agent-lab\data\extracted\entry\1Y01.json`
- `C:\Users\jfvit\Documents\bio-agent-lab\data\extracted\bound_objects\1Y01.json`
- `C:\Users\jfvit\Documents\bio-agent-lab\data\raw\rcsb\1Z8U.json`
- `C:\Users\jfvit\Documents\bio-agent-lab\data\structures\rcsb\1Z8U.cif`
- `C:\Users\jfvit\Documents\bio-agent-lab\data\extracted\entry\1Z8U.json`
- `C:\Users\jfvit\Documents\bio-agent-lab\data\extracted\bound_objects\1Z8U.json`
- `C:\Users\jfvit\Documents\bio-agent-lab\data\raw\rcsb\3OVU.json`
- `C:\Users\jfvit\Documents\bio-agent-lab\data\structures\rcsb\3OVU.cif`
- `C:\Users\jfvit\Documents\bio-agent-lab\data\extracted\entry\3OVU.json`
- `C:\Users\jfvit\Documents\bio-agent-lab\data\extracted\bound_objects\3OVU.json`

Interpretation:

- `Q9NZD4` should be treated as a local structure-bridge ingestion target, not a fresh-acquisition-first row.
- `1Y01` is the best first ingestion target because the master repository already labels it `protein_ligand` and lists `CHK; HEM; OXY`.
- `1Z8U` and `3OVU` are useful corroboration, but both look cofactor-heavy in the bridge metadata and should stay secondary until exact bound-object role filtering is confirmed.

### `P00387`

Verified local BioLiP hints in `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\biolip\BioLiP.txt`:

- `1UMK`
- `7THG`
- `7TNV`
- `7TSW`
- `7W3O`

Verified local structure/extracted presence check for those PDB IDs:

- no matching files under `data\raw\rcsb`
- no matching files under `data\structures\rcsb`
- no matching files under `data\extracted\entry`
- no matching files under `data\extracted\bound_objects`

Verified local ChEMBL hit from `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\chembl\chembl_36_sqlite\chembl_36\chembl_36_sqlite\chembl_36.db`:

- accession `P00387`
- target `CHEMBL2146`
- pref name `NADH-cytochrome b5 reductase`
- `93` linked activities

Verified local BindingDB index result from `C:\Users\jfvit\Documents\bio-agent-lab\metadata\source_indexes\bindingdb_bulk_index.sqlite`:

- no indexed rows for `P00387`

Verified local AlphaFold companion from `C:\Users\jfvit\Documents\bio-agent-lab\metadata\source_indexes\alphafold_archive_index.jsonl.gz`:

- `AF-P00387-F1-model_v6`

Interpretation:

- `P00387` has a plausible local ingestion lane through ChEMBL first.
- BioLiP gives strong target discovery hints, but not an immediately ingestible local structure payload because the corresponding local RCSB/extracted files are absent.
- Best next feed is ChEMBL target/activity ingestion, with structure backfill as a follow-on task.

### `P09105`

Verified local structure-bridge result:

- no `master_pdb_repository.csv` hit

Verified local ChEMBL result:

- no target rows in `chembl_36.db`

Verified local BindingDB index result:

- no indexed rows in `bindingdb_bulk_index.sqlite`

Verified local AlphaFold companion:

- `AF-P09105-F1-model_v6` present in `alphafold_archive_index.jsonl.gz`

Interpretation:

- `P09105` does not have a truthful local ligand feed today.
- The only plausible local support is structural companion context from AlphaFold if a future ligand source is found elsewhere.
- It should stay in the bulk-assay probe queue, not the local-ingestion queue.

### `Q2TAC2`

Verified local structure-bridge result:

- no `master_pdb_repository.csv` hit

Verified local ChEMBL result:

- no target rows in `chembl_36.db`

Verified local BindingDB index result:

- no indexed rows in `bindingdb_bulk_index.sqlite`

Verified local AlphaFold companion:

- `AF-Q2TAC2-F1-model_v6` present in `alphafold_archive_index.jsonl.gz`

Interpretation:

- `Q2TAC2` also lacks a truthful local ligand feed.
- Like `P09105`, it only has a useful local structure companion, not a local ligand source.
- Keep it in bulk-assay probe or fresh-acquisition follow-up, not immediate ingestion.

### `Q9UCM0`

Verified local structure-bridge result:

- no `master_pdb_repository.csv` hit

Verified local ChEMBL result:

- no target rows in `chembl_36.db`

Verified local BindingDB index result:

- no indexed rows in `bindingdb_bulk_index.sqlite`

Verified local AlphaFold result:

- no `Q9UCM0` entry in `alphafold_archive_index.jsonl.gz`

Interpretation:

- `Q9UCM0` remains a true local-source dead end for ligand recovery.
- There is no plausible local dataset to feed ingestion next without fresh external acquisition.

## Practical Ingestion Order

1. `Q9NZD4`
   Use local structure-bridge assets first, starting with `1Y01`.

2. `P00387`
   Add a local ChEMBL ingestion lane next; treat BioLiP rows as discovery hints until the missing local structure payloads are backfilled.

3. `P09105` and `Q2TAC2`
   Do not spend time on structure-bridge mining locally. Keep them in assay-source probe or fresh-acquisition work.

4. `Q9UCM0`
   Keep explicitly blocked on fresh acquisition.

## Bottom Line

- Immediate local ingestion candidates:
  - `Q9NZD4` via local structure-bridge files
  - `P00387` via local ChEMBL
- Local companion-only rows, not true local ligand feeds:
  - `P09105`
  - `Q2TAC2`
- True local hard gap:
  - `Q9UCM0`

That is the cleanest truthful split for the next ProteoSphere ingestion wave.
