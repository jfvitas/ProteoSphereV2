# Split Engine Dry Run Validation

- Status: `aligned`
- Recipe ID: `protein_spine_first_split_recipe_v1`
- Candidate rows: `1889`
- Assignment rows: `1889`

## Matches

- `recipe_input_artifact`
- `candidate_row_count`
- `assignment_count`
- `assignment_vs_simulation_count`
- `split_group_counts`
- `row_level_split_counts`
- `largest_group_order`

## Truth Boundary

- This validation checks parity across the current split-engine input, assignment preview, and simulation preview. It does not commit folds or promote a release split.
