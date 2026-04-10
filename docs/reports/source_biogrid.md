# Source Analysis Report

Source:
BioGRID is a curated biomedical interaction repository for protein, genetic, chemical, and PTM data. For this platform's summary library and training-packet pipeline, the relevant slice is the interaction layer: the current index is version 5.0.255 and reports 2,933,176 protein/genetic interactions from 87,975 publications, plus 31,540 chemical interactions and 1,128,339 PTMs. BioGRID updates monthly and provides standardized downloads and a REST service.  
Primary sources: [BioGRID home](https://thebiogrid.org/), [BioGRID download format details](https://wiki.thebiogrid.org/doku.php/downloads), [BioGRID TAB 3.0 format](https://wiki.thebiogrid.org/doku.php/biogrid_tab_version_3.0), [BioGRID MITAB format](https://wiki.thebiogrid.org/doku.php/psi_mitab_file), [BioGRID curation workflow](https://wiki.thebiogrid.org/doku.php/curation_description), [BioGRID REST service](https://wiki.thebiogrid.org/doku.php/biogridrest), [Supported identifiers](https://wiki.thebiogrid.org/doku.php/identifiers)

Acquisition:
Use TAB3 or MITAB downloads as the primary bulk source. TAB3 is the most useful for the platform because it carries the full BioGRID interaction row with BioGRID interaction ID, both interactor gene IDs, BioGRID IDs, symbols, synonyms, experimental system, throughput, publication source, tax IDs, source database, UniProt/RefSeq accessions, ontology terms, qualifiers, and organism names. MITAB is best when a PSI-MI binary-interaction shape is preferred. The REST service is useful for targeted fetches, but it is access-key gated and paginated at 10,000 rows per request.

Relevant fields:
- Interaction identity: BioGRID Interaction ID, BioGRID IDs for interactor A/B, and publication source/id.
- Protein and gene identity: Entrez Gene IDs, official symbols, systematic names, synonyms, UniProt accessions, and RefSeq accessions.
- Biological origin: NCBI Taxonomy IDs and organism names for both interactors.
- Evidence and quality: experimental system name, experimental system type (`physical` or `genetic`), throughput, score, tags, qualifiers, and ontology terms.
- Provenance: first author, PubMed source, source database, and any source database interaction identifier.
- Cross-reference support: BioGRID can search by BioGRID, UniProt/UniProtKB, RefSeq, Entrez, HGNC, Ensembl, and many other namespaces.

Use in platform:
BioGRID is a strong evidence layer for pairwise interaction coverage and interaction-neighborhood summaries. It is not a canonical protein authority, but it is a good source for "what interacts with this protein/gene" summaries, especially when the platform needs curated PPI evidence, physical-vs-genetic distinction, throughput context, and publication provenance. It should feed the summary library with compact interaction facts and drive training-packet candidate selection for interaction-centric tasks.

Compatibility:
- Proteins: strong as an interaction source, not as the identity backbone.
- PPIs: strong. This is BioGRID's core fit and the reason to ingest it.
- Chemicals/PTMs: present, but secondary for this task.
- Nucleic acids: limited. BioGRID can represent genetic interactions, but it is not a nucleic-acid-first source.

Join keys:
- Best canonical protein join key: UniProt accession when present, with organism-aware resolution and explicit ambiguity handling.
- Best BioGRID pair join key: BioGRID Interaction ID.
- Best interactor join keys: BioGRID ID and Entrez Gene ID, with official symbol and synonym namespaces as aliases only.
- Best provenance joins: PubMed ID, source database, and source database interaction ID.
- Best organism joins: NCBI Taxonomy ID.

Storage recommendation:
- Preload: a compact interaction index with BioGRID Interaction ID, the two BioGRID IDs, Entrez IDs, UniProt accessions, taxids, experimental system/type, throughput, source database, PubMed ID, and organism names.
- Indexed: all identifier namespaces used for cross-reference resolution, plus experimental system, physical/genetic flag, publication source, score, tags, qualifiers, and source interaction IDs.
- Lazily fetched: full TAB3/MITAB/PSI25 rows, full publication context, alternate alias lists, and any bulk per-organism or per-system archives not needed for selected examples.
- Canonical layer: store interaction evidence as a separate object from protein identity, so a single interaction can point to two canonical protein records or unresolved placeholders without collapsing ambiguity.

Lazy materialization advice:
Use BioGRID as a planning index first, not a bulk mirror. For a candidate protein, load a compact neighborhood summary and the highest-value evidence fields, then hydrate the exact interaction rows only after the example is promoted into a training packet. For a candidate pair, materialize the BioGRID interaction row, publication provenance, and organism/evidence metadata together so the final package preserves evidence context without needing the whole release in memory.

Quality and caveats:
- BioGRID curators record interactions from primary literature, not reviews or unpublished data.
- The curation model uses gene identifiers to describe interactors; splice variants, wild-type background, mutations, interaction domains, and localization are not fully captured.
- Self-interactions are recorded, and reciprocal interactions may also be recorded when bait-prey directionality is clear.
- TAB3 and MITAB contain both physical and genetic interactions, so the type must be preserved rather than inferred.
- Coverage is broad for major model organisms and selected human topic areas, but it is not exhaustive and is biased toward curated literature.
- High-throughput and low-throughput evidence should stay visible in the index because it materially affects confidence.
- Symbols and aliases are not safe unique keys; namespace-aware joins are required.

Sources used:
- [BioGRID home](https://thebiogrid.org/)
- [BioGRID download format details](https://wiki.thebiogrid.org/doku.php/downloads)
- [BioGRID TAB 3.0 format](https://wiki.thebiogrid.org/doku.php/biogrid_tab_version_3.0)
- [BioGRID MITAB format](https://wiki.thebiogrid.org/doku.php/psi_mitab_file)
- [BioGRID curation workflow](https://wiki.thebiogrid.org/doku.php/curation_description)
- [BioGRID REST service](https://wiki.thebiogrid.org/doku.php/biogridrest)
- [Supported identifiers](https://wiki.thebiogrid.org/doku.php/identifiers)
