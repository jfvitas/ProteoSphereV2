# Source Analysis Report

Source:
UniProt

Acquisition:
UniProt should be treated as a protein-centric source with three practical ingestion paths. For bulk and repeatable refreshes, use UniProtKB downloads and proteome/track-hub artifacts as the raw cache layer. For relationship-heavy joins and selective extraction, use the [UniProt SPARQL endpoint](https://sparql.uniprot.org/), which currently advertises the full UniProt data graph and release-stamped content. For identifier translation, use the [UniProt ID Mapping Service](https://idmapping.uniprot.org/cgi-bin/idmapping_http_client3). In practice, the platform should ingest UniProtKB protein records, proteome metadata, and selected annotation tracks first, then lazily fetch broader record detail only when a candidate example is promoted.

Relevant fields:
- Primary accession and secondary accessions
- Reviewed flag and record status
- UniProt mnemonic
- Recommended, submitted, and alternative protein names
- Gene and ORF names
- Organism and NCBI taxonomy
- Canonical amino acid sequence, isoforms, sequence length, and sequence version
- Feature spans such as binding site, active site, domain, region, signal peptide, transmembrane region, and modified residue
- Protein existence evidence
- Catalytic activity, enzyme class, cofactors, pathways, and disease annotations
- Interaction annotations and external cross-references
- Proteome membership, reference proteome status, and replacement history

Use in platform:
UniProt is the identity backbone for protein-centered examples. It is the best source here for canonical protein sequence, curated functional annotation, organism context, and stable accession-based joins into the rest of the biomolecular stack. It should populate the canonical protein record, drive sequence-level indexing, and provide high-quality weak labels for function, localization, domains, catalytic roles, and interaction context. It is also a strong source for filtering by reviewed status, organism, and proteome membership before any heavier materialization.

Compatibility:
- Proteins: direct and high-confidence; this is UniProt's primary fit.
- Ligands: indirect but useful through binding-site, cofactor, catalytic activity, and chemical-group annotations.
- PPIs: strong enough for integration because UniProt carries interaction annotations and external cross-references to interaction resources.
- PNAs or nucleic-acid-adjacent examples: limited; UniProt is not a primary nucleic-acid source, so use it only for protein-mediated interaction context, not as the authoritative source for nucleic-acid chemistry.

Join keys:
- Primary UniProt accession should be the canonical join key.
- Secondary accessions should be preserved for alias resolution and historical continuity.
- Isoform identifiers should be kept separate from the base protein accession.
- NCBI taxonomy ID should be used for organism-level partitioning.
- External cross-reference IDs should be indexed for joins to PDB, AlphaFold DB, Ensembl, RefSeq, GeneID, InterPro, Reactome, BioGRID, and IntAct where present.
- Sequence hash or MD5 is useful for deduplicating exact amino-acid content across versions and sources.

Storage recommendation:
- Raw source cache: store UniProtKB export snapshots, proteome files, and any selected annotation track artifacts in append-only form with release stamps.
- Planning index: keep a compact accession-first index with reviewed status, organism, sequence length, mnemonic, primary gene names, proteome membership, and cross-reference namespaces.
- Canonical object store: normalize protein, isoform, sequence, feature, interaction, pathway, and replacement relations into lineage-linked records keyed by accession.
- Feature and embedding cache: materialize sequence-derived features and learned embeddings only for selected examples.
- Training package store: write immutable packages only after a candidate set is finalized so example-level materialization does not require re-downloading the whole source universe.

Lazy materialization advice:
Materialize the full UniProt record only when a candidate enters an active analysis or training set. Keep the long tail of comments, citation lists, evidence text, complete cross-reference payloads, and rarely used isoforms out of the hot path. Pull those details on demand from the raw cache or remote service, and materialize only the accession subset that survives planning, curation, and split assignment.

Quality and caveats:
UniProt is curated, but not uniform. Reviewed entries are high quality, while unreviewed entries are broader and noisier. Gene names are not safe unique keys. Secondary accessions and replacement history must be preserved because records can be merged or superseded. Isoforms and potential-sequence relations can create many-to-many ambiguity, so do not flatten them into a single protein row. Functional annotations are evidence-dependent and coverage varies strongly by organism, family, and review status. Cross-reference completeness is uneven, so joins should be namespace-aware and failure-tolerant rather than assumed.

Sources used:
- [UniProt SPARQL endpoint](https://sparql.uniprot.org/)
- [UniProt RDF schema ontology](https://purl.uniprot.org/core/)
- [UniProt ID Mapping Service](https://idmapping.uniprot.org/cgi-bin/idmapping_http_client3)
