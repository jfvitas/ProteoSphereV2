# BindingDB Source Analysis Report

Source:
BindingDB is a public, web-accessible knowledgebase of measured protein-ligand binding affinities focused on small, drug-like molecules and candidate drug targets. The current download page reports about 3.2M measurements, 1.4M compounds, and 11.4K targets, with a curated subset of about 1.6M measurements, 756K compounds, and 4.8K targets. BindingDB also provides a long-term UC San Diego archive for versioned dataset references.  
Primary sources: [BindingDB downloads](https://www.bindingdb.org/rwd/bind/chemsearch/marvin/Download.jsp?ac9Lxm0azk=7fyZSysHNn4XK4G), [BindingDB TSV format](https://bindingdb.org/rwd/bind/chemsearch/marvin/BindingDB-TSV-Format.pdf), [BindingDB web services](https://www.bindingdb.org/rwd/bind/BindingDBRESTfulAPI.jsp), [BindingDB info](https://www.bindingdb.org/rwd/bind/info.jsp), [BindingDB caveat on target sequences](https://www.bindingdb.org/rwd/bind/caveat_sequences.jsp)

Acquisition:
Preferred acquisition path is the official TSV download family because each row is one binding measurement and the site now updates prepared downloads usually monthly. For reproducible training and release snapshots, use the quarterly UC San Diego archive instead of the live website. BindingDB also exposes REST services for protein-centric and compound-centric retrieval, which are useful for targeted incremental pulls or validation of a candidate set. The full database dump is also available in Oracle/MySQL form, but TSV is the best fit for this platform's planning and materialization flow.

Relevant fields:
- Ligand identifiers and structure: `BindingDB Reactant_set_id`, `BindingDB MonomerID`, `Ligand SMILES`, `Ligand InChI`, `Ligand InChI key`, ligand name.
- Target identifiers and biology: `Target Name`, source organism, protein chain sequences, target chain count, UniProt primary/secondary/alternative IDs, PDB IDs, PDB HET IDs.
- Measurement fields: `Ki`, `IC50`, `Kd`, `EC50`, `kon`, `koff`, `pH`, `Temp`, and affinity cutoff-friendly directionality in the reported source format.
- Provenance fields: curation/data source, article DOI, BindingDB entry DOI, PMID, PubChem AID, patent number, authors, publication date, curation date, institution.
- Cross-database links: PubChem CID/SID, ChEBI, ChEMBL, DrugBank, IUPHAR_GRAC, KEGG, ZINC, PDB complex links, ligand/target/pair deep links.

Use in platform:
BindingDB is a strong core source for protein-ligand supervision, especially for QSAR, affinity regression, ranking, and retrieval-augmented candidate generation. It is also useful as a canonical bridge between structures, assays, literature, patents, and protein identifiers. Because rows are already measurement-level records with explicit provenance, BindingDB can anchor the canonical interaction layer and provide training examples without needing the entire source universe in memory. It is especially valuable for proteins with reliable UniProt mapping and for target-centric workflows that need ligand, assay, and provenance context together.

Compatibility:
- Proteins: strong. BindingDB is protein-target centric and includes UniProt mappings, chain sequences, and PDB links.
- Ligands: strong. Ligands are first-class and have canonical chemical identifiers and structures.
- PPIs: limited. The resource is not primarily a protein-protein interaction database.
- PNAs / nucleic-acid targets: weak to limited. The canonical focus is protein-ligand, though special cases may exist in the broader archive.
- Structural workflows: strong where PDB links or chain sequences are present.

Join keys:
- Best protein join key: UniProt primary ID, with explicit 100% sequence-identity matching for Swiss-Prot chain mappings and source-organism awareness.
- Best ligand join key: BindingDB MonomerID plus InChIKey/SMILES for chemical deduplication.
- Best measurement join key: BindingDB Reactant_set_id for the interaction record.
- Best source joins: PMID, DOI, patent number, PubChem AID, and BindingDB entry DOI.
- Best structure joins: PDB ID(s) for ligand-target complex and ligand HET ID.
- Best assay joins: Entry ID + Assay ID via `BDB_rsid_eaids.txt`, which the download page says links Reactant Set IDs to assay text descriptions.

Storage recommendation:
- Preload: lightweight planning index with row-level metadata, identifiers, source provenance, and normalized target/ligand keys.
- Indexed: canonical interaction objects, UniProt mappings, PMID/DOI/patent links, assay IDs, and all chem identifiers.
- Lazily downloaded: bulk SDF/3D files, full monthly TSV snapshots, and any large archive slices not needed for selected training examples.
- Canonical layer: store one normalized interaction per measurement with explicit provenance, plus separate ligand, target, assay, and source entities.
- Immutable releases: preserve quarterly archive snapshots for training-set packaging and auditability.

Lazy materialization advice:
Use BindingDB's row-level TSV as the planning surface and only materialize the full detailed source records for chosen examples. For candidate generation, keep target-level summaries and identifier pointers in the planning index, then hydrate the exact TSV row, assay text, publication metadata, and related structures only after a dataset slice is selected. This is a good fit because the site already separates bulky assay text from the main TSV and provides mapping files for assay text and identifier normalization. For reproducible training packages, pin to a quarterly archive snapshot and store a manifest of the exact row IDs and source file versions used.

Quality and caveats:
- Sequence mapping is not perfect. BindingDB explicitly warns that stored target sequences may differ from the experimental sequence used in the study, including truncations and substitutions.
- UniProt mappings are strict but not universal. BindingDB's TSV documentation says Swiss-Prot chain matches require 100% sequence identity and a matching source organism, but full-length alignment is not required.
- Many cells may be blank when information is unavailable, so null handling must be explicit and preserved.
- Affinity values can include censored forms such as `>X`, so the numeric layer must keep both value and inequality direction.
- Multichain targets expand the row width because per-chain metadata repeats, so the parser must support variable-length trailing columns.
- The live website updates roughly monthly, while archived releases are quarterly, so release policy must distinguish freshness from reproducibility.
