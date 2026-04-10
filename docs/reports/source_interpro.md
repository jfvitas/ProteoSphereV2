# Source Analysis Report

Source:
InterPro is the best single summary-library source for protein domains, families, repeats, homologous superfamilies, and conserved sites. It integrates signatures from 13 member databases and exposes a unified entry model with a unique `IPRxxxxx` accession, entry type, member-signature provenance, GO links, proteins, structures, pathways, and taxonomic distribution. InterPro also exposes related pages for member signatures, proteins, structures, taxons, proteomes, and sets/clans. Primary sources: [InterPro entries](https://interpro-documentation.readthedocs.io/en/latest/entries_info.html), [InterPro documentation](https://interpro-documentation.readthedocs.io/en/latest/interpro.html), [InterPro API repository](https://github.com/ProteinsWebTeam/interpro7-api), [Representative domain selection](https://interpro-documentation.readthedocs.io/en/latest/represent_dom.html), [InterPro protein viewer](https://interpro-documentation.readthedocs.io/en/latest/protein_viewer.html)

Acquisition:
Use the official InterPro API and release-stamped downloads as the primary ingestion path. The API is organized around six endpoints: `entry`, `protein`, `structure`, `set`, `taxonomy`, and `proteome`, and the repository notes that the backend is served from MySQL metadata, Elasticsearch links, and optional Redis response caching. That separation is a good model for the platform: keep a compact planning index, preserve relationship links separately, and only hydrate large detail payloads when examples are selected. Treat each InterPro release as a snapshot boundary; the current public repository page lists InterPro 108.0 as the latest release, dated Jan 30, 2026.

Relevant fields:
- InterPro accession `IPRxxxxx`, entry name, entry type, and short description
- Entry types: family, domain, site, repeat, and homologous superfamily
- Member database accession and database namespace for the contributing signature
- Integrated vs unintegrated status, including InterPro-N annotations where relevant
- GO terms, taxonomic distribution, protein matches, structure matches, pathway links, and clan/set relationships
- Per-protein feature spans, representative match flags, and source-release metadata
- Member-database signature type, which is critical because representative selection uses the original signature type rather than the InterPro entry type

Use in platform:
InterPro should be a core annotation spine for the summary library and a strong enrichment source for training packets. For canonical protein summaries, it gives a compact, consistent domain-architecture view that is richer than any single member database and easier to normalize than a raw multi-database signature dump. For training data, it supplies evidence-bearing feature spans that help separate proteins by architecture, conserved sites, and family membership, which makes it valuable for split design, candidate grouping, and hard-negative selection. It is especially useful when combined with UniProt accession joins, because InterPro provides the annotation layer while UniProt provides the identity spine.

Compatibility:
- Proteins: very strong. This is InterPro's main fit.
- Domains/families/sites/repeats: excellent. These are the native primitives.
- Protein pairs: moderate at best. InterPro itself is unary, but pair-context can be inferred when a site or domain is partner-aware or structure-linked.
- Ligands: indirect. Useful for catalytic sites, binding sites, and cofactor-related annotations, but not a ligand catalog.
- Nucleic acids: weak. Any NA relevance is secondary and should not be treated as authoritative.

Join keys:
- Best protein join key: UniProt accession, with isoform awareness when a site span is isoform-specific.
- Best annotation join key: `IPRxxxxx` for the integrated entry and the member-signature accession for provenance.
- Best structure join key: PDB ID, then chain/entity and residue coordinates.
- Best taxon join key: NCBI taxonomy ID.
- Best release join key: InterPro release number and release date.
- Best family-relationship join key: parent/child InterPro entry links and clan/set accessions.

Storage recommendation:
- Preload: InterPro entry catalog, entry type, entry description, parent/child relationships, clan/set membership, and a compact namespace map for member databases.
- Indexed: `IPRxxxxx`, member-signature accessions, UniProt accession, taxon ID, residue span, representative flag, GO terms, and structure/pathway link identifiers.
- Lazily fetched: full protein match tables, full structure and pathway payloads, long entry descriptions, InterPro-N detail pages, and any member-database-specific evidence text needed only for audit or display.
- Canonical layer: store InterPro as a separate annotation record keyed to the canonical protein, not as an overwrite of the protein record.

Lazy materialization advice:
The hot path should carry only accession, protein mapping, residue span, type, representative status, and release stamp. Hydrate the full entry record only when a candidate protein, family cluster, or split group is actively being built. For the summary library, precompute one compact annotation row per protein-match span, then attach the entry metadata and source-signature provenance on demand. For training packets, fetch the exact protein-match rows and any linked structure or pathway context only for examples that survive selection, deduplication, and split assignment.

Quality and caveats:
InterPro is the safest umbrella layer, but its quality is inherited from the underlying member databases and not all signatures are equally reliable. Integrated entries are the best default labels; unintegrated signatures and InterPro-N-style annotations should be treated as lower-confidence evidence unless corroborated elsewhere. Representative-domain and representative-family selection is deterministic for a given protein and match set, but it is protein-specific and can change when member databases are updated. The selection logic also uses the member-database signature type rather than the InterPro entry type, so the storage model must preserve original source type. Coverage is broad but not exhaustive, and sparse families or taxon-specific signatures can still be missed.

Training-set design implications:
- Use InterPro architecture to group near-duplicate proteins before split assignment so family leakage does not inflate validation metrics.
- Use site and domain spans to build hard-negative sets from proteins that share a fold or family but differ at the functionally relevant position.
- Use GO terms and pathway links as weak contextual labels, but keep them separate from the structural label core.
- Use clan/set and parent/child relationships to prevent overcounting closely related annotations as independent evidence.
- Preserve source-signature provenance so a training packet can distinguish integrated consensus from single-database evidence.
- Prefer release-pinned InterPro snapshots for immutable training packages, because member-database updates can change representative selection and entry integration.

Sources used:
- [InterPro entries](https://interpro-documentation.readthedocs.io/en/latest/entries_info.html)
- [InterPro documentation](https://interpro-documentation.readthedocs.io/en/latest/interpro.html)
- [InterPro API repository](https://github.com/ProteinsWebTeam/interpro7-api)
- [Representative domain selection](https://interpro-documentation.readthedocs.io/en/latest/represent_dom.html)
- [InterPro protein viewer](https://interpro-documentation.readthedocs.io/en/latest/protein_viewer.html)
