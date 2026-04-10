# Source Release Matrix

This matrix pins the actual acquisition surfaces completed in the current source-report set and translates them into planning guidance for joinability, storage, and reproducibility. The goal is not just to list sources, but to make the downstream contract explicit: what is release-stamped, what should be cached locally, what should stay lazy, and what can be joined without inventing unstable keys.

## Quick Read

- Identity spine: UniProt
- Structure backbone: RCSB/PDBe and AlphaFold DB
- Assay/evidence layers: BindingDB, BioGRID, IntAct
- Annotation layers: InterPro, motif systems, DisProt, Reactome, EMDB
- Evolutionary corpus: pending implementation in `P3-T027`

## Matrix

| Source | Pinned release / snapshot / download surface | Implemented now | Still pending | Local artifact expectation | Joinability / storage note |
|---|---|---|---|---|---|
| RCSB / PDBe | Pin the RCSB mmCIF archive plus PDBe REST/FTP and SIFTS-derived flatfiles such as `pdb_chain_uniprot` and `uniprot_segments_observed`. Treat the archive date and file set as the release boundary. | `P3-T017` acquisition contract exists. | No release-numbered freeze was captured in the report, so the manifest must supply the archive timestamp and exact files used. | Keep raw mmCIF, validation, and mapping files in append-only cache; store compact entry/entity/assembly headers in the planning index. | Best structural join is `pdb_id` plus chain/entity identifiers and SIFTS span mappings. Do not collapse biological assembly and asymmetric unit. |
| UniProt | Pin release-stamped UniProtKB downloads, proteome files, the SPARQL endpoint, and the ID mapping service. | `P3-T018` acquisition pipeline exists. | Exact record set must be manifest-pinned per refresh because the live service is mutable. | Cache UniProtKB exports, proteome snapshots, and selected annotation tracks; keep accession-first summary rows hot. | Canonical join key is primary accession. Preserve secondary accessions, isoforms, and sequence-version lineage. |
| AlphaFold DB | Pin the AlphaFold download surface by accession/model ID, sequence checksum, and per-entry assets (`bcif`, `cif`, `pdb`, `MSA`, `pLDDT`, `PAE`). The current public site advertises 200M+ predictions and a March 2026 complex update. | `P3-T025` acquisition pipeline exists. | Full coordinate hydration is intentionally deferred until selected examples need it. | Keep metadata, confidence summaries, and file URLs in the hot index; fetch coordinates and auxiliary assets lazily. | Join to UniProt accession first, then use `sequenceChecksum`, `entryId`, and `modelEntityId` for exact source provenance. |
| BindingDB | Pin the quarterly UC San Diego archive for reproducible snapshots; use the monthly TSV refreshes only for incremental or validation pulls. | `P3-T019` acquisition pipeline exists. | The live site is updateable, so immutable packages should always cite the archived snapshot rather than the website state. | Cache row-level TSV metadata and the exact `Reactant_set_id` rows used by selected examples. | Best joins are UniProt accession for targets and `BindingDB Reactant_set_id` for interaction rows. Preserve censored affinity values and assay provenance. |
| InterPro / motif systems | Pin InterPro release 108.0 and its download/API bundle; for motif systems also preserve PROSITE, ELM, and RCSB motif-search result payloads as release-stamped query outputs. | `P3-T023` acquisition pipeline exists. | Query-driven motif retrieval is still logically lazy even when the catalog is pinned. | Store compact entry catalogs, motif accessions, spans, and representative flags; keep full matches and logos lazy. | Join on `IPRxxxxx`, `PSxxxxx`, `PDOCxxxxx`, `PRUxxxxx`, `ELME#####`, and residue spans. Preserve member-database provenance. |
| DisProt | Pin `DisProt release_2025_12.json` and the `api-version: 8.0.1` response surface; the current report also cites DisProt 9.8, released June 2025. | `P3-T024` acquisition pipeline exists. | Full region history, curated text, and evidence payloads remain on-demand. | Keep protein-level disorder summary rows and region coordinates in the index; store the raw release JSON and vocabulary snapshot locally. | Join by UniProt accession, with `disprot_id` and `region_id` as source-specific identifiers. Separate disorder-state, transition, and function annotations. |
| BioGRID | Pin version 5.0.255 and the monthly TAB3/MITAB download family. | `P3-T020` acquisition pipeline exists. | No additional blocker is implied, but the release should still be captured in each manifest because the site updates monthly. | Cache compact interaction summaries and the exact row IDs used for selection; lazy-load full TAB3/MITAB rows. | Join by UniProt accession when available and by `BioGRID Interaction ID` for the evidence row. Preserve physical vs genetic type. |
| IntAct | Pin release 247 and the PSI-MI XML / PSI-MITAB 2.5, 2.6, 2.7 / XGMML / RDF / BioPAX export family. | `P3-T021` acquisition pipeline exists. | Native complex records versus binary projections must remain distinguishable in downstream materialization. | Store compact interaction summaries, publication provenance, and the binary-vs-native-complex flag; keep PSI-MI XML and full MITAB lazy. | Join by UniProtKB accession and IntAct `Interaction AC`, with IMEx IDs where present. Preserve expanded-from-complex lineage. |
| Reactome | Pin Reactome v95, released 2025-12-09, plus the quarterly Zenodo snapshot family starting at v89. | `P3-T022` acquisition pipeline exists. | Diagram, BioPAX, SBML, and deep Content Service payloads should stay lazy unless a candidate is selected. | Cache pathway hierarchy, stable identifiers, reaction-PMID links, and human complex-to-protein mapping tables. | Join by Reactome stable ID and UniProt accession. Keep version suffixes and species context. |
| EMDB | Pin EMDB header XML and map files by accession plus schema version, and preserve EMICSS weekly/monthly refresh outputs when cross-links are needed. | `P3-T026` acquisition pipeline exists. | Heavy map volumes, half-maps, masks, FSC outputs, and long validation reports remain lazy. | Keep accession, method, resolution, status, linked PDB/EMPIAR IDs, and EMICSS summary counts in the planning index. | Join by EMDB accession first, then by PDB, EMPIAR, and linked UniProt IDs when available. Treat it as an advanced modality layer. |
| Evolutionary / MSA corpus | No acquisition pipeline is completed yet. The report scope points to UniProt/UniRef, InterPro, OrthoDB, Ensembl Compara, and frozen local MMseqs2 MSAs as the intended corpus. | Not yet implemented. | `P3-T027` is the open acquisition task and should pin corpus snapshot, aligner version, and parameters before any reuse. | Expect a future local corpus cache, exact sequence snapshot manifest, and alignment-parameter record. | This is a sequence-context layer, not an identity backbone. It should join through UniProt accession and sequence hash/version, never through aliases alone. |

## What Is Implemented Versus Pending

Implemented acquisition coverage is already strong across the main summary-library surfaces:

- Structure: RCSB/PDBe, AlphaFold DB, and EMDB are all covered.
- Identity and annotation: UniProt, InterPro/motif systems, and DisProt are covered.
- Evidence and pathway context: BindingDB, BioGRID, IntAct, and Reactome are covered.

The only clearly pending acquisition path in this slice is the evolutionary corpus pipeline (`P3-T027`). That task should not be treated as a generic placeholder: it needs an explicit snapshot policy for the sequence corpus, the alignment engine, and the exact MSA inputs so the output can be rebuilt later.

## Local Artifact Expectations

To keep the acquisition layer joinable and reproducible, each source should leave behind the same kinds of local artifacts:

- A raw snapshot cache with the release-stamped download files exactly as acquired.
- A manifest that records source URL, release identifier or archive date, retrieval time, checksum, and any query or filter parameters.
- A compact planning index with accession-first metadata, stable join keys, and coarse quality flags.
- A canonical or normalized projection only when the source is materially used in the platform.
- Lazy asset pointers for heavy coordinates, maps, MSA payloads, validation bundles, or full evidence exports.

## Reproducibility Rules

1. Pin the source by release, archive date, or manifestable download set, never by an implicit live web state.
2. Preserve original source identifiers alongside normalized join keys.
3. Keep ambiguous mappings visible instead of collapsing them into a single row.
4. Treat heavy assets as lazy, not as preloaded defaults.
5. Record the exact artifact path and source version for every example that may later be packaged or audited.

## Planning Takeaway

The completed acquisition tasks already support a release-aware planning index for proteins, structures, ligands, interactions, pathways, disorder, motifs, and EM maps. The next gap is not breadth but rigor: the remaining evolutionary corpus task needs the same pinning discipline so sequence-context features can be reused without hidden drift.
