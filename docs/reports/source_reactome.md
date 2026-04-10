# Source Analysis Report

Source:
Reactome is a curated, peer-reviewed pathway database with a human-first content model and computed projections to other species. The public site currently reports Reactome v95 (released December 9, 2025) with 2,848 human pathways, 16,200 reactions, 11,651 proteins, 2,183 small molecules, 1,085 drugs, and 42,098 literature references. Reactome exposes open-data downloads, a Content Service API, a Graph Database export, and quarterly Zenodo release snapshots starting at v89. Primary sources: [Reactome home](https://reactome.org/), [download page](https://reactome.org/download-data), [data model](https://reactome.org/documentation/data-model), [pathway information](https://reactome.org/2-uncategorised/61-pathway-information), [Reactome FAQ / stable identifiers](https://download.reactome.org/documentation/DataModelGlossary_V90.pdf), [curator guide](https://download.reactome.org/documentation/CuratorGuideAndAppendices_V91.pdf)

Acquisition:
Use Reactome as a pathway/reaction knowledge source, not as a raw assay source. The best acquisition path is the official download family plus the Content Service for targeted hydration. For repeatable builds, pin to the quarterly Zenodo release snapshot and keep the stable-identifier database and mapping files alongside it. For graph-style materialization, the Reactome Graph Database and stable-ID/MySQL dumps are better than scraping the UI. The pathway-information TSVs are especially useful because they separate the pathway hierarchy into compact tables and map stable IDs directly to pathway names and species.

Relevant fields:
- Stable identifier and versioned identifier for pathways, reactions, complexes, and physical entities.
- Event type: pathway, reaction, black-box event, polymerisation, depolymerisation.
- Pathway hierarchy, parent-child relations, species, and review status.
- Inputs, outputs, catalysts, regulators, and reaction participants.
- PhysicalEntity class, ReferenceEntity, compartments, modification state, and entity-set membership.
- Complex membership and human complex-to-protein mappings.
- Cross-references to UniProt, ChEBI, Ensembl, NCBI, miRBase, GtoP, OMIM, and PMID-linked reaction evidence.
- Disease annotations, GO associations, and inferred-event metadata where present.

Use in platform:
Reactome is the best summary-library source here for biological context enrichment. It should contribute pathway membership, reaction context, compartment context, complex context, disease context, and evidence provenance around a canonical protein or complex example. For downstream training-set design, Reactome is especially useful for grouping examples by pathway family, excluding near-duplicate pathway neighbors from train/val splits, and producing weak labels such as pathway membership, reaction participation, catalyst role, and compartment localization. It is high value for protein-centric and complex-centric tasks, and much weaker as a standalone ligand source.

Compatibility:
- Proteins: high. Reactome explicitly models accessioned protein entities and their reaction roles.
- Complexes: high. Complexes are first-class physical entities with explicit membership and pathway placement.
- Ligands: moderate. Small molecules are represented, but Reactome is not a compound-activity archive.
- PPIs: moderate and indirect. Complex membership and derived interaction files are useful, but they are not a substitute for a dedicated PPI resource.
- Nucleic-acid or PNA-adjacent examples: limited. Reactome contains nucleic-acid entities and reactions, but this is not its strongest coverage axis.

Join keys:
- Primary protein join: UniProt accession from ReferenceEntity / physical-entity mappings.
- Primary pathway join: Reactome stable identifier (ST_ID), preserving version and species code.
- Complex join: complex stable identifier plus participating protein molecule mappings.
- Small-molecule join: ChEBI identifier, with drug annotations treated as auxiliary rather than canonical chemistry.
- Evidence join: PMID and reaction-PMID mapping files.
- Species join: Reactome species code and, where available, NCBI taxonomy from linked identifiers.

Storage recommendation:
- Preload: complete pathway list, pathway hierarchy, stable-identifier manifest, reaction-PMID links, human complex-to-protein mappings, and compact mapping tables for UniProt, ChEBI, and Ensembl.
- Index: stable IDs, event types, review status, species, compartment, pathway ancestry, catalyst/regulator links, complex membership, and cross-reference namespaces.
- Lazy fetch: full diagrams, SVG/PNG assets, SBML/BioPAX exports, broad Content Service payloads, and nonhuman inferred-event detail unless a candidate enters the active training slice.
- Canonical layer: store pathway, reaction, physical-entity, reference-entity, complex, and evidence objects separately so one protein can appear in multiple compartments, modified forms, and pathway roles without flattening.

Lazy materialization advice:
Keep the summary library compact by storing pathway ancestry, reaction role, compartment, and evidence counts up front, then hydrate the full Reactome event only when an example is promoted. The long tail of diagram payloads, nested pathway detail, and all-species exports should remain out of the hot path. For training packets, materialize only the exact pathway and reaction neighborhood required for the final split, and preserve the release snapshot plus stable-ID version so the packet can be rebuilt later.

Quality and caveats:
Reactome is curated, but it is not uniformly direct-evidence human biology. Many human events are inferred from model organisms, and the data model explicitly separates the model-organism event from the inferred human event. Stable IDs are versioned, so consumers must preserve both the base identifier and the version suffix. Proteins in different compartments or modification states are distinct Reactome entities, which is good for biological precision but dangerous if flattened into a single row. Entity sets intentionally group interchangeable molecules, so they should remain set objects rather than being exploded into a single canonical protein. Reactome-derived PPI files infer interactions between complex members and only consider complexes with four or fewer protein components to reduce false positives, which is useful but still inference, not direct binding evidence.

Sources used:
- [Reactome home](https://reactome.org/)
- [Reactome download page](https://reactome.org/download-data)
- [Reactome data model](https://reactome.org/documentation/data-model)
- [Reactome pathway information](https://reactome.org/2-uncategorised/61-pathway-information)
- [Reactome Data Model Glossary](https://download.reactome.org/documentation/DataModelGlossary_V90.pdf)
- [Reactome curator guide](https://download.reactome.org/documentation/CuratorGuideAndAppendices_V91.pdf)
