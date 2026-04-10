# P67 Duplicate Cleanup Gated Execution Order

This report-only note defines the exact precondition order that must be satisfied before any future non-dry-run duplicate cleanup executor may start.

## Current Boundary

The live executor is still report-only and delete-disabled:

- [artifacts/status/duplicate_cleanup_executor_status.json](/D:/documents/ProteoSphereV2/artifacts/status/duplicate_cleanup_executor_status.json)
- [artifacts/status/p66_duplicate_cleanup_preview_authorization_matrix.json](/D:/documents/ProteoSphereV2/artifacts/status/p66_duplicate_cleanup_preview_authorization_matrix.json)
- [artifacts/status/p65_duplicate_cleanup_operator_handoff.json](/D:/documents/ProteoSphereV2/artifacts/status/p65_duplicate_cleanup_operator_handoff.json)

The safe-first boundary still means:

- exact SHA-256 matching
- no protected paths
- no partial or unresolved paths
- no latest-surface rewrites
- allowed cohorts only

## Execution Order

### Step 1: Verify the report-only preview state

Confirm the current executor is still report-only, delete-disabled, and aligned to the live dry-run plan.

Required proof:

- executor status is `report_only_no_delete`
- validation status is passed
- current plan and cleanup status still align

### Step 2: Produce or confirm the preview authorization bucket

Confirm the preview path is in the report-only or verified-preview bucket, not the mutation bucket.

Required proof:

- preview authorization matrix exists
- preview artifact identity is frozen
- no destructive action is implied

### Step 3: Require explicit mutation authorization

Do not proceed unless there is a separate mutation approval record.

Required proof:

- explicit destructive cleanup approval exists
- approval binds to one frozen plan identity
- approval binds to one executor path and run context

### Step 4: Recheck snapshot parity

Inventory, status, and plan snapshots must still match the approved boundary.

Required proof:

- inventory summary parity passes
- status summary shape parity passes
- approved plan identity matches the staged plan
- any drift forces regeneration and re-approval

### Step 5: Lock the cohort boundary

The executor may only operate on the approved duplicate cohorts.

Required proof:

- allowlist matches exactly
- no cohort widening at runtime
- no ad hoc duplicate-class promotion
- no mutation outside the approved cohorts

### Step 6: Freeze protected surfaces

Protected, partial, and latest surfaces must be confirmed immutable before any mutation can start.

Required proof:

- protected paths remain immutable
- partial or unresolved paths stay excluded
- latest surfaces remain untouched
- any protected-surface touch aborts the run

### Step 7: Establish rollback visibility

The operator must know how a partial run would be recorded and recovered before the run starts.

Required proof:

- recovery target is known
- applied changes are logged
- partial mutation produces a recovery artifact or rollback note
- failures are traceable to the exact blocking guard

### Step 8: Confirm post-mutation verification is available

The run must have a verification target ready before mutation starts.

Required proof:

- refreshed inventory will be captured after mutation
- approved delta will be reconciled exactly
- audit evidence will include approval id, executor id, source hashes, and path deltas

### Step 9: Start mutation only if every prior gate passes

Destructive cleanup may start only after the preceding steps are satisfied in order.

Required proof:

- no gate is skipped
- no gate is downgraded to advisory
- no path mutates until the full chain is green

## What Still Blocks Destructive Cleanup

Destructive cleanup is still blocked because:

- no mutation-authorizing executor path exists yet
- the current executor remains report-only and delete-disabled
- the approval boundary for destructive cleanup is not recorded
- the approved plan must be regenerated against the then-current inventory before any mutation

## Bottom Line

The correct order is report-only preview, explicit mutation authorization, snapshot parity, cohort lock, protected-surface freeze, rollback visibility, post-mutation verification, and only then execution. Anything less keeps the stack in report-only mode.
