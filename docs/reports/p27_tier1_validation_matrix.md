# P27 Tier 1 Validation Matrix

## Goal

Define the minimum fail-closed validation rules for the first production-safe procurement tranche.

## Tier 1 sources

- `reactome`
- `sifts`
- `uniprot`
- `chebi`
- `prosite`
- `pdb_chemical_component_dictionary`

## Validation rules

### Reactome

- Required core files:
  - `UniProt2Reactome.txt`
  - `ReactomePathways.txt`
  - `ReactomePathwaysRelation.txt`
  - `reactome.homo_sapiens.interactions.psi-mitab.txt`
- Minimum checks:
  - file exists and is non-empty
  - all required core files arrived
  - representative tabular sample is readable
  - release manifest written
- Fail closed if:
  - any required core file is missing
  - any required core file is zero bytes
  - representative tabular read fails

### SIFTS

- Required core files:
  - `pdb_chain_uniprot.tsv.gz`
  - `pdb_chain_go.tsv.gz`
  - `pdb_chain_pfam.tsv.gz`
  - `uniprot_pdb.tsv.gz`
- Minimum checks:
  - file exists and is non-empty
  - gzip integrity check passes
  - representative tabular sample is readable
  - release manifest written
- Fail closed if:
  - any required core file is missing
  - gzip validation fails
  - representative tabular read fails

### UniProt

- Required core files:
  - `uniprot_sprot.dat.gz`
  - `uniprot_sprot.fasta.gz`
  - `idmapping.dat.gz`
- Minimum checks:
  - file exists and is non-empty
  - gzip integrity check passes
  - representative FASTA or DAT sample is readable
  - release manifest written
- Fail closed if:
  - any required core file is missing
  - gzip validation fails
  - representative sequence sample read fails

### ChEBI

- Required core files:
  - `chebi.owl`
  - `chebi.obo`
  - `chebi.json`
- Minimum checks:
  - file exists and is non-empty
  - JSON variant parses
  - ontology text sample is readable
  - release manifest written
- Fail closed if:
  - any required core file is missing
  - JSON parse fails
  - ontology sample read fails

### PROSITE

- Required core files:
  - `prosite.dat`
  - `prosite.doc`
  - `prosite.aux`
- Minimum checks:
  - file exists and is non-empty
  - all required core files arrived
  - representative text sample is readable
  - release manifest written
- Fail closed if:
  - any required core file is missing
  - any required core file is zero bytes
  - representative text sample read fails

### wwPDB Chemical Component Dictionary

- Required core files:
  - `components.cif.gz`
  - `aa-variants-v1.cif.gz`
  - `chem_comp_model.cif.gz`
- Minimum checks:
  - file exists and is non-empty
  - gzip integrity check passes
  - representative mmCIF sample is readable
  - release manifest written
- Fail closed if:
  - any required core file is missing
  - gzip validation fails
  - representative mmCIF sample read fails

## Current note

The uploaded manifest originally pointed `chem_comp_model.cif.gz` at the wrong wwPDB path under `monomers`. The official wwPDB CCD page points it to `component-models/complete/chem_comp_model.cif.gz`, and the manifest has been corrected accordingly.
