# P77 Duplicate Cleanup Post-Preview Guard Checklist

Report-only post-preview mutation guard checklist for duplicate cleanup.

## Current Boundary

The live cleanup stack is still report-only and delete-disabled:

- [`artifacts/status/p76_duplicate_cleanup_first_execution_checklist.json`](D:/documents/ProteoSphereV2/artifacts/status/p76_duplicate_cleanup_first_execution_checklist.json)
- [`artifacts/status/duplicate_cleanup_executor_status.json`](D:/documents/ProteoSphereV2/artifacts/status/duplicate_cleanup_executor_status.json)
- [`artifacts/status/duplicate_cleanup_status.json`](D:/documents/ProteoSphereV2/artifacts/status/duplicate_cleanup_status.json)
- [`runs/real_data_benchmark/full_results/operator_dashboard.json`](D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/operator_dashboard.json)

The operator dashboard is still `no-go` and `blocked_on_release_grade_bar`, so the post-preview mutation path remains closed today.

## What This Guard Is For

This checklist is the post-preview barrier between the first authorized execution shape and any actual destructive mutation.

It should only pass if the preview boundary stays frozen, a separate mutation authorization exists, the dashboard no longer blocks release-grade execution, and the live snapshot still matches the approved plan.

## Checklist

### 1. The preview boundary stays frozen

Pass only if the p76 first-authorized execution shape remains a one-action exact-match removal and the report-only preview stack does not widen.

### 2. Mutation authorization is separate and explicit

Pass only if the destructive cleanup authorization is distinct from the report-only executor and binds the frozen plan identity, executor path, and run context.

### 3. The operator dashboard is no longer blocked

Pass only if the dashboard is no longer `blocked_on_release_grade_bar`, `ready_for_release` is true, and operator go/no-go is no longer `no-go`.

### 4. Snapshot parity still holds

Pass only if inventory, status, and plan snapshots still align at execution time and any drift forces re-approval before mutation.

### 5. Path and identity safety remain exact

Pass only if the keeper/removal pair is exact by SHA-256 and the removal path is an exact approved member of the plan.

### 6. Protected surfaces remain immutable

Pass only if protected, partial, unresolved, and latest surfaces remain untouched.

### 7. Rollback and audit are visible

Pass only if the run has a known recovery target and capture-ready audit fields before the first removal starts.

### 8. Post-mutation verification is defined

Pass only if the refreshed inventory, removed-file count, reclaimed bytes, and audit trail can be reconciled exactly after mutation.

## What Still Blocks Today

- The current executor is still report-only and delete-disabled.
- The operator dashboard still reads `no-go`.
- The dashboard still reports `blocked_on_release_grade_bar`.
- The mutation authorization boundary is still separate from the preview.

## Bottom Line

This checklist is ready, but not yet passable today. Keep the cleanup path report-only until the dashboard no longer blocks release-grade execution and the mutation authority is explicit.
