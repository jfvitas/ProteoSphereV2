# Source Analysis Report

Source:
Evolutionary and MSA data sources for the platform's summary library and model/training pipeline. The practical shortlist is UniProt/UniRef as the identity and redundancy backbone, InterPro for curated family/domain/site normalization, OrthoDB for broad orthology and phyletic profiles, Ensembl Compara for species-scoped homology and conservation tracks, and a frozen local MSA corpus built from those sequence sources when a precomputed source is not enough. Primary sources: [UniProt SPARQL endpoint](https://sparql.uniprot.org/), [UniProt RDF schema ontology](https://purl.uniprot.org/core/), [InterPro browsing docs](https://interpro-documentation.readthedocs.io/en/latest/browse.html), [InterPro entry docs](https://interpro-documentation.readthedocs.io/en/latest/entries_info.html), [InterPro download docs](https://interpro-documentation.readthedocs.io/en/latest/download.html), [InterPro license](https://interpro-documentation.readthedocs.io/en/latest/license.html), [InterPro Pfam page](https://interpro-documentation.readthedocs.io/en/latest/pfam.html), [OrthoDB RDF/SPARQL frontend](https://purl.orthodb.org/), [OrthoDB WIDOCO docs](https://sparql.orthodb.org/widoco/index-en.html), [OrthoDB site](https://www.orthodb.org/), [Ensembl Compara overview](https://www.ensembl.org/info/docs/compara), [Ensembl multiple genome alignments](https://www.ensembl.org/info/genome/compara/multiple_genome_alignments.html), [Ensembl comparative genomics API](https://www.ensembl.org/info/docs/api/compara/index.html), [Ensembl gene families note](https://www.ensembl.org/info/genome/compara/family.html)

Acquisition:
Use UniProtKB and UniRef as the frozen sequence corpus for all downstream family and conservation work. Use InterPro as the canonical family/domain/site layer because it integrates signatures from multiple member databases and exposes both integrated and unintegrated signatures. Use OrthoDB for cross-species orthogroups, clade-level grouping, and phyletic profiles when the question is broader than a single species set. Use Ensembl Compara for taxa covered by Ensembl when gene trees, homology quality, and whole-genome conservation scores matter. For proteins that still lack a satisfactory precomputed alignment, build a local MSA job against a pinned sequence snapshot with MMseqs2 and store the exact inputs and parameters so the result is reproducible.

Relevant fields:
- UniProt accession, secondary accession history, isoform identifier, sequence version, sequence hash or MD5, organism taxon, and proteome/reference-proteome membership.
- UniRef cluster identifier, representative/member relations, cluster size, and sequence redundancy level.
- InterPro accession `IPRxxxxx`, member-database accession, entry type, taxonomic distribution, proteins, structures, pathways, and integrated versus unintegrated status.
- Pfam family accession `PFxxxxx`, clan accession `CLxxxxx`, and direct seed/full-alignment provenance when the pipeline needs member-level Pfam behavior.
- OrthoDB orthogroup ID, taxonomic level, single-copy versus multi-copy context, evolutionary-rate summary, and xrefs to UniProt/Ensembl/GO where present.
- Ensembl Compara gene-tree stable ID, homology type, orthology quality, conservation score, constrained elements, alignment block identity, and species-tree context.
- Local MSA outputs: alignment coverage, depth, Neff, gap fraction, entropy, per-position conservation, coupling/co-evolution scores, and taxon spread.

Use in platform:
These sources should feed the summary library as compact sequence-family and conservation summaries, not as opaque alignment blobs. They are most valuable for residue weighting, interface reliability, family-aware split grouping, negative-sample control, and missing-modality compensation when structure alone is too sparse. They also support weak labels such as conserved core, taxon-restricted family, orthogroup membership, and alignment depth, all of which are useful for multimodal training without pretending that every family label means the same thing.

Compatibility:
- Proteins: strong. This is the primary fit for all sources in this report.
- Structures: indirect but useful through mapped residues, domains, and conserved regions.
- PPIs: indirect. Use conservation and co-evolution as priors, not as direct interaction truth.
- Ligands and nucleic acids: secondary only, except where a conserved site or orthologous context is relevant to a protein-mediated system.

Join keys:
- Canonical protein join: UniProt accession first, with isoform-aware spans when needed.
- Sequence lineage join: sequence hash plus sequence version for exact rebuilds.
- Family join: InterPro accession as the normalization spine, with Pfam accessions preserved as member-database provenance.
- Cluster join: UniRef cluster ID for redundancy control and split governance.
- Orthology join: OrthoDB orthogroup ID and Ensembl gene/tree IDs only after the protein-to-UniProt mapping is resolved.
- Taxon join: NCBI taxonomy ID or the source's stable taxon identifier, normalized to the platform's taxon table.

Storage recommendation:
- Preload: a compact accession-first index containing UniProt accession, taxon, sequence length, sequence hash, UniRef cluster IDs, InterPro entry IDs, OrthoDB group summaries, and Ensembl homology summaries for supported species.
- Index: all accession namespaces, taxon IDs, cluster IDs, orthogroup IDs, gene-tree IDs, source release stamps, alignment depth, and quality flags such as gap fraction or low-depth warnings.
- Lazy fetch: full alignment blocks, HMM/profile payloads, all-member orthogroup tables, long text descriptions, raw tree objects, and any species-specific homology rows not required by the current candidate set.
- Canonical layer: store family, orthogroup, and alignment objects separately from the protein record so one protein can participate in several sequence neighborhoods without being flattened into one label.

Lazy materialization advice:
Keep the hot path on accession, family ID, taxon, depth, and release stamp. When a candidate is promoted into a training packet, hydrate only the exact alignment neighborhood needed for that packet, plus the query parameters that define it. Do not materialize one-off MSA searches into reusable training data unless the frozen corpus, search thresholds, and aligner version are all recorded alongside the packet.

Quality and caveats:
UniRef clusters are similarity clusters, not biological families, so they are best used for redundancy reduction and split grouping rather than function labels. InterPro is the safest umbrella source, but it still includes unintegrated signatures and some AI-generated family descriptions, so low-confidence signatures should not be treated as gold labels without corroboration. Direct Pfam is useful for family-level HMM behavior, but the direct view is reference-proteome-biased and should be used sparingly when InterPro already provides the needed family label. OrthoDB groups are clade-defined orthologous groups and can be many-to-many across taxa, which makes them excellent for evolutionary context but dangerous as a single canonical identity key. Ensembl Compara is powerful for conservation and homology, but its gene-family pages were retired as of release 102, so the current practical surface is homology, gene trees, and whole-genome alignment tracks rather than legacy family browsing. For local MSA jobs, the main failure modes are shallow depth, biased taxon sampling, and non-reproducible database drift, so every packet needs the corpus snapshot and alignment parameters.

Recommended short list:
1. UniProt/UniRef for canonical sequence identity, redundancy reduction, and reference-proteome anchoring.
2. InterPro for the family/domain/site spine and cross-database normalization.
3. OrthoDB for broad ortholog groups and phyletic-profile style evolutionary summaries.
4. Ensembl Compara for supported species when homology quality and conservation scores matter.
5. Frozen local MMseqs2 MSAs over a pinned sequence corpus for proteins that need custom conservation or coupling features.

Sources used:
- [UniProt SPARQL endpoint](https://sparql.uniprot.org/)
- [UniProt RDF schema ontology](https://purl.uniprot.org/core/)
- [InterPro browsing docs](https://interpro-documentation.readthedocs.io/en/latest/browse.html)
- [InterPro entry docs](https://interpro-documentation.readthedocs.io/en/latest/entries_info.html)
- [InterPro download docs](https://interpro-documentation.readthedocs.io/en/latest/download.html)
- [InterPro license](https://interpro-documentation.readthedocs.io/en/latest/license.html)
- [InterPro Pfam page](https://interpro-documentation.readthedocs.io/en/latest/pfam.html)
- [OrthoDB RDF/SPARQL frontend](https://purl.orthodb.org/)
- [OrthoDB WIDOCO docs](https://sparql.orthodb.org/widoco/index-en.html)
- [OrthoDB site](https://www.orthodb.org/)
- [Ensembl Compara overview](https://www.ensembl.org/info/docs/compara)
- [Ensembl multiple genome alignments](https://www.ensembl.org/info/genome/compara/multiple_genome_alignments.html)
- [Ensembl comparative genomics API](https://www.ensembl.org/info/docs/api/compara/index.html)
- [Ensembl gene families note](https://www.ensembl.org/info/genome/compara/family.html)
