# Source Analysis Report

Source:
Motif and domain annotation systems for proteins and interfaces. For this platform, the practical shortlist is InterPro as the integration spine, PROSITE for curated sequence motifs and profiles, ELM for short linear motifs and partner-context signals, and RCSB PDB motif search for structure-linked local motifs. Pfam should be treated as a member-database view of the InterPro layer unless the team needs direct Pfam-specific behavior. Primary sources: [InterPro documentation](https://interpro-documentation.readthedocs.io/en/latest/interpro.html), [InterPro entries](https://interpro-documentation.readthedocs.io/en/latest/entries_info.html), [InterPro protein viewer](https://interpro-documentation.readthedocs.io/en/latest/protein_viewer.html), [PROSITE home](https://prosite.expasy.org/), [PROSITE user manual](https://prosite.expasy.org/prosuser.html), [PROSITE details](https://prosite.expasy.org/prosite_details.html), [ELM details example](https://elm.eu.org/elms/elmPages/DOC_CYCLIN_RxL_1.html), [RCSB sequence motif search](https://www.rcsb.org/docs/search-and-browse/advanced-search/sequence-motif-search), [RCSB 3D motif search](https://www.rcsb.org/docs/search-and-browse/advanced-search/3d-motif-search), [RCSB search API overview](https://search.rcsb.org/), [Pfam in InterPro](https://interpro-documentation.readthedocs.io/en/latest/pfam.html)

Acquisition:
Use official downloads and APIs first, not HTML scraping. InterPro should be pulled through its download/API surface and release notes, with member-database signatures and integrated entries cached as release-stamped snapshots. PROSITE should be ingested from its accessioned pattern/profile documentation and scan outputs, using the stable `PDOCxxxxx`, `PSxxxxx`, and `PRUxxxxx` identifiers. ELM can be pulled from its class pages and instance tables, while RCSB motif search should be treated as a query service plus a cache of selected match results. Pfam is now effectively a static front end that redirects to InterPro, so do not build a separate live Pfam path unless direct member-db granularity is required.

Recommended short list:
1. InterPro for the domain/family/site spine and cross-database normalization.
2. PROSITE for highly interpretable sequence motifs, patterns, profiles, and ProRules.
3. ELM for short linear motifs, docking motifs, degrons, and motif-to-partner context.
4. RCSB PDB sequence and 3D motif search for structure-linked site and interface retrieval.
5. Optional direct Pfam only if the pipeline needs standalone Pfam clan/family behavior instead of the InterPro view.

Relevant fields:
- InterPro: `IPRxxxxx` entry accession, entry type, member database accession, integrated vs unintegrated status, GO links, taxonomic distribution, proteins, structures, pathways, and clan/set accessions such as `CLxxxxx`.
- PROSITE: documentation accessions `PDOCxxxxx`, motif/profile accessions `PSxxxxx`, ProRule accessions `PRUxxxxx`, pattern or matrix definition, and taxonomic scope.
- ELM: functional site class accession `ELME#####`, class name, motif description, pattern, taxonomic scope, evidence count, instances, interaction-domain hints, and PDB structure links where available.
- RCSB motif search: motif expression or query fingerprint, matched PDB/CSM structure, polymer entity, residue numbering, chain/assembly context, and RMSD for 3D motif search results.
- Pfam: family accession `PFxxxxx`, clan accession `CLxxxxx`, HMM-based family/domain assignment, and reference-proteome bias in the direct Pfam view.

Use in platform:
These sources belong in the summary library as compact protein features and in the training-packet pipeline as evidence-bearing annotations. InterPro should provide the canonical domain architecture view and a stable bridge from member-database signatures to a single searchable entry model. PROSITE should contribute the most precise functional-site labels and should be especially useful for catalytic motifs, metal-binding motifs, glycosylation or phosphorylation patterns, and other sequence-local signatures. ELM should be used for short linear motifs that often encode interaction or regulation, especially where taxon and binding-partner context matter. RCSB motif search should be used to recover structure-local motifs and interface-adjacent residue sets in solved structures or computed models.

Compatibility:
- Proteins: very strong across all four sources.
- Protein interfaces: strong for ELM and RCSB motif search, moderate for PROSITE, and indirect but useful for InterPro through site, domain, and structure cross-links.
- Protein-pair records: best when the source itself includes a partner domain, receptor class, or structure link; weakest when the source is a pure unary motif annotation.
- Ligands: indirect through catalytic, cofactor, and binding-site annotations rather than ligand catalogs.
- Nucleic acids: mostly secondary, with RCSB motif search the only source here that naturally searches DNA/RNA motifs too.

Join keys:
- Canonical protein join: UniProt accession, plus isoform-aware sequence span when a motif maps to a specific isoform.
- Structure join: PDB ID or CSM identifier, then chain/entity identifiers and residue ranges.
- InterPro join: `IPRxxxxx` for the canonical entry, with member accession preserved as provenance and as a back-link to the source signature.
- PROSITE join: `PSxxxxx` for the motif/profile, `PDOCxxxxx` for explanatory documentation, and `PRUxxxxx` for rule-level refinement.
- ELM join: `ELME#####` plus instance coordinates, organism, and evidence count.
- Pair-record join: `protein_accession + motif_span + partner_domain_or_structure_context`. Do not force a protein-pair row unless the source provides partner evidence or a structural interaction context.

Storage recommendation:
- Preload: InterPro entry catalog, PROSITE documentation/accession index, ELM class catalog, and a small curated RCSB motif query catalog for the motifs the platform expects to reuse often.
- Index: motif accession, motif class, protein accession, residue span, taxon, evidence count, integrated/unintegrated flag, partner domain/class, and PDB/CSM references.
- Lazy fetch: full alignment blocks, logos, complete instance tables, long textual descriptions, full RCSB search result payloads, and any HTML-only detail pages needed only for audit or display.
- Canonical layer: store a motif annotation record separately from the protein record, then project motif-bearing proteins or protein pairs only after the canonical protein mapping is resolved.

Lazy materialization advice:
Keep the hot path on accession, span, taxon, and evidence count. For the summary library, precompute one compact row per motif hit with source accession, canonical protein accession, source release, coordinates, taxonomic scope, and a simple reliability flag. For training packets, hydrate only the motif hits and partner context that survive candidate selection, and retain the raw source URL or release stamp so the packet can be rebuilt later without re-querying the world.

Quality and caveats:
InterPro is the safest umbrella source, but it is only as strong as the underlying member databases and contains both integrated and unintegrated signatures. Use unintegrated signatures cautiously and keep them out of high-confidence labels unless a second source agrees. PROSITE is highly interpretable, but its non-matches are not evidence of absence and its license is more restrictive than InterPro's aggregated CC0 data. ELM is excellent for interface-relevant short linear motifs, but motif degeneracy is high and many motifs are biologically meaningful only in the right taxon, disorder context, phosphorylation state, or partner-domain context. RCSB motif search is excellent for local structural similarity, but it is coverage-biased toward available structures and computed models and should be treated as a retrieval layer, not a curated function authority. Pfam direct is useful when member-level HMM details or clans matter, but for most summary-library use cases the InterPro view is the cleaner and more stable ingestion target.

Sources used:
- [InterPro documentation](https://interpro-documentation.readthedocs.io/en/latest/interpro.html)
- [InterPro entries](https://interpro-documentation.readthedocs.io/en/latest/entries_info.html)
- [InterPro protein viewer](https://interpro-documentation.readthedocs.io/en/latest/protein_viewer.html)
- [InterPro search ways](https://interpro-documentation.readthedocs.io/en/latest/searchways.html)
- [InterPro Pfam page](https://interpro-documentation.readthedocs.io/en/latest/pfam.html)
- [PROSITE home](https://prosite.expasy.org/)
- [PROSITE details](https://prosite.expasy.org/prosite_details.html)
- [PROSITE user manual](https://prosite.expasy.org/prosuser.html)
- [PROSITE license](https://prosite.expasy.org/prosite_license.html)
- [ELM detail examples](https://elm.eu.org/elms/elmPages/DOC_CYCLIN_RxL_1.html)
- [ELM detail examples](https://elm.eu.org/elms/elmPages/LIG_Pex14_3.html)
- [RCSB sequence motif search](https://www.rcsb.org/docs/search-and-browse/advanced-search/sequence-motif-search)
- [RCSB 3D motif search](https://www.rcsb.org/docs/search-and-browse/advanced-search/3d-motif-search)
- [RCSB Search API overview](https://search.rcsb.org/)
