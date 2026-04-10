# Source Analysis Report

Source:
RCSB PDB + PDBe. Primary structural archive coverage comes from the PDBx/mmCIF data model, with RCSB adding JSON/GraphQL/Data API access and PDBe adding REST/FTP access plus SIFTS-derived mappings.

Acquisition:
Use RCSB Data API/GraphQL for entry, entity, assembly, and chemical-component metadata; use RCSB archive downloads for mmCIF coordinate files and validation artifacts. Use PDBe REST API and FTP for residue-level and chain-level cross-reference files, especially SIFTS outputs such as `pdb_chain_uniprot`, `uniprot_segments_observed`, taxonomy, InterPro, Pfam, GO, EC, and PubMed summaries.

Relevant fields:
Core fields are PDB entry ID, title, experimental method, resolution, release date, polymer entity count, assembly count, polymer/nonpolymer/branched entity IDs, chain identifiers, biological assembly definitions, ligand/chemical component IDs, sequence coverage, observed residues, taxonomic annotations, UniProt accessions, and validation/quality signals. On the RCSB side, the most useful object-level fields include `entry.entry.id`, `entry.struct.title`, `entry.rcsb_entry_info.experimental_method`, `entry.rcsb_entry_info.resolution_combined`, `entry.rcsb_entry_info.assembly_count`, and the entity container identifier objects for entry/entity/assembly linkage. For downstream modeling, the highest-value fields are entity type, sequence, entity length, chain mapping, interface/assembly context, ligand identity, and missing-residue spans.

Use in platform:
This source is the structural backbone for protein and protein-complex examples, ligand-bound complexes, interface/PPI supervision, structure quality filtering, residue-level label projection, and structure-to-sequence alignment. It should drive canonical structure records, example selection, and later training-package materialization for selected entries rather than powering a full raw-data mirror in memory.

Compatibility:
Protein compatibility is high. Ligand compatibility is high through small-molecule and cofactors annotations. PPI compatibility is high because assemblies, interfaces, and chain-level structure are explicit. Nucleic-acid compatibility is moderate to high for protein-nucleic-acid complexes. PNA compatibility is low or indirect; the archive can contain unusual polymers, but PNA is not a native first-class target and should be handled as an edge case if encountered.

Join keys:
Primary join keys are `pdb_id`, `entry_id`, `entity_id`, `assembly_id`, `auth_asym_id`, `label_asym_id`, residue sequence numbers, UniProt accession, CCD/ligand component ID, and SIFTS mapping spans. Use `pdb_id + chain_id` for chain tables, `pdb_id + entity_id` for entity tables, and `pdb_id + uniprot_accession + residue range` for sequence-level joins to external annotations.

Storage recommendation:
Preload compact metadata and mapping summaries into the planning index: entry headers, entity summaries, assembly summaries, chain-to-UniProt mappings, taxonomy, and quality flags. Keep raw mmCIF, validation, and SIFTS XML/flatfiles in the raw source cache. Materialize canonical objects for entries, entities, chains, ligands, assemblies, and mappings with lineage metadata. Keep coordinate-heavy and validation-heavy assets lazy until a training set or analysis slice explicitly selects them.

Quality and caveats:
Treat biological assembly vs asymmetric unit as a deliberate modeling choice, not an interchangeable detail. Expect unresolved residues, alternate locations, chain renumbering, obsolete entries, incomplete coverage, and mapping ambiguity between author and label identifiers. Ligands may be partial, covalent, or solvent-like, and not all annotations are equally reliable across entries. Structures are biased toward experimentally solved, stable, and publishable systems, so this source should be combined with sequence and functional sources rather than used alone for coverage-sensitive modeling.
