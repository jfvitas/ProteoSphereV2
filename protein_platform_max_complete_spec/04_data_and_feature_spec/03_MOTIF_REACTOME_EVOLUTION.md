# Motifs, Pathways, and Evolution: How They Factor In

## 1. Motif layer
Motif resources and methods answer different questions:
- conserved family core motifs
- local structural motif recurrence
- site/pocket motif similarity
- sequence motif presence

Required platform behavior:
- treat motif information as both annotation and retrieval primitive
- allow motif presence/absence as features
- allow motif similarity scores as derived features
- allow local motif match confidence
- allow motif-based clustering of sites

## 2. Reactome/pathway layer
Pathways are not geometry, but they are functional context.
Use Reactome-style data to compute:
- pathway membership vectors
- shared pathway count
- pathway overlap ratio
- shortest-path distance in pathway graph
- pathway role compatibility (same reaction, regulator/substrate/catalyst patterns)
- pathway graph embeddings
- pathway-context priors for interaction plausibility

Use cases:
- improve biological realism
- negative sampling constraints
- multitask prediction with functional relevance
- interpretability

## 3. Evolution layer
Evolutionary information is one of the strongest anti-noise signals available.
Required evolutionary features:
- MSA-derived conservation per position
- entropy
- co-evolution / coupling scores
- family/superfamily assignments
- domain architecture
- sequence cluster identifiers
- optional phylogenetic distance summaries

Required uses:
- residue weighting
- interface reliability
- split grouping to reduce leakage
- multi-view fusion with structure
- missing-dimension compensation when structures alone are insufficient
