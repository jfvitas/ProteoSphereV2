# Split Post-Staging Gate Check Preview

- Status: `complete`
- Stage ID: `cv_fold_export_unlock_gate_check`
- Stage shape: `post_staging_gate_check`
- Today output: `blocked report only`
- Gate status: `open`
- CV fold export unlocked: `True`

## Staging Parity

- Staging status: `complete`
- Staging validation status: `aligned`
- Dry-run validation status: `aligned`
- Candidate rows: `1889`
- Assignment count: `1889`

## Blocked Reasons


## Truth Boundary

- This post-staging gate check preview revalidates the staging handoff against the fold-export gate. It remains run-scoped and, when fold materialization exists, reflects the executed non-committing export.
