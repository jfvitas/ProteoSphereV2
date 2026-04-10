# Source Analysis Report

Source:
EMDB is the Electron Microscopy Data Bank, a public repository for cryogenic-sample electron microscopy volumes and representative tomograms of macromolecular complexes and subcellular structures. The local source matrix correctly treats it as an advanced modality layer rather than a backbone source.

Acquisition:
Prefer the EMDB website/API for entry search and metadata, the EMDB FTP archive for authoritative header and map files, EMICSS for cross-referenced protein/complex/sequence annotations, and the EMDB validation resources for quality signals. EMICSS is especially important because it publishes one XML annotation file per EMDB entry plus TSVs per resource and is refreshed with weekly releases of new entries and monthly archive updates.

Schema surface:
The public EMDB surface is map-centric, not atom-centric. The core archive ships XML header files that validate against the EMDB data model XSD, and the archive naming convention separates header XML from primary map files. Public entry identifiers use `EMD-` accessions, while schema versions are tracked separately in the header filename. EMICSS expands the surface with entry-level links such as publication, PDB, and EMPIAR references, plus sample-level links such as UniProt accessions and AlphaFold DB models.

Relevant fields:
- EMDB accession, schema version, release status, release instruction, deposition and release dates
- title, sample type, organism, sample composition, microscopy method, sample preparation context
- resolution, map class, map availability, primary map and auxiliary map references
- linked PDB IDs, EMPIAR IDs, publication metadata
- EMICSS sample annotations: UniProt accessions, AlphaFold DB models, InterPro, GO, ChEBI, domain/complex/drug names where present
- validation metrics and fit-to-model signals from the EMDB validation analysis layer

Use in platform:
EMDB should contribute map-level context, not replace coordinate-first structure sources. Its best value is cryo-EM quality features, heterogeneity signals, map-to-model fit context, in situ complex evidence, and a modality-aware overlay for examples already anchored by UniProt, PDB, or a known complex. For the summary library, EMDB is useful as an attached evidence layer on top of canonical proteins and complexes, not as the primary identity spine.

Compatibility:
- Proteins: high for sample-linked proteins via EMICSS and PDB-linked model context, but only indirect at the map level.
- Complexes: high for macromolecular complexes and subcellular assemblies observed by cryo-EM.
- Ligands: moderate to low. Ligand context may exist in sample annotations or fitted models, but EMDB is not a canonical chemistry or affinity source.
- PPIs: moderate. The archive can support complex-state and interface evidence, but it is not direct interaction evidence in the BioGRID/IntAct sense.
- PNAs: moderate. Nucleic-acid-containing assemblies and tomograms can be represented, but join quality is more variable and often depends on linked atomic models.

Join keys:
- Primary entry key: EMDB accession.
- Structure join: PDB ID for map/model pairs and corresponding atomic structures.
- Raw-data join: EMPIAR accession where raw acquisition data is archived separately.
- Protein join: UniProt accession from EMICSS and related PDBe/wwPDB mapping layers.
- Auxiliary joins: AlphaFold DB model IDs, InterPro IDs, GO terms, ChEBI IDs, and sample composition labels from EMICSS.
- Internal component joins: use synthetic component IDs if the source does not expose a stable sample-component identifier; do not assume sample names are unique enough to act as keys.

Storage recommendation:
- Preload a compact planning index with accession, title, method, resolution, status, release date, sample type, organism, linked PDB/EMPIAR IDs, and EMICSS summary counts.
- Index EMDB accessions, schema version, status, method, resolution bins, organism, sample type, linked UniProt accessions, PDB IDs, EMPIAR IDs, validation summary fields, and map modality tags.
- Canonical layer should contain an `EMDBEntry` record, a synthetic `EMDBSampleComponent` record per mapped sample component, an `EMDBValidationSummary` record, and explicit link records to PDB, EMPIAR, UniProt, AlphaFold DB, and other namespaces.
- Keep raw CCP4/MRC map files, header XML, half-maps, masks, FSC outputs, and long validation reports in lazy storage.

Lazy materialization advice:
Hydrate EMDB only after a candidate is already selected by a coordinate-first or protein-first path. For routine summary-library use, store the accession, linked model IDs, and validation summary, then fetch the map and auxiliary files only when a cryo-EM-specific training packet or map review is actually needed. This keeps the hot path light and avoids pulling multi-megabyte density assets for entries that will never be packaged.

Quality and caveats:
EMDB is rich but not self-sufficient. A single entry is a deposited experiment with a primary map and optional auxiliary files, so it should not be flattened into a generic structure row. Released entries can become obsolete, withdrawn entries may have no public data, and the primary map is versioned through the archive process, so the code must preserve accession, status, and schema version explicitly. EMDB validation is useful, but resolution and fit metrics are method-dependent and must be interpreted in context rather than compared naively across all processing strategies. Composite maps, focused maps, alternative conformations, and tomography-derived volumes complicate canonicalization. EMICSS is automated and updated on a weekly/monthly cadence, so cross-reference freshness should be versioned rather than assumed static.

Verdict:
EMDB should be in scope for early indexing and quality overlay work, but it should be deferred behind coordinate-first sources for default training-packet packaging. The right implementation posture is "metadata now, heavy volumes later": preload and index the entry-level and sample-level metadata, then lazily fetch the density volumes and validation artifacts only for cryo-EM-oriented examples that already have a protein or complex anchor.

Sources used:
- [EMDB home](https://www.ebi.ac.uk/emdb)
- [EMDB policies](https://www.ebi.ac.uk/emdb/documentation/policies)
- [EMDB validation analysis](https://www.ebi.ac.uk/emdb/va/)
- [EMICSS](https://www.ebi.ac.uk/emdb/emicss)
- [EMDB map format](https://files.wwpdb.org/pub/emdb/doc/Map-format/current/EMDB_map_format.pdf)
- [wwPDB Charter with EMDB archive/schema conventions](https://www.ebi.ac.uk/pdbe/sites/default/files/2022-10/2021_wwPDB_Charter_with_Appendix.pdf)
