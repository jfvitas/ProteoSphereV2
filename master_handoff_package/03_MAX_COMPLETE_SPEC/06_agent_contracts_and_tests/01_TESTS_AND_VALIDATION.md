# Tests and Validation Plan

## Unit tests
Connectors:
- parser correctness
- retry behavior
- schema validation
Normalization:
- mapping correct for exact match
- ambiguous mapping preserved as ambiguous
- conflict resolution policies honored
Features:
- each calculator produces expected shape/type
- missingness masks emitted
- units/aggregation verified
Models:
- forward pass shape tests
- masking behavior
- uncertainty head positivity/validity checks where relevant
Training:
- loss decreases on tiny synthetic sanity set
- checkpoint save/load roundtrip
Execution:
- DAG topological order
- retry transitions
- checkpoint resume

## Integration tests
- source -> canonical object pipeline on sample records
- canonical -> features -> dataset build
- dataset -> split -> train -> eval
- lineage query retrieves raw source ancestry

## System tests
- end-to-end dry run on miniature sample project
- failure injection during feature extraction with successful resume
- schema version bump invalidates stale downstream artifacts
- experiment reproducibility with fixed seed and same environment

## Leakage checks
- overlapping sequence clusters across train/test are flagged
- identical ligands or near-duplicate pockets across forbidden splits are flagged where configured
- same complex/assay duplicates across split boundaries are flagged

## Diagnostics required
- feature missingness report
- source coverage report
- conflict burden report
- split leakage report
- calibration report for uncertainty-enabled models
