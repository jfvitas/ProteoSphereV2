# Split Fold Export Gate Validation

- Status: `aligned`
- Gate status: `open_run_scoped_materialized`
- Candidate rows: `1889`
- Assignment count: `1889`
- Dry-run issue count: `0`

## Matches

- `dry_run_validation_status`
- `candidate_row_count`
- `assignment_count`
- `split_group_counts`
- `row_level_split_counts`
- `largest_groups`
- `execution_candidate_row_count`
- `execution_assignment_count`
- `cv_folds_materialized`
- `final_split_committed`
- `cv_fold_export_unlocked`
- `ready_for_fold_export`
- `blocked_reasons`

## Blocked Reasons


## Truth Boundary

- This validation checks parity between the fold-export gate preview and the current split-engine input and dry-run validation surfaces. It accepts either the blocked pre-materialization state or a completed run-scoped fold export materialization.
