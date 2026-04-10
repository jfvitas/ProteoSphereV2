# Split Post-Staging Gate Check Validation

- Status: `aligned`
- Stage status: `complete`
- Gate status: `open`
- Candidate rows: `1889`
- Assignment count: `1889`

## Matches

- `stage_id`
- `stage_shape`
- `today_output`
- `gate_id`
- `gate_surface`
- `gate_status`
- `fold_export_ready`
- `staging_status`
- `staging_validation_status`
- `dry_run_validation_status`
- `candidate_row_count`
- `assignment_count`
- `split_group_counts`
- `row_level_split_counts`
- `largest_groups`
- `input_assignment_count`
- `input_candidate_row_count`
- `status`
- `run_scoped_only`
- `cv_fold_export_unlocked`
- `blocked`
- `staging_validation_issue_count`
- `gate_validation_issue_count`
- `matches_staging_assignment_count`
- `matches_staging_candidate_row_count`

## Truth Boundary

- This validation checks the post-staging gate-check preview against the current staging and split-input surfaces. It accepts either the blocked gate-check state or a completed run-scoped fold materialization state.
