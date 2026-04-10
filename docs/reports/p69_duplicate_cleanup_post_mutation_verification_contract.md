# P69 Duplicate Cleanup Post-Mutation Verification Contract

This report-only note defines the minimum validation that any future duplicate cleanup action beyond dry-run must satisfy after it mutates files.

## Current Boundary

The live cleanup stack is still report-only and delete-disabled:

- [artifacts/status/duplicate_cleanup_executor_status.json](/D:/documents/ProteoSphereV2/artifacts/status/duplicate_cleanup_executor_status.json)
- [artifacts/status/p68_duplicate_cleanup_execution_readiness_note.json](/D:/documents/ProteoSphereV2/artifacts/status/p68_duplicate_cleanup_execution_readiness_note.json)
- [artifacts/status/duplicate_cleanup_status.json](/D:/documents/ProteoSphereV2/artifacts/status/duplicate_cleanup_status.json)
- [runs/real_data_benchmark/full_results/operator_dashboard.json](/D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/operator_dashboard.json)

The safe-first boundary still means:

- exact SHA-256 matching
- no protected paths
- no partial or unresolved paths
- no latest-surface rewrites
- allowed cohorts only

The operator dashboard is a non-target surface. It currently remains `no-go` and `blocked_on_release_grade_bar`, and cleanup verification must not treat it as a mutation target.

## Minimum Post-Mutation Verification

### 1. Refresh the inventory

Rebuild or re-read the inventory immediately after the run.

Required proof:

- refreshed inventory snapshot exists
- post-mutation counts are captured
- observed counts are compared to the approved pre-mutation snapshot

### 2. Reconcile the approved delta

The observed cleanup result must match the approved plan exactly.

Required proof:

- removed-file count matches the approved action count
- reclaimed bytes match the approved byte budget
- every approved removal path is accounted for
- no extra paths disappear

### 3. Preserve protected and latest surfaces

Cleanup must not touch protected, partial, unresolved, or latest surfaces.

Required proof:

- protected paths remain present and unchanged
- partial or unresolved paths remain present and unchanged
- latest surfaces remain untouched
- no protected-surface deletion or rewrite occurred

### 4. Preserve cohort boundaries

The run must stay within the approved duplicate cohorts only.

Required proof:

- only approved cohorts show changes
- no cohort widening appears in the observed delta
- the result stays within the frozen approval set

### 5. Preserve unrelated operator surfaces

The cleanup run must not rewrite or reclassify the operator dashboard or other non-target operator surfaces.

Required proof:

- the operator dashboard artifact remains unchanged
- the dashboard remains `no-go`
- the dashboard remains `blocked_on_release_grade_bar`
- no cleanup output is written into the benchmark operator surface

### 6. Capture audit evidence

Every destructive action must leave a reconstructable trace.

Required proof:

- approval record id is recorded
- executor id and run context are recorded
- source artifact hashes are recorded
- before/after path sets are recorded
- observed delta is recorded in a machine-readable artifact

### 7. Fail closed on drift

Any mismatch between the approved plan and the observed result is a failure, not a warning.

Required proof:

- inventory drift rejects the result
- status-summary drift rejects the result
- plan drift rejects the result
- partial success is not accepted as completion

## What Success Requires

A future non-dry-run duplicate cleanup action is acceptable only if the post-mutation evidence proves:

- the approved files were removed and nothing else was removed
- protected and latest surfaces stayed immutable
- the operator dashboard stayed untouched and still reports `no-go`
- the observed cleanup delta matches the approved plan
- the audit trail is sufficient to reconstruct the run

## What Still Blocks Acceptance Today

This contract is not yet satisfiable because:

- no mutation-authorizing executor path exists yet
- the current executor remains report-only and delete-disabled
- the approval boundary for destructive cleanup is not recorded
- the approved plan must be regenerated against the then-current inventory before any mutation

## Bottom Line

The minimum post-mutation bar is exact delta reconciliation, protected-surface preservation, operator-surface preservation, and auditability. If any of those fail, the run must be rejected.
