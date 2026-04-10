# Full System Spec

## 1. Platform mission
Build a domain-specific ML operating system for biomolecular modeling that can ingest heterogeneous
sources, canonicalize conflicting data, compute rich multimodal features, train multiple model families,
support hybrid pipelines, quantify uncertainty, and expose robust workflows through a GUI and APIs.

The platform must support:
- proteins in isolation
- protein–ligand systems
- protein–protein systems
- protein–nucleic-acid systems
- multimodal fusion across structure, sequence, evolution, motifs, pathway context, assay metadata, and confidence

## 2. Non-negotiable design principles
1. Canonicalization before modeling.
2. Provenance attached to every imported and derived object.
3. No silent overwrite of source conflicts.
4. Missing data is not zero; missingness must be explicit.
5. Data quality and biological relevance are first-class signals.
6. Model families are pluggable; backend abstractions are mandatory.
7. GUI option exposure must be conditional and schema-driven.
8. Leakage-aware splits and dataset diversity controls are mandatory.
9. Noise-robustness is part of the architecture, not an afterthought.
10. Execution must be resumable, debuggable, and reproducible.

## 3. System layers
### Layer A: Source acquisition
Connectors for primary databases, bulk downloads, APIs, and controlled enrichment services.

### Layer B: Canonical data system
Normalize IDs, map chains to proteins, represent complexes, resolve conflicts, preserve provenance.

### Layer C: Feature processing
Compute structural, biophysical, interaction, ligand, motif, evolutionary, pathway, and uncertainty features.

### Layer D: Model platform
Support tree models, neural networks, GNNs, transformers, hybrid ensembles, uncertainty heads, multitask heads.

### Layer E: Training + evaluation
Curriculum, active data filtering, AutoML, distributed training, leakage-safe splits, quality-aware metrics.

### Layer F: Execution engine
DAG scheduling, checkpointing, retries, resource assignment, lineage, caching, and batch orchestration.

### Layer G: User-facing layer
GUI, API, experiment registry, artifact export, model registry, visualization, and interpretability tools.

## 4. Core use cases
1. Predict affinity or interaction score for a protein–ligand complex.
2. Predict whether two proteins are likely to interact and how credible the prediction is.
3. Build graph representations at atom or residue level, or both.
4. Enrich structures with motifs, disorder, domain, pathway, and evolutionary annotations.
5. Train on multiple modalities and use gating/attention to identify the most informative signals.
6. Compare alternative model families under standardized evaluation and provenance tracking.
7. Surface all configurable options through a dynamic GUI without hardcoding hidden assumptions.

## 5. Production expectations
- Must support local workstation use and future scaling to larger multi-GPU or cluster environments.
- Must preserve backend flexibility (PyTorch now, TensorFlow/JAX optional, additional backends possible).
- Must support plugin registration for new models, feature calculators, and source connectors.
- Must generate reusable data caches and versioned datasets.
- Must support resumability after failure at both task and pipeline level.
