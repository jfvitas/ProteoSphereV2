# Source-by-Source Acquisition and Compatibility Matrix

## Priority backbone sources
- RCSB PDB / PDBe
- UniProt
- AlphaFold DB
- BindingDB
- InterPro
- DisProt
- BioGRID
- IntAct
- EMDB (advanced)
- motif search systems / structural motif engines
- Reactome
- evolutionary/MSA-derived sources and pipelines

## 1. RCSB / PDBe
Primary role:
- structural coordinates
- chains/entities/assemblies
- ligands and chemical components
- experimental method, resolution, quality metadata
- residue/position mappings where available

Use for:
- atom/residue graph construction
- assembly extraction
- protein–ligand / protein–protein / protein–NA structure retrieval
- confidence and quality features

Missing/weak:
- direct broad assay labels
- curated disorder truth
- broad systems-biology context
- universal biological relevance labels for all contacts

## 2. UniProt
Primary role:
- canonical sequence identity
- protein metadata
- taxonomy
- cross-references
- function annotations

Use for:
- identity spine
- sequence normalization
- joining to InterPro, AlphaFold, disorder, pathways, etc.

Missing/weak:
- 3D geometry
- complex state
- assay-linked coordinates

## 3. AlphaFold DB
Primary role:
- predicted structures
- confidence metrics such as pLDDT/PAE-style confidence layers depending on access path

Use for:
- fill structure gaps
- single-chain structural features
- confidence-aware predicted structure use

Missing/weak:
- bound-state truth
- complex assembly truth
- direct assay labels
- full disorder truth

## 4. BindingDB
Primary role:
- ligand-target assay measurements

Use for:
- large assay layer
- chemical diversity
- target-ligand measurement integration

Missing/weak:
- exact structure linkage
- assay harmonization complexity
- chain-specific geometry

## 5. InterPro / motif/domain family resources
Primary role:
- domains
- families
- important sites
- motif-level annotations

Use for:
- domain architecture features
- family-aware split grouping
- motif annotations

## 6. DisProt / disorder resources
Primary role:
- curated intrinsic disorder / region annotations

Use for:
- IDR/IDP labeling
- uncertainty-aware structural interpretation
- disorder masks

## 7. BioGRID / IntAct
Primary role:
- interaction evidence
- literature-backed interaction context

Use for:
- physical/genetic interaction priors
- PPI evidence layer
- contextual features

Missing/weak:
- geometry
- structure-linked affinity at scale

## 8. EMDB
Primary role:
- cryo-EM map and experimental context

Use for:
- advanced modality-aware quality features
- cryo-EM confidence and heterogeneity signals

## 9. RCSB motif search / 3D motif tools
Primary role:
- sequence motif search
- 3D local motif search

Use for:
- motif similarity retrieval
- local structural motif matching
- pocket/site similarity features

## 10. SiteMotif-style local binding site motif methods
Primary role:
- derive sequence-order-independent local structural motifs of binding sites

Use for:
- binding pocket motif clustering
- local site architecture descriptors
- motif-based similarity between unrelated proteins

## 11. MegaMotifBase-style conserved structural motif resources
Primary role:
- conserved family/superfamily core motifs

Use for:
- optional enrichment of structurally conserved motif labels

## 12. Reactome / pathway resources
Primary role:
- pathway membership
- reaction roles
- systems-biology context
- functional network relationships

Use for:
- pathway overlap features
- pathway distance / graph embeddings
- functional relevance priors
- pathway-aware multitask learning

## 13. Evolutionary resources and pipelines
Primary role:
- conservation
- MSA statistics
- co-evolution
- family relationships

Use for:
- residue conservation scores
- interface conservation
- co-evolving residue features
- family-aware dataset controls

## Source join policy summary
protein identity backbone:
- UniProt-centered
structure observation layer:
- RCSB/PDBe and AlphaFold
assay layer:
- BindingDB and structure-linked assay datasets where available
annotation layer:
- InterPro, disorder, motif tools, Reactome
evidence layer:
- BioGRID, IntAct
advanced modality layer:
- EMDB
