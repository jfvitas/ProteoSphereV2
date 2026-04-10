# Source Joinability Analysis

This report turns the completed source compatibility matrix, source release matrix, and source analysis reports into an implementation-grade joinability guide. The goal is not just to say that the sources are "compatible", but to spell out which joins are canonical, which are lossy, and which require supplemental scraping or portal-specific hydration to become usable.

## Executive Summary

The join stack is clear:

1. **UniProt is the canonical protein identity spine**.
2. **RCSB/PDBe is the authoritative experimental structure spine**.
3. **AlphaFold DB is the predicted-structure companion, not a substitute for experimental coordinates**.
4. **BindingDB, BioGRID, and IntAct are the main evidence layers for ligands and interactions**.
5. **InterPro, PROSITE, ELM, DisProt, and Reactome are enrichment layers that attach to a protein anchor and often need residue spans or pathway context to become meaningful**.

The safest implementation pattern is:

1. Normalize every protein-bearing source to UniProt accession first.
2. Preserve source-native identifiers as lineage, not replacements.
3. Only project interactions, motifs, pathway membership, or disorder onto a canonical protein after the identity mapping is resolved.
4. Keep ambiguous or many-to-many relationships visible instead of collapsing them.

## Joinability By Linkage Type

| Linkage type | High-confidence join path | Main loss modes | Supplemental scraping / hydration needed |
| --- | --- | --- | --- |
| Protein identity | UniProt primary accession, with secondary accessions, isoform IDs, sequence version/hash, and taxon as support | Alias-only joins, historical accession replacement, isoform ambiguity, organism mismatch | Rarely for canonical identity, but sometimes for long detail text or replacement history |
| Pair / interactor | BioGRID Interaction ID, IntAct Interaction AC, IMEx ID, plus UniProt pair normalization and publication/taxon context | Complex-vs-binary projection, physical-vs-genetic mixing, spoke-expansion lineage loss, directionality loss | Sometimes for full evidence text, feature spans, or native-complex context |
| Structure to protein | PDB ID + entity/chain/assembly + SIFTS spans to UniProt; AlphaFold accession/checksum/modelEntityId to UniProt | Chain renumbering, missing residues, AU vs biological assembly confusion, predicted vs experimental conflation | Sometimes for mmCIF, validation, map, PAE, or chain-mapping payloads |
| Ligand linkage | BindingDB Reactant_set_id / MonomerID + InChIKey/SMILES; RCSB CCD IDs + complex context; Reactome ChEBI IDs | Target-sequence mismatch in BindingDB, partial/covalent ligands in structures, weak chemistry authority in pathway sources | Often for assay text, full TSV rows, portal pages, or selected chemical annotations |
| Motif / pathway / disorder enrichment | UniProt accession + residue span + source accession: `IPRxxxxx`, `PSxxxxx`, `PDOCxxxxx`, `PRUxxxxx`, `ELME#####`, DisProt region_id, Reactome stable ID | Integrated vs unintegrated ambiguity, motif degeneracy, disorder-type conflation, inferred pathway events | Often for long motif tables, instance pages, pathway payloads, or HTML-only annotations |

## Protein Identity Linkage

### Canonical rule

Every protein-bearing source should be normalized through **UniProt accession first**.

That means:

- UniProt is the canonical protein row.
- Secondary accessions are aliases and historical continuity, not alternate primary IDs.
- Isoform identifiers stay separate from the base accession.
- Sequence version and sequence hash should be retained when exact rebuilds matter.
- Taxon should be carried alongside accession because several sources are organism-sensitive.

### Source-specific identity behavior

- **UniProt** is the authoritative identity backbone and provides the cleanest accession-first join.
- **RCSB/PDBe** resolves proteins through SIFTS-style mapping. The best join is `pdb_id + entity_id + chain_id + residue span -> UniProt accession`.
- **AlphaFold DB** joins best through UniProt accession, then `sequenceChecksum`, `entryId`, and `modelEntityId` for exact provenance.
- **BindingDB** joins by UniProt accession when available, but the source warns that target sequences can differ from the experimental construct. That means accession joins are strong, but sequence-equivalence joins are only safe when organism and sequence identity are explicitly validated.
- **BioGRID** and **IntAct** both support UniProt-based normalization, but they also carry gene IDs, symbols, and aliases. Those other namespaces are useful for lookup, not for identity authority.
- **InterPro**, **PROSITE**, **ELM**, and **DisProt** all depend on UniProt accession plus residue spans for meaningful attachment.
- **Reactome** uses UniProt reference-entity mappings for protein participation and should be joined through accession, not through display names.
- **EMDB/EMICSS** can expose UniProt accessions at the sample level, but those are ancillary links attached to a map-centric entry.

### Confidence tiers

- **High confidence**: UniProt accession to UniProt accession, or direct accession-based joins into RCSB, AlphaFold, DisProt, InterPro, and Reactome.
- **High confidence with validation**: BindingDB accession joins when the target sequence and organism are explicitly verified.
- **Lossy but usable**: joins that start from gene names, symbols, synonyms, or replacement history and then resolve to UniProt.
- **Weak**: accession-less joins that rely only on display names, especially when multiple organisms or isoforms are possible.

## Pair / Interactor Linkage

### BioGRID

BioGRID is the best broad **pairwise interaction evidence** layer in the current slice. The high-confidence join is:

- `BioGRID Interaction ID` for the evidence row.
- UniProt accession for each interactor when present.
- Entrez Gene ID, BioGRID ID, and taxon as supporting resolution fields.

The key loss modes are:

- physical and genetic interactions live in the same download family and must not be merged.
- self-interactions and reciprocal records can both appear.
- symbols and aliases are not unique.

### IntAct

IntAct is the strongest curated **protein-protein interaction** source here, but it must be handled carefully because the portal can display **binary projections of native complexes**.

High-confidence join path:

- `Interaction AC` and `IMEx ID` when present.
- UniProtKB accession for participants.
- organism, detection method, interaction type, confidence, and feature spans.

Main loss mode:

- a displayed binary pair may actually have been expanded from an n-ary complex, so the native-complex lineage must be preserved.

### Reactome

Reactome can support interaction-like summaries, but it is **not** a direct PPI authority.

Useful joins:

- Reactome stable ID plus UniProt participation.
- Complex membership and reaction context.

Loss mode:

- inferred human events and complex-member-derived interaction files should be treated as context or weak supervision, not as direct binding evidence.

### BindingDB

BindingDB is not a PPI source. It is a **protein-ligand interaction source**.

Its join value for pairwise work is limited to:

- target protein accession.
- assay row identity.
- ligand identity and provenance.

If a downstream object needs protein-protein linkage, BindingDB should not be projected into that role.

### Confidence tiers for pair linkage

- **High confidence**: BioGRID and IntAct when joined by their interaction identifiers plus UniProt participants.
- **Medium confidence**: Reactome complex-context projections.
- **Low confidence**: alias-only or symbol-only interactor matching.
- **Not valid**: treating BindingDB as a PPI authority.

## Structure To Protein Linkage

### Experimental structure

RCSB/PDBe is the authoritative structure source.

Best join path:

- `pdb_id`
- `entity_id`
- `assembly_id`
- `chain identifiers`
- residue ranges
- SIFTS mapping spans
- UniProt accession

Important implementation rule:

- do not collapse biological assembly and asymmetric unit into one object.
- keep chain-level and entity-level identity separate.
- preserve unresolved residues and renumbering ambiguity.

This is the strongest structure-to-protein join in the stack and should be treated as the default when experimental coordinates exist.

### Predicted structure

AlphaFold DB is a parallel predicted layer, not a replacement for RCSB/PDBe.

Best join path:

- UniProt accession first.
- `sequenceChecksum` for exact-sequence provenance.
- `entryId` and `modelEntityId` for source-native instance tracking.

Important implementation rule:

- never merge predicted and experimental coordinates into one canonical coordinate object.

### EMDB

EMDB is map-centric and only indirectly protein-linked.

Best joins:

- EMDB accession to PDB IDs and EMPIAR where present.
- UniProt accessions from EMICSS or related mapping layers.

Loss mode:

- sample names are not stable keys.
- map-level evidence should stay attached to a protein or complex anchor, not used as the anchor itself.

### Confidence tiers for structure linkage

- **High confidence**: RCSB/PDBe `pdb_id + entity/chain + SIFTS span -> UniProt`.
- **High confidence, predicted**: AlphaFold accession/checksum mapping.
- **Moderate**: EMDB-to-protein joins via EMICSS or linked PDB context.
- **Lossy**: any structure join that ignores assembly state, chain mapping, or missing-residue spans.

## Ligand Linkage

### Strong ligand sources

- **BindingDB** is the authoritative ligand-assay source here.
- **RCSB/PDBe** contributes ligand identity through CCD/component IDs and structure context.
- **Reactome** contributes ChEBI-linked small-molecule context, but not chemical assay authority.

### Join rules

- For BindingDB, the safest ligand join is `Reactant_set_id` or `MonomerID`, backed by InChIKey/SMILES.
- For structures, use CCD/component IDs and keep covalent or partial occupancy context visible.
- For pathway context, use ChEBI as a semantic link, not as an assay substitute.

### Loss modes

- BindingDB target sequences may differ from the assayed construct.
- structure-bound ligands can be partial, solvent-like, or covalent.
- pathway small molecules are context, not measurement-grade chemistry.

### Confidence tiers for ligand linkage

- **High confidence**: BindingDB row-level ligand joins and canonical chemical identifiers.
- **Medium confidence**: RCSB ligand joins when the component ID and structure context are retained.
- **Contextual only**: Reactome ChEBI links.

## Motif, Pathway, And Disorder Enrichment

### InterPro

InterPro is the safest umbrella layer for protein family/domain/site enrichment.

Best joins:

- `IPRxxxxx`
- UniProt accession
- residue span
- member-signature provenance
- taxon

Loss modes:

- integrated vs unintegrated signatures are not equivalent.
- source signature type must be preserved because representative selection depends on it.

### PROSITE

PROSITE is the precise sequence-motif layer.

Best joins:

- `PDOCxxxxx`, `PSxxxxx`, `PRUxxxxx`
- UniProt accession
- motif span

Loss modes:

- a non-match is not evidence of absence.
- page-level documentation and full instance tables may need supplemental capture.

### ELM

ELM is the short-linear-motif and partner-context layer.

Best joins:

- `ELME#####`
- UniProt accession
- motif instance coordinates
- organism and evidence count
- partner/domain hints when available

Loss modes:

- motif degeneracy is high.
- many motifs only become meaningful with disorder, phosphorylation, or partner-domain context.
- full instance tables and documentation may require portal capture.

### DisProt

DisProt is the curated disorder layer.

Best joins:

- UniProt accession
- `disprot_id`
- `region_id`
- residue span
- term/evidence identifiers

Loss modes:

- disorder-state, disorder-transition, and disorder-function are different annotations and must not be collapsed.
- absence of annotation is not a negative label.
- records can carry `uniprot_changed`, so accession normalization is required.

### Reactome

Reactome is the pathway and complex-context layer.

Best joins:

- Reactome stable ID
- versioned stable ID
- UniProt accession
- species context
- pathway ancestry

Loss modes:

- inferred human events should not be treated as direct human evidence.
- complex membership and reaction context are not interchangeable.

### RCSB motif search / structural motif tools

RCSB motif tools are structure-linked retrieval layers.

Best joins:

- query fingerprint or motif query
- PDB / chain / entity / residue context
- UniProt mapping

Loss modes:

- this is retrieval-first, not a curated function authority.
- the result set is often only recoverable through the UI or selected payload capture.

### Confidence tiers for enrichment linkage

- **High confidence**: UniProt + residue span + accessioned annotation source.
- **Moderate**: pathway or structural motif context that is accessioned but not directly evidence-bearing.
- **Low / contextual**: any enrichment inferred from a related source without residue-level mapping.

## Main Unresolved Or Lossy Joins

1. **Gene names, symbols, and aliases are not canonical keys**. They are lookup aids only, especially across BioGRID, IntAct, BindingDB, and DisProt.
2. **BindingDB target sequences are not guaranteed to match the assayed construct**. The accession join is strong, but exact sequence provenance must be validated when the analysis depends on residue-level correctness.
3. **IntAct native complexes can be flattened into binary projections**. If the lineage is not preserved, the join becomes lossy.
4. **BioGRID mixes physical and genetic interaction evidence**. That type field must survive every projection.
5. **Reactome inferred human events are not direct experimental evidence**. They are useful context, but the source is not a substitute for direct assay or structure evidence.
6. **AlphaFold predictions must remain separate from experimental coordinates**. Sequence identity can align them, but the evidence class is different.
7. **EMDB sample-component joins are weak unless they are backed by EMICSS or PDB context**. Sample names are not stable identifiers.
8. **Motif and portal-based enrichment often needs supplemental scraping or curated payload capture**. This is especially true for long instance tables, documentation pages, and selected search-result payloads.
9. **DisProt absence is not a negative label**. Missing coverage is a coverage gap, not proof of order.

## Implementation Posture

The practical join order should be:

1. Normalize protein identity to UniProt.
2. Attach experimental structure through RCSB/PDBe or predicted structure through AlphaFold DB.
3. Add interaction evidence from BioGRID, IntAct, or BindingDB according to whether the record is pairwise PPI or protein-ligand.
4. Add motif, disorder, and pathway enrichment as separate annotation objects keyed by accession and residue span.
5. Preserve every source-native identifier and every ambiguity flag.

That ordering keeps the canonical protein record stable while allowing the platform to attach evidence-rich layers without collapsing the source semantics.

