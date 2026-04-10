# Catalog Summary

This is the curated **broad-scope source catalog** represented in `sources_manifest.json`.

## Included sources

### 1. Reactome
Coverage:
- pathways
- reactions
- complexes
- identifier mappings
- interaction exports
- graph database dump
- MySQL dump

Representative top-level files:
- `UniProt2Reactome.txt`
- `UniProt2Reactome_All_Levels.txt`
- `UniProt2ReactomeReactions.txt`
- `ChEBI2Reactome.txt`
- `ChEBI2Reactome_All_Levels.txt`
- `ChEBI2ReactomeReactions.txt`
- `NCBI2Reactome.txt`
- `NCBI2Reactome_All_Levels.txt`
- `NCBI2ReactomeReactions.txt`
- `Ensembl2Reactome.txt`
- `Ensembl2Reactome_All_Levels.txt`
- `Ensembl2ReactomeReactions.txt`
- `miRBase2Reactome.txt`
- `miRBase2Reactome_All_Levels.txt`
- `miRBase2ReactomeReactions.txt`
- `GtoP2Reactome.txt`
- `GtoP2Reactome_All_Levels.txt`
- `GtoP2ReactomeReactions.txt`
- `ReactomePathways.txt`
- `ReactomePathwaysRelation.txt`
- `Complexes2Pathways_human.txt`
- `ProteinRoleReaction.txt`
- `reactionPMIDS.txt`
- `reactome_stable_ids.txt`
- `humanComplexes.txt`
- `reactome.graphdb.tgz`
- `reactome.graphdb.dump.tgz`
- `reactome.sql.gz`
- `gk_stable_ids.sql.gz`
- `reactome.homo_sapiens.interactions.psi-mitab.txt`
- `reactome_all.interactions.psi-mitab.txt`
- `reactome.homo_sapiens.interactions.tab-delimited.txt`
- `reactome_all.interactions.tab-delimited.txt`

### 2. STRING v12
Coverage:
- functional networks
- physical networks
- embeddings
- aliases
- homology
- orthology
- species and schema files

### 3. SIFTS
Coverage:
- PDB ↔ UniProt
- taxonomy
- PubMed
- enzyme
- GO
- InterPro
- Pfam
- CATH / SCOP / SCOP2
- Ensembl
- HMMER
- observed UniProt segments

### 4. UniProt / UniRef / ID Mapping
Coverage:
- Swiss-Prot
- TrEMBL
- XML / DAT / FASTA
- isoform FASTA
- giant ID mapping tables
- UniRef100 / UniRef90 / UniRef50

### 5. AlphaFold DB
Coverage:
- bulk predicted structure archives
- Swiss-Prot CIF and PDB bundles

### 6. BioGRID
Coverage:
- all-species MITAB
- organism MITAB
- PSI XML and PSI 2.5 packages

### 7. IntAct
Coverage:
- MITAB
- PSI-MI XML
- mutation export

### 8. Complex Portal
Coverage:
- curated and predicted complexes
- PSI-MI XML 2.5 / 3.0
- ComplexTab TSV by species
- JSON exports through webservice

### 9. BindingDB
Coverage:
- full TSV
- 2D and 3D SDF
- source-subset exports
- purchasable compounds by target
- MySQL archive

### 10. ChEMBL
Coverage:
- database dumps
- SDF
- FASTA
- release notes
- RDF
- UniChem / SureChEMBL ecosystem entry points

### 11. ChEBI
Coverage:
- ontology in OWL / OBO / JSON
- full / core / lite variants

### 12. RNAcentral
Coverage:
- release archive entry point
- public Postgres database access
- genome-coordinate BED files
- ncRNA reference backbone

### 13. InterPro
Coverage:
- entries
- GO mappings
- UniProt hit mappings
- XML
- InterProScan-related bulk resources

### 14. PROSITE
Coverage:
- motif / profile database
- documentation
- auxiliary file

### 15. wwPDB Chemical Component Dictionary
Coverage:
- ligand dictionary
- amino-acid variants
- chemical component model data

## Not fully enumerated here

These are important but are better treated as separate ingestion projects because the public data is enormous, highly nested, or release-specific:
- full wwPDB archive mirror
- full EMDB / EMICSS mirror
- all AlphaFold per-proteome tarballs
- all per-entry SIFTS XML files
- per-species Complex Portal TSV / XML trees
- every release-specific ChEMBL binary bundle
- every RNAcentral archive object
