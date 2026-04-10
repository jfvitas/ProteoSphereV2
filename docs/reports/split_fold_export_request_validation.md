# Split Fold Export Request Validation

- Status: `aligned`
- Stage status: `complete`
- Gate status: `open`
- Candidate rows: `1889`
- Assignment count: `1889`

## Matches

- `stage_id`
- `stage_shape`
- `today_status`
- `recipe_id`
- `input_artifact`
- `linked_group_count`
- `candidate_row_count`
- `assignment_count`
- `gate_stage_id`
- `gate_status`
- `staging_status`
- `post_staging_validation_status`
- `live_gate_status`
- `live_candidate_row_count`
- `live_assignment_count`
- `live_split_group_counts`
- `live_row_level_split_counts`
- `status`
- `run_scoped_only`
- `blocked`
- `cv_fold_export_unlocked`
- `cv_folds_materialized`
- `final_split_committed`
- `gate_validation_issue_count`

## Truth Boundary

- This validation checks the blocked run-scoped fold-export request preview against the post-staging gate check and split-engine input surfaces. It accepts either the blocked request state or a fulfilled run-scoped fold materialization state.
