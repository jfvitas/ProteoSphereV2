# Extraction Plans by System Type

## 1. Protein-only objects
Extract:
- all structural features
- sequence/evolution features
- motif/domain/disorder/pathway annotations
- confidence/quality summaries
Use cases:
- embedding generation
- family clustering
- structure-function pretraining
- mutation-effect support later

## 2. Protein–ligand systems
Extract additionally:
- ligand standardized chemistry
- protein-ligand contact maps
- pocket geometry
- interaction fingerprints
- assay labels where available
- pose/relevance confidence
Derived targets:
- affinity regression
- interaction classification
- pocket similarity
- site motif learning

## 3. Protein–protein systems
Extract additionally:
- inter-chain contact maps
- interface composition
- symmetry/oligomerization features
- evidence-layer priors from interaction DBs
- interface conservation
Potential labels:
- binary interaction
- affinity where available
- interface hotspot prediction

## 4. Protein–nucleic-acid systems
Extract additionally:
- NA type
- sequence and modification information where available
- protein–NA contact maps
- groove/stacking interaction proxies
- base-specific contacts
Potential labels:
- binding/nonbinding
- interface characterization
- motif specificity analysis

## 5. Multi-component mixed assemblies
Preserve explicit component graph, do not flatten away member identity.
