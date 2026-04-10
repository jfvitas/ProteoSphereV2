# Source Analysis Report

Source:
DisProt

Acquisition:
Treat DisProt as the curated intrinsic-disorder evidence layer, not as a general protein identity source. The live site exposes a clear programmatic API at `https://disprot.org/api/`, and the current API response headers advertise `api-version: 8.0.1` while the official vocabulary endpoint returns a release-stamped download named `DisProt release_2025_12.json`. The browsing API returns protein-level records with disorder regions, UniProt-linked identifiers, UniParc and UniRef cross-references, taxonomy, and per-region evidence payloads; the controlled-vocabulary endpoint exposes the ontology-backed annotation terms used by curators. Primary sources: [DisProt website](https://disprot.org/), [DisProt API browse endpoint](https://disprot.org/api/search), [DisProt controlled vocabulary endpoint](https://disprot.org/api/disprot_cv), [DisProt 2026 NAR update](https://academic.oup.com/nar/article-abstract/54/D1/D383/8325584), [DisProt 2024 NAR update](https://academic.oup.com/nar/article-abstract/52/D1/D434/7334088)

Relevant fields:
- `acc` as the DisProt protein accession
- `disprot_id` as the stable entry identifier
- `sequence`, `length`, `organism`, and `ncbi_taxon_id`
- `genes`, synonyms, and ORF names for display only
- `UniParc`, `uniref50`, `uniref90`, and `uniref100` cluster anchors
- `regions_counter`, `regions`, and `disprot_consensus`
- Region-level `region_id`, `start`, `end`, and `version`
- Region `term_id`, `term_name`, `term_namespace`, and `term_ontology`
- Evidence fields such as `ec_id`, `ec_go`, `ec_name`, `ec_ontology`, `reference_id`, `reference_source`, and `reference_html`
- Curation and provenance fields such as `curator_id`, `curator_name`, `curator_orcid`, `validated`, `date`, `released`, and `uniprot_changed`
- Structured extras such as `cross_refs`, `annotation_extensions`, `conditions`, `construct_alterations`, `interaction_partner`, `sample`, and `statement`
- Derived summary metrics such as `disorder_content` and `alphafold_very_low_content` where present

Use in platform:
DisProt is the best curated source here for experimentally validated intrinsic disorder, disorder transitions, and disorder-mediated functions. The 2026 update reports that DisProt version 9.8, released in June 2025, contains 3201 IDPs and 13,347 pieces of evidence, with more than 1500 structural-state annotations and over 1300 function annotations, so the source is large enough to matter but still small enough to keep as a high-value, high-confidence annotation layer rather than a bulk sequence corpus. For the summary library, it should contribute a compact disorder mask, disorder-function labels, and evidence-qualified text summaries. For the training-packet pipeline, it should supply positive disorder spans, disorder-to-order transition spans, motif-linked disorder regions, and quality-weighted supervision for region-level tasks.

Compatibility:
- Proteins: strong, but only through a canonical protein join.
- Motifs and linear interaction features: excellent, because many functional annotations live in disordered segments.
- Interfaces: strong as a context layer, especially for fuzzy, transient, or induced-fit contacts.
- Ligands: indirect, mostly through binding motifs, PTM display sites, and disordered regulatory regions.
- Nucleic acids: indirect but useful for disorder-mediated binding and recognition, not as a primary NA source.

Join keys:
- Primary join key: UniProt accession from the DisProt `acc` field.
- Canonical fallback: UniProt accession normalization through the platform registry, because DisProt records can carry `uniprot_changed: true`.
- Secondary cluster joins: `UniParc` and the UniRef family of identifiers, but only as grouping aids, not as canonical primary keys.
- Organism join key: `ncbi_taxon_id`.
- Region join key: DisProt `region_id` plus protein accession.
- Evidence join keys: `reference_id`/PMID, `ec_id`, `term_id`, and `disprot_id`.
- Cross-resource join keys: PDB IDs in `cross_refs`, GO terms, IDPO terms, and ECO codes.

Storage recommendation:
- Preload: release metadata, the DisProt accession map, the IDPO/ECO-controlled vocabulary catalog, the thematic dataset catalog, and compact protein-level summary rows.
- Indexed: `acc`, `disprot_id`, `UniParc`, `uniref50`, `uniref90`, `uniref100`, `ncbi_taxon_id`, `region_id`, `term_id`, `term_namespace`, `ec_id`, `reference_id`, `released`, `start`, `end`, and `disprot_consensus` span type.
- Lazily fetched: full `statement` text, `reference_html`, curator audit history, `annotation_extensions`, `conditions`, `sample`, `construct_alterations`, `interaction_partner`, `region_history`, and any auxiliary deposition payloads.
- Canonical layer: store one protein record keyed by UniProt accession and attach DisProt region records as separate evidence objects; do not overwrite canonical protein state with disorder annotations.

Lazy materialization advice:
Keep the hot path narrow. For summary generation, materialize only the protein accession, disorder span coordinates, term namespace, and a lightweight confidence/evidence summary. Hydrate the full region record only when a candidate enters curation, split assignment, or example packaging. Preserve `disprot_consensus` as a compact residue-span overlay for fast display and masking, but fetch the full `regions` payload only when an explanation, audit trail, or training packet needs the underlying evidence. This is especially important because some records contain multiple region types for the same span, and the same protein can carry structural-state, transition, and function annotations simultaneously.

Quality and caveats:
DisProt is curated, but the annotation types are not interchangeable. A structural-state span, a transition span, and a disorder-function span should not be collapsed into one boolean label, because they answer different biological questions. Some annotations are inferred from missing density or incomplete structural models, which is useful for context but not equivalent to direct solution disorder. Coverage is meaningful but incomplete, so absence of annotation is not a negative label. The live records also show accession evolution via `uniprot_changed`, which means historical joins need accession normalization and alias preservation. The 2026 paper also emphasizes that DisProt is now integrated with UniProtKB, PDBe, and Gene Ontology, and that it serves as the reference dataset for CAID, which is a strong signal that the source is good for benchmarking but should remain release-pinned for immutable training packages.

Training-set design implications:
- Use DisProt as a positive-label source for IDRs, IDPs, disorder-to-order transitions, and disorder-mediated function, but keep those label families separate.
- Never treat "not in DisProt" as a negative label; instead, use explicit negatives from other curated sources or controlled hard-negative construction.
- Weight examples by evidence type and curation strength, with MIADE-aligned annotations and direct experimental assertions ranked above weaker or more indirect evidence.
- Group or split by UniProt family, UniRef cluster, and thematic dataset to reduce leakage from homologous disorder motifs.
- Use disorder spans to create hard negatives for motif and interface tasks by pairing proteins that share a family, fold, or binding context but differ in the annotated disordered segment.
- Preserve disorder-function spans as context labels for motif discovery, especially for short linear motifs, PTM display sites, transient recognition, and induced-fit binding regions.
- Keep a clean-to-noisy curriculum: start with direct structural-state annotations, then add transition and function annotations, then add more context-heavy examples.
- For immutable training packets, pin the exact DisProt release and store the record-level evidence snapshot so later curation updates do not silently change labels.

Sources used:
- [DisProt website](https://disprot.org/)
- [DisProt API browse endpoint](https://disprot.org/api/search)
- [DisProt controlled vocabulary endpoint](https://disprot.org/api/disprot_cv)
- [DisProt 2026 NAR update](https://academic.oup.com/nar/article-abstract/54/D1/D383/8325584)
- [DisProt 2024 NAR update](https://academic.oup.com/nar/article-abstract/52/D1/D434/7334088)
