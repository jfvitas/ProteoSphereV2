# P32 Summary Fusion Code Wave

This is the implementation-ready wave that turns the summary fusion plan into concrete module work.

## What We Should Build Next

The fastest path is to build the summary library in five dependency-ordered waves:

1. Lock the accession and provenance spine.
2. Fuse structure crosswalks without merging predicted truth into experimental truth.
3. Fuse ligand identity before assay measurements.
4. Fuse curated PPI and Reactome context.
5. Add span-aware motif context and finalize the library assembler.

## Wave 1: Accessions And Provenance

Extend `core/canonical/protein.py`, `core/canonical/registry.py`, `execution/ingest/sequences.py`, `execution/indexing/protein_index.py`, `core/library/summary_record.py`, and `execution/library/build_summary_library.py`.

This wave makes UniProt the only protein spine and makes provenance pointers mandatory on materialized protein records. It also keeps secondary accessions, aliases, and unresolved candidates visible instead of flattening them away.

## Wave 2: Structure Crosswalks

Extend `execution/acquire/rcsb_pdbe_snapshot.py`, `execution/ingest/structures.py`, `execution/materialization/structure_packet_enricher.py`, `execution/assets/structure_cache.py`, and `execution/library/build_summary_library.py`. Create `execution/acquire/afdb_snapshot.py` as the predicted-structure companion lane if the next code wave needs a dedicated module for AlphaFold intake.

This wave should materialize RCSB/PDBe experimental structures with explicit entity, chain, assembly, and span lineage, while keeping AlphaFold separate as predicted support.

## Wave 3: Ligand Identity And Assays

Extend `core/canonical/ligand.py`, `core/canonical/assay.py`, `execution/acquire/bindingdb_snapshot.py`, `execution/ingest/assays.py`, `execution/materialization/ligand_packet_enricher.py`, `execution/materialization/local_bridge_ligand_backfill.py`, `execution/acquire/local_ligand_source_map.py`, `execution/acquire/local_pair_ligand_bridge.py`, and `execution/acquire/local_ligand_gap_probe.py`. Create `execution/acquire/chembl_snapshot.py` and `execution/acquire/chebi_snapshot.py` if the current intake path needs dedicated snapshot modules.

The key rule here is that ligand identity must resolve before any assay value is fused. ChEBI stays the identity authority; BindingDB and ChEMBL stay assay-backed.

## Wave 4: Curated PPI And Pathway Context

Extend `execution/acquire/intact_snapshot.py`, `execution/acquire/biogrid_snapshot.py`, `execution/acquire/intact_cohort_slice.py`, `execution/acquire/biogrid_cohort_slice.py`, `execution/indexing/interaction_index.py`, `execution/indexing/protein_pair_crossref.py`, `execution/library/intact_local_summary.py`, `execution/library/weak_ppi_candidate_summary.py`, `execution/materialization/local_bridge_ppi_backfill.py`, `execution/acquire/reactome_snapshot.py`, and `execution/library/reactome_local_summary.py`. Create `execution/acquire/string_snapshot.py` if the breadth lane is going to be added as a gated projection source.

This wave preserves native interaction IDs, participant accessions, physical-vs-genetic class, and complex lineage. Reactome is attached as pathway context, not as interaction authority.

## Wave 5: Motif Context And Final Assembly

Extend `execution/acquire/interpro_motif_snapshot.py`, `execution/library/family_motif_consensus.py`, `execution/library/build_summary_library.py`, `core/library/summary_record.py`, and `execution/acquire/supplemental_scrape_registry.py`. Create `execution/acquire/prosite_snapshot.py`, `execution/acquire/elm_snapshot.py`, `execution/acquire/sabio_rk_snapshot.py`, and `execution/acquire/uniprot_trembl_snapshot.py` as the next gated intake modules for the missing lanes.

This wave keeps motif annotations accessioned and span-aware. It also keeps the summary builder fail-closed so unresolved motif or metadata gaps remain visible rather than being coerced into fake consensus.

## Multi-Valued Fields To Preserve

These fields should stay multi-valued in the fused library:

- Protein aliases, gene names, cross references, motif references, domain references, pathway references, provenance pointers, and notes.
- Protein-ligand interaction references, assay references, provenance pointers, and notes.
- Protein-protein interaction references, evidence references, provenance pointers, and notes.

Scalar fields should only become scalar after normalization proves they are truly equivalent, such as accession, stable chemical identifier, native interaction ID, stable Reactome ID, residue span coordinates, or a normalized measurement value.

## Gating Rules

Some source families should stay gated until they are really available in the local registry or procurement queue:

- STRING
- PROSITE
- ELM
- SABIO-RK
- UniProt TrEMBL
- mega_motif_base
- motivated_proteins

Support lanes like AlphaFold DB, BioLiP, PDBBind, and local extracted assets can remain projection-only while the primary sources stay authoritative.

## Why This Wave Order Works

The order matters because every later lane depends on the accession spine.

1. Without the protein spine, structure and ligand joins become ambiguous.
2. Without the structure crosswalk, experimental and predicted structure risk being merged.
3. Without ligand identity, assay values cannot be normalized safely.
4. Without curated PPI, interaction evidence gets downgraded into context.
5. Without span-aware motif handling, functional annotations lose their meaning.

## Grounded In Current Folders

This wave is grounded in the current repository layout:

- `core/canonical`
- `core/library`
- `execution/acquire`
- `execution/ingest`
- `execution/indexing`
- `execution/library`
- `execution/materialization`
- `execution/assets`

It also aligns with the current unit test surface under `tests/unit/core` and `tests/unit/execution`.

