# Procurement Expansion Inventory (2026-04-05)

## Current mirrored baseline

- Current task-oriented raw mirror under `data/raw/protein_data_scope_seed`: `1,634,856,956,745` bytes (`1,522.58 GiB`, `1.63 TB`)
- Current PDBbind local-copy lane under `data/raw/local_copies/pdbbind`: `7,460,657,307` bytes (`6.95 GiB`)
- Interpretation: the repo already holds a strong curated corpus, but it is not an exhaustive "all valuable upstream products" mirror.

## High-value remaining datasets worth considering

### UniProt secondary products not yet mirrored

1. UniProt reference proteomes bulk tarball
   - `Reference_Proteomes_2026_01.tar.gz`
   - Size: `334,210,140,111` bytes (`311.26 GiB`, `334.21 GB`)
   - Why it matters: broad representative proteome coverage and cleaner reference-oriented organism expansion than raw TrEMBL alone.

2. UniProt reference proteomes additional tarball
   - `Reference_Proteomes_2026_01_additional.tar.gz`
   - Size: `20,973,274,580` bytes (`19.53 GiB`, `20.97 GB`)
   - Why it matters: auxiliary reference-proteome layer paired with the main reference proteome release.

3. UniProt taxonomic divisions
   - Source family: `knowledgebase/taxonomic_divisions`
   - Total size: `370,802,706,275` bytes (`345.34 GiB`, `370.80 GB`)
   - Why it matters: species/division-specific slices that can support taxon-aware partitioning, focused retrieval, and lower-cost organism-specific workflows.

4. UniProt embeddings
   - Source family: `knowledgebase/embeddings`
   - Total currently exposed size: `1,662,832,048` bytes (`1.55 GiB`, `1.66 GB`)
   - Current visible coverage includes `uniprot_sprot` and selected model/reference proteomes.
   - Why it matters: precomputed representation layer that can feed retrieval, clustering, baseline feature augmentation, and candidate ranking.

5. UniProt pan proteomes
   - Source family: `knowledgebase/pan_proteomes`
   - Total size from `RELEASE.metalink`: `5,966,267,722` bytes (`5.56 GiB`, `5.97 GB`)
   - File count: `6,010`
   - Why it matters: strain/population-level protein universe slices that can help when breadth within a species matters.

6. UniProt variants
   - Source family: `knowledgebase/variants`
   - Total size: `785,722,197` bytes (`0.73 GiB`, `0.79 GB`)
   - Why it matters: structured variant expansions beyond current core entry pulls, especially for disease and isoform-adjacent modeling.

7. UniProt genome annotation tracks
   - Source family: `knowledgebase/genome_annotation_tracks`
   - Total size of current release tree: `227,485,757` bytes (`0.21 GiB`, `0.23 GB`)
   - Why it matters: genomic-coordinate alignment and feature track export for a small set of key reference proteomes.

8. UniProt proteomics mapping
   - Source family: `knowledgebase/proteomics_mapping`
   - Total size: `213,908,794` bytes (`0.20 GiB`, `0.21 GB`)
   - Why it matters: peptide evidence overlays and MS-oriented support features for selected proteomes.

### AlphaFold DB expansion beyond current Swiss-Prot bulk tarballs

1. AlphaFold latest additional current-release files
   - Total additional size visible in `ftp.ebi.ac.uk/pub/databases/alphafold/latest` beyond already-downloaded `swissprot_cif_v6.tar` and `swissprot_pdb_v6.tar`:
   - `88,368,233,510` bytes (`82.30 GiB`, `88.37 GB`)
   - Includes:
     - model-organism proteome tarballs such as `UP000005640_9606_HUMAN_v6.tar`, `UP000000589_10090_MOUSE_v6.tar`, `UP000006548_3702_ARATH_v6.tar`, `UP000007305_4577_MAIZE_v6.tar`
     - `msa_depths.csv`
     - many other curated proteome tarballs in the current `latest` tree
   - Why it matters: broader predicted-structure coverage beyond Swiss-Prot and stronger proteome-specific structure context.

2. AlphaFold historical/versioned trees
   - Current assessment: optional and not recommended for first expansion pass
   - Why it matters: archival reproducibility only
   - Planning note: treat as cold-storage-only if ever mirrored

### Optional orthology-oriented add-on

1. EBI Reference Proteomes QfO package
   - `QfO_release_2025_04.tar.gz`: `2,158,796,060` bytes (`2.01 GiB`, `2.16 GB`)
   - `QfO_release_2025_04_additional.tar.gz`: `20,973,274,580` bytes (`19.53 GiB`, `20.97 GB`)
   - Combined: `23,132,070,640` bytes (`21.54 GiB`, `23.13 GB`)
   - Why it matters: compact orthology-friendly species set, useful if we want a smaller reference-proteome lane without mirroring the full UniProt reference-proteome bulk.

## Important source-by-source reality check

### Already broad enough for now

- STRING v12
  - We already hold the heavy interaction, homology, orthology, enrichment, alias, sequence, and embedding files.
- BindingDB
  - We already hold the main TSV, 2D/3D SDF, articles, ChEMBL-linked, patents, target FASTA, UniProt mapping, and MySQL dump.
- SIFTS
  - We already hold a broad crosswalk layer across UniProt, taxonomy, GO, InterPro, Pfam, Ensembl, observed segments, and structural classifications.
- Reactome
  - We already hold pathway/reaction maps, stable IDs, role tables, PMIDs, IntAct static export, and graphdb exports.

### Valuable but not yet maximally mirrored

- UniProt
  - Strong backbone already mirrored, but many secondary high-value families are still absent.
- AlphaFold DB
  - Swiss-Prot tarballs are present, but most current-release proteome tarballs are not.
- InterPro
  - Core truth-bearing files are mirrored, but this is still a curated core rather than a maximal mirror.
- IntAct
  - Good starter bulk, but not every companion export family.

### Mostly an integration/automation gap, not a storage gap

- PDBbind
  - We already have local raw copies in `data/raw/local_copies/pdbbind`.
  - Main remaining work is standardizing acquisition, indexing, and integration into the structured dataset pipeline rather than buying large additional capacity.

## Storage totals for planning

### Known additional storage if we add the main missing high-value families

- UniProt secondary products listed above plus AlphaFold latest additional current-release files:
  - `823,210,570,994` bytes
  - `766.67 GiB`
  - `823.21 GB`

### Known additional storage if we also add the optional QfO reference-proteomes package

- `846,342,641,634` bytes
- `788.22 GiB`
- `846.34 GB`

### Projected future raw total if we add the main known-missing families

- Current mirrored baseline + known additional families:
  - `2,458,067,527,739` bytes
  - `2,289.25 GiB`
  - `2.46 TB`

### Projected future raw total if we also add optional QfO

- `2,481,199,598,379` bytes
- `2,310.80 GiB`
- `2.48 TB`

## Recommended download priority

### Priority 1

- UniProt embeddings
- UniProt variants
- UniProt proteomics mapping
- UniProt genome annotation tracks

Reason: high information density, low storage cost, immediate usefulness to feature engineering and support layers.

### Priority 2

- AlphaFold latest additional proteome tarballs
- UniProt pan proteomes

Reason: meaningful coverage gain with moderate storage cost.

### Priority 3

- UniProt reference proteomes bulk
- UniProt taxonomic divisions

Reason: very valuable, but these are the big storage movers and should probably wait for the new external drive and a deliberate storage layout.

### Optional Priority 4

- QfO reference proteomes

Reason: orthology-friendly convenience layer, but redundant with some broader reference-proteome goals.

## Suggested decision rule

- If we want the best near-term lift per GB, add Priority 1 first.
- If we want the best structural expansion next, add AlphaFold Priority 2 next.
- If we want the long-term repository-grade mirror, reserve the external drive for Priority 3 and stage it after the storage migration plan is finalized.
