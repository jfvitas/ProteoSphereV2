# Split Fold Export Gate Preview

- Gate ID: `cv_fold_export_unlock_gate`
- Gate surface: `split_engine_input_preview`
- Status: `open_run_scoped_materialized`
- Required unlock conditions: `4`

## Validation Snapshot

- Dry-run validation status: `aligned`
- Dry-run issue count: `0`
- Match count: `7`
- Candidate rows: `1889`
- Assignment count: `1889`

## Execution Snapshot

- Next unlocked stage: `split_fold_export_materialized`
- Fold export ready: `True`
- CV folds materialized: `True`
- Final split committed: `False`

## Blocked Reasons


## Truth Boundary

- This preview makes the current fold-export boundary explicit. The dry-run split chain is aligned, and when a run-scoped fold export materialization exists it is treated as the authoritative unlock without promoting a release split.
