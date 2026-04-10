# Protein Data Scope Seed Validation

- Status: `passed`
- Manifest: `data/raw/protein_data_scope_seed`
- Policy: `protein_data_scope/tier1_validation_policy.json`
- Passed: `6`
- Failed: `0`
- Not run: `0`

## chebi

- Status: `passed`
- Failures: none
- Required core files:
  - `chebi.owl`
  - `chebi.obo`
  - `chebi.json`

## pdb_chemical_component_dictionary

- Status: `passed`
- Failures: none
- Required core files:
  - `components.cif.gz`
  - `aa-variants-v1.cif.gz`
  - `chem_comp_model.cif.gz`

## prosite

- Status: `passed`
- Failures: none
- Required core files:
  - `prosite.dat`
  - `prosite.doc`
  - `prosite.aux`

## reactome

- Status: `passed`
- Failures: none
- Required core files:
  - `UniProt2Reactome.txt`
  - `ReactomePathways.txt`
  - `ReactomePathwaysRelation.txt`

## sifts

- Status: `passed`
- Failures: none
- Required core files:
  - `pdb_chain_uniprot.tsv.gz`
  - `pdb_chain_go.tsv.gz`
  - `pdb_chain_pfam.tsv.gz`
  - `uniprot_pdb.tsv.gz`

## uniprot

- Status: `passed`
- Failures: none
- Required core files:
  - `uniprot_sprot.dat.gz`
  - `uniprot_sprot.fasta.gz`
  - `idmapping.dat.gz`

