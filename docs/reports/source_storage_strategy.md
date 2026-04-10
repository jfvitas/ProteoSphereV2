# Source Storage Strategy

This report turns the completed compatibility matrix, release matrix, joinability analysis, and supplemental scrape registry into an implementation-grade storage policy. The core rule is simple: **pin the release boundary first, preload only the selection surface, keep canonical stores lineage-safe, and defer heavy or portal-only payloads until a candidate is actually selected**.

## Storage Tiers

- **Pinned manifest**: immutable snapshot metadata, source URL or endpoint, release identifier or archive date, retrieval timestamp, checksum list, file list, query parameters, parser/extractor version, and any explicit scope or allowlist marker.
- **Planning index**: compact, accession-first routing data used to decide what to join, select, or materialize next. This is the hot path for search and candidate generation.
- **Canonical store**: normalized, lineage-preserving entity graphs keyed by source-native identifiers and canonical cross-resource identifiers. This is where the platform records the durable object model.
- **Feature cache**: rebuildable derived summaries used by ranking, filtering, masking, and packet assembly. These are denormalized on purpose, but must remain reproducible from the manifest and canonical store.
- **Deferred fetch/materialization**: bulky, slow, or selection-specific payloads such as coordinates, maps, full evidence tables, long text, alignments, and diagrams.
- **Scrape-only enrichment**: accession-scoped portal or HTML payloads that are only allowed through the supplemental scrape registry. These are never treated as primary source identity.

## Policy By Source Class

| Source class | Pinned manifest | Planning index | Canonical store | Feature cache | Deferred fetch/materialization | Scrape-only enrichment |
| --- | --- | --- | --- | --- | --- | --- |
| UniProt | Release-stamped UniProtKB exports, proteome files, ID mapping service snapshot, and retrieval timestamp. | Accession, reviewed status, organism, sequence length, mnemonic, proteome membership, cross-ref namespaces, sequence version/hash. | Canonical protein record plus isoforms, aliases, secondary accessions, and provenance lineage. | Compact protein summary rows, weak labels, cross-ref summaries, and sequence-derived display features. | Long comments, evidence text, rare isoforms, and any accession-specific annotation payload not needed for routing. | None. |
| RCSB / PDBe | mmCIF archive date, PDBe REST/FTP surface, SIFTS flatfiles, and exact file set used. | PDB ID, entity ID, assembly ID, chain ID, residue span, quality flags, and SIFTS mapping spans. | Entry, entity, assembly, chain, ligand, and mapping records kept separate from predicted structures. | Entry headers, chain-to-UniProt summaries, interface summaries, and quality bins. | Raw mmCIF, validation reports, coordinate-heavy downloads, map-heavy payloads, and full SIFTS payloads. | None. |
| AlphaFold DB | Accessions, model IDs, sequence checksum, release date, and per-entry asset inventory (`bcif`, `cif`, `pdb`, `MSA`, `pLDDT`, `PAE`). | UniProt accession, modelEntityId, sequenceChecksum, version, sequence bounds, provider ID, confidence summary. | Predicted-model records only, kept separate from experimental coordinates. | Confidence summaries, coverage bins, and lightweight structure-proxy features. | Coordinate files, PAE/MSA assets, annotation payloads, and any full per-entry download bundle. | None. |
| BindingDB | Quarterly archive snapshot plus any monthly refresh used for validation or incrementals. | Reactant_set_id, MonomerID, target accession, assay ID, publication provenance, censored value flags, and row IDs. | Interaction and assay records with strict target, ligand, and provenance separation. | Target-level summaries, affinity bins, assay modality summaries, and selected row fingerprints. | Full TSV rows, detailed assay text, archive slices, and selected publication detail pages. | None. |
| BioGRID | Versioned TAB3/MITAB family snapshot with release stamp and exact row set used. | BioGRID Interaction ID, BioGRID IDs, Entrez, UniProt, PMID, taxon, source interaction IDs, physical/genetic flag. | Interaction evidence objects that preserve the physical-vs-genetic distinction. | Neighborhood summaries, evidence counts, publication counts, and organism-scoped interaction views. | Full TAB3/MITAB rows and publication context. | None. |
| IntAct | Release 247 plus PSI-MI XML, PSI-MITAB 2.5/2.6/2.7, XGMML, RDF, and BioPAX export family. | Interaction AC, IMEx ID, participant IDs, UniProt/RefSeq, organism, confidence, feature spans, binary-vs-native-complex flag. | Interaction evidence and complex projections with explicit lineage from native complexes. | Binary/native-complex summaries, confidence bins, and feature-span summaries. | Full PSI-MI XML, full MITAB, federation payloads, and expanded complex detail. | None. |
| Reactome | Reactome v95 plus quarterly Zenodo snapshots, stable-ID manifest, and version suffixes. | Stable ID, species, reaction type, pathway ancestry, compartment, catalyst/regulator links, PMID links, complex membership. | Pathway, reaction, complex, and participant mapping records with version and species preserved. | Hierarchy summaries, ancestry paths, role summaries, and pathway grouping features. | Full diagrams, SVG/PNG assets, BioPAX/SBML, and broad Content Service payloads. | None. |
| InterPro | InterPro 108.0 download/API bundle plus release-stamped member-database snapshots where needed. | IPR accession, member-signature accession, UniProt, taxon, residue span, representative flag, clan/set IDs, provenance. | Motif annotation and entry graph separate from the protein record. | Compact entry catalogs, motif hit summaries, protein-domain architecture features, and representative-flag caches. | Full match tables, long detail pages, and logos. | Accessions-scoped InterPro entry pages only when registered through the supplemental scrape registry. |
| PROSITE | Accessioned documentation and scan outputs pinned to the release boundary. | PDOC/PS/PRU accessions, motif span, taxonomic scope, documentation link, and pattern/profile summary. | Motif-call records with rule provenance and residue-span lineage. | Compact motif hits, pattern/profile summaries, and site-local confidence features. | Logos, full instance tables, long documentation, and scan-detail payloads. | Accessions-scoped detail pages only when registered through the supplemental scrape registry. |
| ELM | Class catalog plus any release-stamped instance snapshot. | ELME accession, instance coordinates, organism, evidence count, partner/domain hints, and source page fingerprint. | Short-linear-motif annotation records with partner-context lineage. | Motif-hit summaries, partner-context tags, and evidence-weighted display rows. | Full class pages, full instance tables, and long textual documentation. | Accessions-scoped class pages only when registered through the supplemental scrape registry. |
| RCSB motif search | Curated query catalog and saved result fingerprint for the selected motif set. | Query fingerprint, matched PDB/CSM, polymer entity, residue numbering, chain/assembly context, RMSD or match score. | Selected structure-motif match records, kept distinct from generalized motif annotation. | Curated hit caches, match summaries, and residue-local retrieval features. | Full search result payloads and any heavy result bundle. | Search-result payloads only when the query is registered and scope-limited by the supplemental scrape registry. |
| DisProt | `DisProt release_2025_12.json`, `api-version: 8.0.1`, and the controlled-vocabulary snapshot. | `acc`, `disprot_id`, `region_id`, `term_id`, `term_namespace`, `released`, `start`, `end`, `disprot_consensus`, cross-ref keys. | Disorder-region and evidence records attached to a canonical protein record, never merged into protein identity. | Disorder masks, region overlays, evidence summaries, and split-friendly label caches. | Full `statement` text, `reference_html`, curator history, `annotation_extensions`, `conditions`, `sample`, `construct_alterations`, and region history. | Accessions-scoped entry pages only when registered through the supplemental scrape registry. |
| EMDB | EMDB header XML, map files by accession plus schema version, and EMICSS refresh outputs. | EMDB accession, title, method, resolution, status, release date, sample type, organism, linked PDB/EMPIAR IDs, summary counts. | EMDB entry, sample component, validation summary, and explicit link records to PDB, EMPIAR, UniProt, AlphaFold DB, and related namespaces. | Quality overlays, map-class summaries, resolution bins, and cryo-EM fit features. | Raw CCP4/MRC map files, half-maps, masks, FSC outputs, header XML beyond the summary slice, and long validation reports. | None. |
| Evolutionary / MSA corpus | Frozen local sequence corpus, corpus snapshot ID, aligner version, and exact parameters. | UniProt accession, sequence hash/version, UniRef cluster IDs, orthogroup IDs, alignment depth, and quality flags. | Sequence-cluster and alignment-bundle records, with frozen corpus lineage. | Conservation vectors, redundancy masks, depth bins, and family-aware split features. | Full alignments, trees, HMM/profile payloads, and any species-specific homology tables not needed for the current candidate set. | None. |

## Explicit Expensive Payloads

The following payload families should never be treated as default preload material:

- Experimental structure payloads: mmCIF, validation bundles, coordinate-heavy downloads, map-heavy assets, and SIFTS flatfiles beyond the summary slice.
- Predicted structure payloads: BCIF/CIF/PDB coordinate files, PAE, MSA, and annotation bundles.
- Interaction payloads: full TAB3/MITAB rows, full PSI-MI XML, full MITAB, federated PSICQUIC/IMEx result sets, and complete assay text.
- Pathway payloads: diagrams, SVG/PNG assets, BioPAX, SBML, and broad Content Service bundles.
- Motif payloads: full match tables, logos, alignment blocks, instance tables, and long documentation pages.
- Disorder payloads: full region evidence, curator audit history, HTML reference pages, and auxiliary deposition fields.
- EMDB payloads: raw volumes, half-maps, masks, FSC outputs, and long validation reports.
- Evolutionary payloads: full alignments, trees, HMMs, and profile objects.

## Scrape-Only Policy

Portal or HTML-only enrichments are allowed only when the supplemental scrape registry approves the target, the extraction mode, and the scope. The approved enrichment set is intentionally narrow:

- InterPro accession-scoped entry pages
- PROSITE accession-scoped detail pages
- ELM class-scoped pages
- DisProt accession-scoped pages
- Reactome pathway pages
- RCSB sequence-motif and 3D-motif search result payloads

Those captures are enrichment material, not identity material. They may populate feature caches or audit trails, but they should not become the canonical record for a source class.

## Implementation Rules

1. Pin the manifest before anything else. If the source is mutable, a runtime pointer is not a release boundary.
2. Preload only the fields needed to route, filter, or select examples.
3. Put durable object identity in the canonical store, not in the planning index.
4. Keep feature caches small, derived, and rebuildable from pinned sources.
5. Defer any heavy or selection-specific asset until the candidate has passed join, split, and packaging checks.
6. Treat predicted and experimental coordinates as separate object classes.
7. Treat portal-only captures as supplemental enrichments, gated by the registry, and never as a substitute for source-native snapshots.

## Outcome

This storage split gives the platform a stable identity spine, a compact planning surface, and a safe path for heavyweight or portal-only enrichments. It also keeps the main training-packet pipeline narrow: the default path should be metadata-first, canonical-store-second, and deferred-hydration-last.
