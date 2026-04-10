# Split Fold Export Staging Validation

- Status: `aligned`
- Stage status: `complete`
- Gate status: `open`
- Candidate rows: `1889`
- Assignment count: `1889`
- Dry-run issue count: `0`

## Matches

- `stage_id`
- `surface_id`
- `gate_id`
- `gate_surface`
- `gate_status`
- `candidate_row_count`
- `assignment_count`
- `split_group_counts`
- `row_level_split_counts`
- `largest_groups`
- `blocked_reasons`
- `validation_status`
- `dry_run_validation_status`
- `dry_run_issue_count`
- `input_assignment_count`
- `input_candidate_row_count`
- `staging_status`
- `run_scoped_only`
- `blocked`
- `cv_fold_export_unlocked`
- `cv_folds_materialized`
- `final_split_committed`

## Blocked Reasons


## Truth Boundary

- This validation checks that the scoped fold-export staging preview stays aligned with the contract, the gate preview, and the split-engine input preview. It accepts either the blocked staging state or a completed run-scoped fold materialization state.
