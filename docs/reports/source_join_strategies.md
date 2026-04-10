# Source Join Strategies

This report defines the canonical join strategy for the completed compatibility, release-matrix, and joinability analyses. The rule is simple: **join by the most stable source-native identifier first, normalize to UniProt for protein-bearing objects, and keep unresolved or many-to-many mappings explicit instead of collapsing them**.

## Canonical Join Order

1. Anchor every record to the right entity class first: protein, pair/interactor, ligand, structure, motif, pathway, disorder, or evolutionary feature.
2. Use the source-native canonical identifier for that class.
3. Normalize to UniProt accession when the object is protein-bearing.
4. Validate with span, taxon, sequence version/hash, or assembly context when the source provides it.
5. If a join is still ambiguous, keep it unresolved with candidate provenance intact.

## Implementation-Grade Strategies

| Entity | Preferred keys | Fallback keys | Ambiguity handling | Remain unresolved when |
|---|---|---|---|---|
| Proteins | UniProt primary accession; sequence version/hash; isoform ID; taxon | Secondary accessions; replacement history; gene symbol only for lookup | Treat secondary accessions as aliases, not alternate primary IDs. Preserve isoform and sequence-version lineage. | Multiple accessions match the same display name; isoform cannot be determined; taxon conflicts; sequence identity is not validated. |
| Pairs / interactors | BioGRID Interaction ID for BioGRID rows; IntAct Interaction AC and IMEx ID for IntAct rows; normalized UniProt pair for biological interpretation | Entrez Gene ID; BioGRID ID; participant aliases/symbols | Preserve physical-vs-genetic type, binary-vs-native-complex lineage, and directionality if present. Do not flatten n-ary complexes into binary edges without lineage. | One or both participants are not accession-resolved; a complex projection cannot be traced back; species, directionality, or interaction type is ambiguous. |
| Ligands | BindingDB `Reactant_set_id` and `MonomerID`; InChIKey; SMILES; RCSB CCD/component ID; ChEBI for pathway context | Assay row IDs; chemical synonyms; portal names | Keep target, assay, and chemistry separate. Preserve salt/tautomer/covalent-state notes when available. | Only a name synonym exists; the chemical identity is partial, salt/tautomer ambiguous, or the structure-bound ligand cannot be mapped to a stable component ID. |
| Structures | RCSB/PDBe `pdb_id + entity_id + chain_id + assembly_id + residue span -> UniProt`; AlphaFold `UniProt accession + sequenceChecksum + entryId + modelEntityId` | SIFTS mappings; chain labels; residue numbering; EMDB/PDB cross-links | Experimental and predicted coordinates stay separate. Keep asymmetric unit and biological assembly distinct. Preserve missing residues and renumbering gaps. | Assembly state is unclear; chain remapping conflicts; the residue span does not map cleanly; predicted and experimental coordinates would be merged into one object. |
| Motifs | InterPro `IPRxxxxx`; PROSITE `PDOCxxxxx / PSxxxxx / PRUxxxxx`; ELM `ELME#####`; motif span on UniProt | Member-signature accessions; portal result payloads; query fingerprints | Attach motifs as span-aware annotations, not free-text labels. Preserve integrated vs unintegrated provenance, signature type, and evidence count. | The span is not stable; multiple motif systems match with no discriminating evidence; the capture is portal-only and the accession/payload was not retained. |
| Pathways | Reactome stable ID plus version and species; UniProt participation; complex/reaction membership | ChEBI; PMID; pathway ancestry; compartment labels | Treat Reactome as pathway and reaction context, not assay authority. Keep version suffixes and species context. | Species is mixed or unclear; the event is inferred-only and not suitable as direct evidence; complex membership cannot be mapped back to a stable Reactome object. |
| Disorder | UniProt accession; DisProt accession; region ID; residue span; disorder-state / transition / function term IDs | DisProt release JSON; evidence IDs; curator text | Separate disorder-state, disorder-transition, and disorder-function annotations. Absence of DisProt coverage is not a negative label. | Only partial coverage exists; the annotation type is conflated; the accession changed and cannot be normalized; span coordinates are absent or conflicting. |
| Evolutionary features | UniProt accession; sequence version/hash; frozen corpus snapshot; MSA family / cluster / orthogroup ID | UniRef; OrthoDB; Ensembl Compara; taxon; local MMseqs2 job ID | Treat evolutionary data as a sequence-context layer and keep the exact corpus and aligner parameters with the result. | Corpus snapshot, aligner version, or parameters are missing; sequence version drift makes the alignment non-reproducible; family membership is many-to-many without a stable representative. |

## Source-Specific Rules

- **UniProt remains the canonical protein spine**. Everything protein-bearing should normalize there first, even if the source also carries gene names, aliases, or historical accessions.
- **RCSB/PDBe is the experimental structure authority**. Preserve `pdb_id`, entity, chain, assembly, and SIFTS span mappings separately.
- **AlphaFold DB is the predicted companion**. Join by UniProt accession first, then checksum and model identifiers. Never merge it with experimental coordinates.
- **BindingDB is the ligand-assay authority**. Use row identity and chemical identifiers, not target names alone.
- **BioGRID and IntAct are interaction evidence layers**. Keep their native interaction identifiers and projection lineage.
- **InterPro, PROSITE, ELM, and RCSB motif retrieval are span-aware annotation layers**. Use the accession plus residue span, not display names.
- **Reactome is pathway context**. Use it for reaction membership, ancestry, and weak functional grouping.
- **DisProt is disorder context**. It is not a negative-label source.
- **Evolutionary/MSA features are priors**. They should drive split governance, conservation weighting, and redundancy reduction, but not substitute for identity.

## Ambiguity And Unresolved Policy

- Keep a join unresolved if the best candidate is only supported by aliases, display names, or symbols.
- Keep a join unresolved if the source can only provide a many-to-many mapping and no tie-breaker exists.
- Keep a join unresolved if source class would be changed by the projection, such as predicted structure being merged into experimental structure or a native complex being flattened into a simple pair.
- Keep unresolved placeholders visible in downstream materialization, with candidate IDs, source provenance, and the reason for failure.
- Prefer explicit `join_status` values such as `resolved`, `ambiguous`, and `unresolved` over silent coercion.

## Practical Defaults

- Prefer accession-first joins, then validate with sequence/version, taxon, and span.
- Preserve source-native IDs in every normalized record.
- Never discard evidence class, release version, or projection lineage.
- Use lazy hydration for heavy payloads such as full coordinates, maps, alignment blocks, motif tables, or long portal text.

## Outcome

This strategy yields a single stable protein spine with source-specific evidence layers attached around it. The platform can then join proteins, pairs, ligands, structures, motifs, pathways, disorder, and evolutionary features without collapsing evidence semantics or hiding ambiguity.
