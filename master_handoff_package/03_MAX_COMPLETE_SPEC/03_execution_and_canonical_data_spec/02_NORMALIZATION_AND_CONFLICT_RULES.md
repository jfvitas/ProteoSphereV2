# Normalization, Join, and Conflict Resolution Rules

## 1. ID priority
Proteins:
1. UniProt accession (preferred primary)
2. curated alternative primary ID if UniProt absent
3. source-specific provisional protein ID

Chains:
- structure_id + chain label + entity/model context

Ligands:
- InChIKey preferred canonical chemistry identity when available
- otherwise canonical SMILES + source chemical ID

Nucleic acids:
- source structure chain plus type and normalized sequence when available

## 2. Mapping rules
### PDB chain to protein
- align extracted chain sequence to candidate canonical sequences
- allow configurable identity thresholds
- preserve mutation/insertion/deletion differences
- if alignment ambiguous, create unresolved mapping state rather than forcing assignment

### Assay target to protein
- normalize target names/IDs through UniProt or curated target registry
- if assay target is family-level or complex-level rather than single protein, represent that explicitly

### Ligand standardization
- canonicalize tautomers/protonation only through a controlled chemistry pipeline
- preserve raw source representation plus standardized representation
- never discard raw ligand string

## 3. Conflict classes
- sequence conflict
- identity conflict
- structure quality conflict
- assay value conflict
- annotation conflict
- biological relevance conflict

## 4. Conflict handling
### Sequence conflicts
- prefer canonical sequence source for identity backbone
- preserve observed chain sequence as source-specific observation
- emit mutation_summary and sequence_alignment record

### Structure quality conflicts
- do not collapse multiple structures into one without versioned derived policy
- allow multiple ChainRecord/ComplexRecord variants per ProteinRecord
- preferred structure selection should be a query-time policy, not destructive overwrite

### Assay conflicts
- do not average across incompatible measurement types
- standardize units first
- keep individual measurements
- create derived aggregate only if aggregation policy is explicitly selected:
  - mean
  - median
  - confidence-weighted mean
  - best-quality measurement
  - source-priority measurement

### Annotation conflicts
- preserve all annotations
- rank by confidence/source priority at query time

## 5. Missing data handling
Allowed strategies:
- mask
- explicit unknown token
- optional imputation
- source fallback retrieval
Forbidden strategy:
- treating missing as zero without explicit semantic justification

## 6. Source priority examples
Sequence identity backbone:
- UniProt > curated sequence DB > source-local sequence
Structure quality preference:
- higher resolution experimental > lower resolution experimental > predicted structure
Disorder truth:
- curated disorder source > inferred from low confidence prediction
