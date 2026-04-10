# P27 Fresh-Acquisition Shortlist for P09105 and Q2TAC2

Date: 2026-03-23

Scope: define the next exact external source lanes for `P09105` and `Q2TAC2`, given that local recovery is not available and AlphaFold structure context is already present.

## Grounding

- [artifacts/status/local_ligand_source_map.json](/D:/documents/ProteoSphereV2/artifacts/status/local_ligand_source_map.json)
- [p27_no_local_rescue_acquisition_priority_p09105_q2tac2.md](/D:/documents/ProteoSphereV2/docs/reports/p27_no_local_rescue_acquisition_priority_p09105_q2tac2.md)
- [source_bindingdb.md](/D:/documents/ProteoSphereV2/docs/reports/source_bindingdb.md)
- [source_rcsb_pdbe.md](/D:/documents/ProteoSphereV2/docs/reports/source_rcsb_pdbe.md)
- [source_alphafold_db.md](/D:/documents/ProteoSphereV2/docs/reports/source_alphafold_db.md)

## Current Truth State

Both accessions are currently `structure_companion_only` in the local source map:

- `P09105`
  - local ligand rescue: none
  - AlphaFold companion present: `AF-P09105-F1-model_v6`
- `Q2TAC2`
  - local ligand rescue: none
  - AlphaFold companion present: `AF-Q2TAC2-F1-model_v6`

AlphaFold is already sufficient for protein-structure context. It is not the next acquisition lane for ligand recovery.

## Recommended Acquisition Order

### 1. BindingDB

Why first:

- strongest assay-first lane for protein-ligand evidence
- explicit UniProt-centered target mapping
- measurement-level records with provenance
- best chance to recover ligand supervision without requiring an immediately available structure complex

Exact lane:

- targeted target-centric pull by accession
- prioritize measured rows with `Ki`, `Kd`, `IC50`, `EC50`, `kon`, `koff`
- retain `Reactant_set_id`, ligand identifiers, publication metadata, and any linked PDB IDs

Operational outcome:

- if either accession returns measured ligand rows, promote BindingDB to the first real ingestion lane
- if no rows return, move immediately to ChEMBL without waiting on structure search

### 2. ChEMBL

Why second:

- next best assay-centric recovery lane after BindingDB
- target/activity structure is useful even when BindingDB is sparse or absent
- still valuable for ligand-supervision recovery without requiring a solved complex

Exact lane:

- target lookup by UniProt accession
- recover linked target IDs, assays, activities, and ligand identifiers
- keep accession-to-target mapping explicit and fail closed on ambiguous target joins

Operational outcome:

- if accession-scoped target/activity support exists, use it as the assay ingestion lane
- if ChEMBL is also empty, keep the accessions in external structure-complex search only

### 3. RCSB/PDBe ligand complexes

Why third:

- highest-value structural lane, but only if an exact target-bound ligand complex exists
- more brittle than assay-first lanes because chain mapping and ligand role must be proven

Exact lane:

- query RCSB/PDBe by UniProt accession
- require chain-level UniProt mapping and ligand-bearing experimental entry
- require target-chain ligand support, not companion-chain-only ligand presence
- use PDBe/SIFTS chain mapping to keep the chain-truthfulness boundary intact

Operational outcome:

- if a real target-bound complex exists, it becomes the preferred structure-linked ligand packaging lane
- if only partner-chain or assembly-level ligand context exists, do not count it as structure rescue

### 4. AlphaFold DB

Why fourth:

- already present for both accessions
- useful for protein-only geometry/context after ligand evidence is acquired elsewhere
- not a ligand acquisition source

Exact lane:

- no new acquisition required now
- keep current AlphaFold entries as companion structure context only

Operational outcome:

- use only after BindingDB/ChEMBL/RCSB supply ligand evidence

### 5. Guarded/manual lanes worth trying next

These are worth trying only after the three primary lanes above:

- `PDBBind`
  - manual-gated archive
  - worth checking only if RCSB/PDBe yields exact target-bound complexes
  - use as a packaging/support source, not as the first discovery lane
- `BioLiP`
  - useful as discovery support for candidate ligand-bearing PDB IDs
  - not authoritative enough to treat as direct ingestion on its own
  - must still be confirmed through exact RCSB/PDBe chain-truthful structure evidence

## Accessions

The recommended order is the same for both `P09105` and `Q2TAC2`:

1. BindingDB
2. ChEMBL
3. RCSB/PDBe ligand complex search
4. reuse existing AlphaFold context only
5. guarded/manual follow-up through PDBBind and BioLiP if exact structure hits are found

## Bottom Line

For both `P09105` and `Q2TAC2`, the next useful acquisition work is assay-first and external:

- start with `BindingDB`
- then `ChEMBL`
- then exact `RCSB/PDBe` ligand-complex recovery
- do not spend more effort on local mining
- do not treat AlphaFold as ligand rescue
