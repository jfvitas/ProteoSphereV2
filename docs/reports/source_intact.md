# Source Analysis Report

Source:
IntAct is a curated molecular interaction database focused on protein-protein interactions, with data that are also exchanged through the IMEx and PSICQUIC ecosystems. The public IntAct 247 release was announced as reaching 1.5 million binary interaction evidences. IntAct's site exposes interaction search, download, and visualization, and the official training material says data come from direct submissions, high-throughput projects, and the literature.

Acquisition:
Use IntAct as a curated interaction source rather than a raw protein catalog. For repeatable ingestion, prefer the official IntAct download/export paths and keep the raw PSI-MI/MITAB payloads as a release-stamped cache. The site currently advertises PSI-MI XML, PSI-MITAB 2.5/2.6/2.7, XGMML, RDF, and BioPAX exports. For interaction discovery and validation, the web UI and PSICQUIC/IMEx access layers are useful, but the platform should treat those as query and federation surfaces, not as the canonical storage layer.

Relevant fields:
- Interaction accession (`Interaction AC`) and, where present, IMEx identifier.
- Participant identities, aliases, and database cross-references.
- Interactor type, organism/taxonomy, and sequence or sequence-derived identifiers.
- Interaction type, detection method, identification method, and experimental roles.
- Publication provenance: PubMed, DOI, authors, and figure or experiment context.
- Confidence score and supporting parameters when provided.
- Participant features: binding regions, mutations, modifications, and range status.
- Complex membership and whether a displayed binary record was expanded from an n-ary co-complex.

Use in platform:
IntAct is a strong candidate for the summary library's protein-protein interaction layer and a useful training-packet source for pairwise supervision, evidence retrieval, and interaction-context summaries. It should populate canonical interaction evidence records, support protein-centric summaries, and provide pair records that can be traced back to the underlying experiment and publication. IntAct is especially valuable when the platform needs curated interaction provenance and PSI-MI-standard evidence detail rather than just coarse network edges.

Compatibility:
- Proteins: strong, especially for curated protein-centric interaction context.
- PPIs: very strong; this is IntAct's core use case.
- Complexes: strong, but native complexes should not be flattened silently because the portal often displays them as binary after post-processing.
- Ligands: limited to contextual or interactor-adjacent cases.
- Nucleic acids: limited; IntAct/IMEx curation rules are protein-centric and nucleic-acid interactors are not the main remit of the curated subset.

Join keys:
- Best canonical protein join key: UniProtKB accession, with RefSeq as a fallback/secondary sequence anchor where present.
- Best interaction join key: IntAct `Interaction AC`, plus IMEx ID when present.
- Best participant join key: participant/interactor accession plus organism and interaction accession.
- Best feature join key: feature accession or stable feature identifier together with participant and sequence span.
- Supporting joins: PubMed ID, DOI, PSI-MI controlled-vocabulary term IDs, and PSIQUIC/IMEx cross-resource identifiers.
- Alias names and gene names should be treated as lookup aids only, not as canonical keys.

Storage recommendation:
- Preload: compact interaction summaries with interaction AC, participant accessions, organism, interaction type, detection method, publication IDs, confidence summary, and the binary-vs-native-complex flag.
- Indexed: UniProtKB and RefSeq participant cross-references, PSI-MI term IDs, experiment types, feature spans, mutation/modification markers, and publication provenance.
- Lazy fetch: full PSI-MI XML, complete MITAB rows, figure legends, detailed feature annotations, comments, and any federated PSICQUIC/IMEx result sets.
- Canonical layer: store native `InteractionEvidenceRecord` objects, then derive pair records as a separate projection when a complex or spoke-expanded record is selected for training.

Lazy materialization advice:
Do not treat the portal's binary display as the primary truth. IntAct stores co-complexes natively and then post-processes them for a binary view, typically using spoke expansion, so a displayed pair may be an inference from a complex rather than a directly assayed binary interaction. Keep the native evidence record and the derived pair record linked, and only materialize the full participant/feature payload once a candidate interaction is selected for the summary library or a training packet.

Quality and caveats:
IntAct is curated and high-value, but not uniformly direct. Some records are true binary interactions, while others are binary projections of co-complex assays, so downstream consumers must preserve an `expanded_from_complex` style flag or equivalent lineage. The IMEx validation rules are protein-centric and require strong metadata when records are in scope: a valid experiment, publication, organism, and a protein identity xref to UniProtKB or RefSeq. Negative interactions are outside the IMEx remit, so curated subsets will not behave like a general-purpose all-evidence interaction dump. Confidence scores, feature annotations, and cross-reference completeness vary by record, and gene names or aliases are not safe unique identifiers.

Sources used:
- [IntAct resources overview](https://www.ebi.ac.uk/legacy-intact/resources/overview)
- [IntAct training: Searching and visualising data](https://www.ebi.ac.uk/training/online/courses/intact-quick-tour/searching-and-visualising-data-intact/)
- [EMBL-EBI news: IntAct 247 release](https://www.ebi.ac.uk/about/news/updates-from-data-resources/intact-247-release/)
- [IntAct validator help](https://www.ebi.ac.uk/intact/validator/help.xhtml)
