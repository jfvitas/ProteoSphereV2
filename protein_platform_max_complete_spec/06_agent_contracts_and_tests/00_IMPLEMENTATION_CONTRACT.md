# Coding-Agent Implementation Contract

## Absolute requirements
1. Implement schemas as typed objects or structured validation models.
2. Do not invent hidden assumptions not represented in config/schema.
3. Do not silently drop conflicting data.
4. Do not collapse missing into zero unless explicitly configured.
5. Do not bypass provenance.
6. Do not hardcode model-specific GUI logic outside schema/registry systems.
7. Do not skip “advanced” modules because they are hard.
8. Provide tests for each major subsystem before declaring completion.

## Required repository module map
/core
  canonical_models/
  provenance/
  config/
  registry/
/connectors
  rcsb/
  uniprot/
  alphafold/
  bindingdb/
  interpro/
  disprot/
  biogrid/
  intact/
  emdb/
  motif/
  reactome/
  evolution/
/normalization
  mapping/
  conflict_resolution/
/features
  atoms/
  residues/
  interfaces/
  ligands/
  sequence/
  evolution/
  motif/
  biology/
  quality/
/datasets
  builders/
  splitters/
/models
  tree/
  dense/
  cnn/
  sequence/
  graph/
  fusion/
  uncertainty/
  multitask/
/training
  trainer/
  schedulers/
  losses/
  callbacks/
/evaluation
  metrics/
  calibration/
  leakage_checks/
  diagnostics/
/execution
  dag/
  scheduler/
  resources/
  caching/
  checkpointing/
/gui
  schema_binding/
  views/
/api
  routes/
  serializers/
/tests
  unit/
  integration/
  system/

## Definition of done
- connectors run and create versioned raw artifacts
- canonicalization produces valid typed objects with provenance
- feature extraction populates declared schema with masks/confidence
- at least one baseline and one flagship multimodal model train end-to-end
- leakage-safe evaluation runs
- DAG execution resumes from checkpoint after simulated failure
- GUI/API load schemas dynamically
