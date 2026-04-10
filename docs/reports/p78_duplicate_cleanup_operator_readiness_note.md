# P78 Duplicate Cleanup Operator Readiness Note

Report-only readiness note for the current small-batch duplicate cleanup path.

## Current State

The preview is ready, but the path is still blocked:

- the executor remains `report_only_no_delete`
- the first execution preview is `not_yet_executable_today`
- the operator dashboard is still `blocked_on_release_grade_bar`
- operator go/no-go is still `no-go`

## First Small-Batch Preview

The smallest previewed batch remains:

- batch size limit: `1`
- batch shape: one exact-match removal action from `same_release_local_copy_duplicates`
- exemplar keeper: `data\raw\local_copies\raw\rcsb\5I25.json`
- exemplar removal: `data\raw\local_copies\raw_rcsb\5I25.json`
- reclaimable bytes: `3116`

## What Still Remains Before Any Mutation Could Be Considered

1. A separate destructive cleanup authorization record must exist.
2. The authorization must bind the frozen plan identity, executor path, and run context.
3. The live snapshot must still match the approved plan at execution time.
4. The batch must remain exactly one approved removal action.
5. The keeper/removal SHA-256 pairing must remain exact.
6. Protected, partial, unresolved, and latest surfaces must remain untouched.
7. Rollback and audit visibility must be ready before the first removal starts.
8. Post-mutation verification must be defined and capture-ready.

## What Still Blocks Today

- The current executor is still report-only and delete-disabled.
- The operator dashboard still reads `no-go`.
- The dashboard still reports `blocked_on_release_grade_bar`.
- The mutation authority is still separate from the preview.

## Bottom Line

The path stays blocked today. The preview gives us the exact first batch shape, but no small-batch mutation should be considered until authorization exists, the dashboard is unblocked, and execution-time snapshot parity is proven.
