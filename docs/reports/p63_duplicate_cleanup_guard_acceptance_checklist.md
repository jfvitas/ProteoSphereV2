# P63 Duplicate Cleanup Guard Acceptance Checklist

This report-only note turns the P62 mutation-guard design into a concise acceptance checklist for any future non-dry-run duplicate cleanup executor.

## Current Boundary

The present duplicate cleanup path is still report-only, delete-disabled, and not mutation-authorized:

- [artifacts/status/p62_duplicate_cleanup_mutation_guard_design.json](/D:/documents/ProteoSphereV2/artifacts/status/p62_duplicate_cleanup_mutation_guard_design.json)
- [artifacts/status/p61_duplicate_cleanup_authorization_handoff.json](/D:/documents/ProteoSphereV2/artifacts/status/p61_duplicate_cleanup_authorization_handoff.json)
- [artifacts/status/duplicate_cleanup_executor_status.json](/D:/documents/ProteoSphereV2/artifacts/status/duplicate_cleanup_executor_status.json)
- [artifacts/status/duplicate_cleanup_dry_run_plan.json](/D:/documents/ProteoSphereV2/artifacts/status/duplicate_cleanup_dry_run_plan.json)
- [artifacts/status/duplicate_cleanup_status.json](/D:/documents/ProteoSphereV2/artifacts/status/duplicate_cleanup_status.json)

The safe-first boundary remains unchanged:

- exact SHA-256 matching
- no protected paths
- no partial or unresolved paths
- no latest-surface rewrites
- allowed cohorts only

## Acceptance Checklist

### 1. Authorization Exists

A future destructive executor is acceptable only if it has a separate mutation authorization record.

Pass criteria:

- explicit approval for destructive cleanup exists
- approval binds to one frozen plan identity
- approval binds to one executor path and run context
- the report-only executor is not being reused as mutation authority

### 2. Snapshot Parity Holds

The approved inventory, status, and plan snapshot must still match the run inputs.

Pass criteria:

- inventory summary parity passes
- status summary shape parity passes
- approved plan identity matches the staged plan
- any drift forces regeneration and re-approval

### 3. Cohorts Are Locked

Mutation must stay inside the approved duplicate cohorts.

Pass criteria:

- allowlist matches exactly
- no cohort widening at runtime
- no ad hoc duplicate-class promotion
- no mutation outside the approved cohorts

### 4. Paths Are Exact

The executor may only touch approved removal paths.

Pass criteria:

- every removal path is an exact approved member
- no traversal outside the target roots
- no path normalization that broadens scope
- no symlink, rename, or move escape

### 5. Pairings Are Proven

Duplicate identity must be exact before any mutation.

Pass criteria:

- keeper/removal files match by SHA-256
- pairings match the approved plan
- no inferred duplicate relationship
- no best-effort matching

### 6. Protected Surfaces Stay Immutable

Protected, partial, and latest surfaces must remain untouched.

Pass criteria:

- protected paths remain immutable
- partial or unresolved paths stay excluded
- latest surfaces remain untouched
- any protected-surface touch aborts the run

### 7. Budget Stays Bounded

The destructive run must stay within the approved action and byte budget.

Pass criteria:

- action count stays within the approved plan
- reclaimable-byte total stays within the approved plan
- batch and run ceilings are both enforced
- no silent expansion of the removal set

### 8. Failure Handling Is Safe

The executor must stop cleanly if a guard fails.

Pass criteria:

- batch operations are atomic where possible
- partial mutation triggers immediate abort
- already-applied changes are rolled back or captured in recovery evidence
- no continued processing after a safety violation

### 9. Verification and Audit Exist

The executor must prove the result and preserve traceability.

Pass criteria:

- refreshed inventory is captured after mutation
- duplicate counts change only as predicted
- protected and latest surfaces remain untouched
- audit output records approval id, executor id, source hashes, and path deltas

## What Is Still Blocking

This checklist is not yet passable because:

- there is no mutation-authorizing executor path yet
- the current executor remains report-only and delete-disabled
- the destructive approval boundary is not recorded
- the approved plan must be regenerated against the then-current inventory before any mutation

## Bottom Line

Treat this as the acceptance gate for a future destructive cleanup executor, not as permission to run one now. Until every item above passes, the current duplicate cleanup stack remains report-only.
