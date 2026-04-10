# Bio-Agent-Lab Local Source Inventory

Date: 2026-03-22  
Scope: `C:\Users\jfvit\Documents\bio-agent-lab\data` and `C:\Users\jfvit\Documents\bio-agent-lab\data_sources`

## Snapshot

The local workspace already carries a broad reusable corpus stack:

- `data/raw/rcsb` has `39,318` accession JSON payloads.
- `data/structures/rcsb` has `19,354` mmCIF files.
- `data/extracted/{assays,bound_objects,chains,entry,interfaces,provenance}` each has `19,416` accession-level JSON files.
- `data/raw/bindingdb` has `6,971` per-PDB cache payloads.
- `data_sources/pdbbind` has `4,413` files, including the licensed P-L / P-P / NA-L / P-NA subtrees.
- `data_sources/alphafold`, `bindingdb`, `biolip`, `chembl`, `interpro`, `pdbbind`, `pfam`, `reactome`, `scope`, and `uniprot` are all populated.

The best current read is that the workspace is strong for protein, pair, ligand, pathway, annotation, and derived-training reuse, but still thin on a few interaction and motif sources.

## Preload-Worthy

These are small, high-signal control artifacts that should stay cheap to load eagerly:

- `C:\Users\jfvit\Documents\bio-agent-lab\data\catalog\download_manifest.csv`
- `C:\Users\jfvit\Documents\bio-agent-lab\data\catalog\source_state\bindingdb.json`
- `C:\Users\jfvit\Documents\bio-agent-lab\data\catalog\source_state\chembl.json`
- `C:\Users\jfvit\Documents\bio-agent-lab\data\reports\source_capabilities.json`
- `C:\Users\jfvit\Documents\bio-agent-lab\data\reports\source_lifecycle_report.json`
- `C:\Users\jfvit\Documents\bio-agent-lab\data\reports\summary.json`
- `C:\Users\jfvit\Documents\bio-agent-lab\data\reports\audit_summary.json`
- `C:\Users\jfvit\Documents\bio-agent-lab\data\releases\latest_release.json`
- `C:\Users\jfvit\Documents\bio-agent-lab\data\releases\test_v1\release_snapshot_manifest.json`
- `C:\Users\jfvit\Documents\bio-agent-lab\data\releases\test_v1\dataset_release_manifest.json`
- `C:\Users\jfvit\Documents\bio-agent-lab\data\training_examples\training_manifest.json`
- `C:\Users\jfvit\Documents\bio-agent-lab\data\splits\metadata.json`
- `C:\Users\jfvit\Documents\bio-agent-lab\data\splits\split_diagnostics.json`
- `C:\Users\jfvit\Documents\bio-agent-lab\data\features\feature_manifest.json`
- `C:\Users\jfvit\Documents\bio-agent-lab\data\graph\graph_manifest.json`

These are the right layer for operator views, release summaries, and planning-index bootstrap.

## Index-Worthy

These are the reusable corpora and derived datasets that should be searchable or index-backed:

- Sequence and annotation:
  - `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\uniprot\uniprot_sprot.dat.gz`
  - `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\interpro\interpro.xml.gz`
  - `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\pfam\Pfam-A.full.gz`
  - `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\reactome\UniProt2Reactome_All_Levels.txt`
  - `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\reactome\ReactomePathways.txt`
  - `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\reactome\ReactomePathwaysRelation.txt`
  - `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\cath\cath-domain-list.txt`
  - `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\scope\dir.cla.scope.2.08-stable.txt`
  - `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\scope\dir.des.scope.txt`
- Structures and pair context:
  - `C:\Users\jfvit\Documents\bio-agent-lab\data\raw\rcsb\10JU.json`
  - `C:\Users\jfvit\Documents\bio-agent-lab\data\structures\rcsb\10JU.cif`
  - `C:\Users\jfvit\Documents\bio-agent-lab\data\extracted\entry\10JU.json`
  - `C:\Users\jfvit\Documents\bio-agent-lab\data\extracted\chains\10JU.json`
  - `C:\Users\jfvit\Documents\bio-agent-lab\data\extracted\interfaces\10JU.json`
  - `C:\Users\jfvit\Documents\bio-agent-lab\data\extracted\provenance\10JU.json`
- Protein-ligand and assay context:
  - `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\bindingdb\BDB-mySQL_All_202603_dmp.zip`
  - `C:\Users\jfvit\Documents\bio-agent-lab\data\raw\bindingdb\1BB0.json`
  - `C:\Users\jfvit\Documents\bio-agent-lab\data\extracted\assays\1A00.json`
  - `C:\Users\jfvit\Documents\bio-agent-lab\data\extracted\bound_objects\1A00.json`
- Curated ligand/protein-pair corpora:
  - `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\biolip\BioLiP.txt`
  - `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\pdbbind\index\INDEX_general_PL.2020R1.lst`
  - `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\pdbbind\P-P\P-P\6o3o_complex.pdb`
  - `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\pdbbind\P-L`
  - `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\pdbbind\NA-L`

The graph and training layers are also worth indexing because they are already curated for downstream reuse:

- `C:\Users\jfvit\Documents\bio-agent-lab\data\models\model_studio\graph_dataset\graph_dataset_records.json`
- `C:\Users\jfvit\Documents\bio-agent-lab\data\models\model_studio\pyg_ready_graphs\pyg_ready_graph_samples.json`
- `C:\Users\jfvit\Documents\bio-agent-lab\data\graph\graph_nodes.json`
- `C:\Users\jfvit\Documents\bio-agent-lab\data\graph\graph_edges.json`
- `C:\Users\jfvit\Documents\bio-agent-lab\data\training_examples\training_examples.json`
- `C:\Users\jfvit\Documents\bio-agent-lab\data\releases\test_v1\custom_training_set.csv`
- `C:\Users\jfvit\Documents\bio-agent-lab\data\releases\test_v1\master_pdb_repository.csv`
- `C:\Users\jfvit\Documents\bio-agent-lab\data\releases\test_v1\master_pdb_pairs.csv`

## Lazy-Import-Worthy

These assets are big enough or granular enough that the default should be deferred loading:

- `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\chembl\chembl_36_sqlite\chembl_36\chembl_36_sqlite\chembl_36.db` is a ~29.7 GB SQLite snapshot.
- `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\alphafold\swissprot_pdb_v6.tar` is a ~28.6 GB archive.
- `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\biolip\BioLiP.txt` is a ~548 MB text snapshot.
- `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\bindingdb\BDB-mySQL_All_202603_dmp.zip` is a large bulk dump.
- `C:\Users\jfvit\Documents\bio-agent-lab\data\raw\rcsb\*.json` and `C:\Users\jfvit\Documents\bio-agent-lab\data\structures\rcsb\*.cif` should be selected by accession, not preloaded wholesale.
- `C:\Users\jfvit\Documents\bio-agent-lab\data\extracted\{assays,bound_objects,chains,entry,interfaces,provenance}\*.json` are per-accession payloads and should stay selection-driven.
- `C:\Users\jfvit\Documents\bio-agent-lab\data\custom_training_sets\*\*.csv` and `*.json` are release artifacts, not core bootstrap inputs.
- `C:\Users\jfvit\Documents\bio-agent-lab\data\models\model_studio\runs\*` are experiment outputs and should be loaded only when a specific run is being inspected.

For exact pair/structure examples, the PDBbind trees are the best lazy-import candidates:

- `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\pdbbind\P-P\P-P\6o3o_complex.pdb`
- `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\pdbbind\P-L\...`
- `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\pdbbind\NA-L\...`

## Modality Notes

- Protein-protein:
  - Strong local coverage exists in `data/raw/rcsb`, `data/structures/rcsb`, `data/extracted/interfaces`, `data/extracted/provenance`, `data_sources/pdbbind/P-P`, and `data_sources/biolip/BioLiP.txt`.
  - `data_sources/string`, `data_sources/biogrid`, and `data_sources/intact` are still missing from the local source inventory.
- Protein-ligand:
  - Strong coverage exists in `data_sources/bindingdb`, `data/raw/bindingdb`, `data_sources/chembl`, `data_sources/pdbbind/P-L`, `data_sources/biolip`, and `data/extracted/assays`.
- Pathway and annotation:
  - `data_sources/reactome`, `data_sources/interpro`, `data_sources/pfam`, `data_sources/cath`, and `data_sources/scope` are the main reusable local corpora.
- Sequence:
  - `data_sources/uniprot/uniprot_sprot.dat.gz` is the primary reviewed-sequence anchor.
  - The raw `data\raw\uniprot` folder is not currently the main local asset here.
- Structure:
  - `data_sources/alphafold/swissprot_pdb_v6.tar`, `data\raw\rcsb`, and `data\structures\rcsb` are the key structure lanes.
- Extracted assay/interface/provenance:
  - The entire `data\extracted` subtree is important because it is already normalized by accession and split into assay, interface, bound-object, chain, entry, and provenance views.

## Gaps And Blockers

- Missing interaction-network sources: `STRING`, `BioGRID`, and `IntAct` are not present as staged local corpora.
- Missing kinetics / motif corpora: `SABIO-RK`, `PROSITE`, `ELM`, `MegaMotifBase`, and `Motivated Proteins` are not staged locally.
- The inventory is strong enough to support release-prep and selective materialization, but those missing sources still limit broader interaction and motif coverage.

## Concrete Reuse Recommendation

- Preload the manifests, release summaries, split diagnostics, and source-state JSON first.
- Index the reviewed sequence, pathway, annotation, pair, and graph-derived corpora next.
- Load raw structure, assay, and per-accession extraction files lazily and only for the selected training set or the exact analysis question.
- Keep the large bulk archives and run outputs deferred unless the task is specifically about refresh, rebuild, or provenance audit.
