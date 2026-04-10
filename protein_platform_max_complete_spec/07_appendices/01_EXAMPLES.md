# Example Object Instances and Pseudocode Sketches

## Example ComplexRecord (conceptual)
complex_id_internal: cx_000123
complex_type: protein_ligand
structure_source: rcsb
structure_id: 1ABC
assembly_id: 1
member_chain_ids:
  - ch_00001
member_ligand_ids:
  - lg_00451
biologically_relevant_flag: unknown
relevance_confidence: 0.62

## Example DAG
source_acquire_rcsb -> raw_validate_rcsb -> normalize_structures -> map_to_uniprot
-> feature_extract_structure
source_acquire_bindingdb -> raw_validate_bindingdb -> normalize_assays -> map_assays_to_targets
feature_extract_sequence/evolution
feature_extract_biology
dataset_build -> split_generate -> model_train -> model_validate -> calibrate -> export

## Pseudocode: conflict-aware assay aggregation
1. group by target-ligand normalized pair and measurement type
2. standardize units
3. discard impossible parsed values to conflict table, not trash
4. compute aggregates only if explicit policy chosen
5. emit aggregate plus references to constituent measurements
