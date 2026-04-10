# 00 Master Index

## Package purpose
This package specifies a full professional version of the platform, not a starter prototype.

## Section map

### 01_full_system_spec
Single-document systems overview and non-negotiable design principles.

### 02_ml_platform_spec
ML model families, hyperparameters, architecture-builder options, fusion patterns, training system,
AutoML, evaluation, GUI controls, backend abstraction, and plugin rules.

### 03_execution_and_canonical_data_spec
Canonical entities, source normalization, ID mapping, conflict resolution, DAG scheduler, task lifecycle,
checkpointing, retries, recovery, resource management, provenance, lineage, and reproducibility.

### 04_data_and_feature_spec
Data-source acquisition matrix, feature ontology, extraction plans for proteins / ligands / PPIs / PNAs,
motifs, disorder, pathway context, evolutionary context, and scraping/API enrichment strategy.

### 05_model_noise_robustness_spec
How to design models that find signal in noisy, incomplete, heterogeneous data:
multimodal encoders, cross-modal attention, gating, uncertainty, curriculum, data-centric safeguards,
multi-task learning, and confidence-aware training.

### 06_agent_contracts_and_tests
Strict implementation rules, required module layout, forbidden shortcuts, validation steps,
unit/integration/system tests, and completion criteria.

### 07_appendices
Glossary, naming conventions, example object instances, example DAG, and implementation sequence.

## Delivery intent
This bundle should be treated as the master technical handoff for coding agents.
