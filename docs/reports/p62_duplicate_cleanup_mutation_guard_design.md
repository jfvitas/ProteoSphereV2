# P62 Duplicate Cleanup Mutation Guard Design

This report-only note designs the mutation-time guards that a future non-dry-run duplicate cleanup executor would need.

## Starting Point

The current duplicate cleanup surfaces are still report-only and delete-disabled:

- [artifacts/status/p61_duplicate_cleanup_authorization_handoff.json](/D:/documents/ProteoSphereV2/artifacts/status/p61_duplicate_cleanup_authorization_handoff.json)
- [artifacts/status/duplicate_cleanup_executor_status.json](/D:/documents/ProteoSphereV2/artifacts/status/duplicate_cleanup_executor_status.json)
- [artifacts/status/duplicate_cleanup_dry_run_plan.json](/D:/documents/ProteoSphereV2/artifacts/status/duplicate_cleanup_dry_run_plan.json)
- [artifacts/status/duplicate_cleanup_status.json](/D:/documents/ProteoSphereV2/artifacts/status/duplicate_cleanup_status.json)

Those artifacts already establish the safe-first boundary:

- exact SHA-256 matching
- no protected paths
- no partial or unresolved paths
- no latest-surface rewrites
- report-only executor behavior

## Required Mutation Guards

### 1. Authorization Guard

A non-dry-run executor must bind to a separate mutation authorization record. The current handoff is not enough by itself.

Minimum requirements:

- explicit approval for destructive cleanup
- approval tied to a frozen plan identity
- approval tied to a specific executor path and run context
- no reuse of the report-only executor as an implicit mutation authority

### 2. Snapshot Parity Guard

The mutation executor must verify that inventory, status, and approved plan still match the same snapshot boundary.

Minimum requirements:

- inventory summary hash or checksum matches the approved snapshot
- cleanup status summary shape matches the approved snapshot
- approved plan identity matches the staged plan
- any drift forces regeneration and a new approval

### 3. Cohort Boundary Guard

Mutation must stay within the approved cohorts only.

Minimum requirements:

- exact cohort allowlist match
- no cohort widening at execution time
- no ad hoc promotion of other duplicate classes
- no mutation outside the approved duplicate cleanup cohorts

### 4. Path Safety Guard

The executor must only act on exact approved removal paths.

Minimum requirements:

- every removal path is an exact member of the approved plan
- no traversal outside the target roots
- no path normalization that broadens scope
- no symlink, rename, or move escape to a non-approved surface

### 5. Identity Guard

The duplicate pairing must be proven before any mutation.

Minimum requirements:

- exact SHA-256 agreement for keeper and removal files
- keeper/removal pairing matches the approved plan
- no inferred duplicate relationship
- no best-effort matching

### 6. Protected Surface Guard

Mutation must fail closed around protected, partial, and latest surfaces.

Minimum requirements:

- protected paths remain immutable
- partial or unresolved paths remain excluded
- latest surfaces remain untouched
- any protected-surface touch aborts the run

### 7. Budget Guard

The executor must not exceed the approved removal budget.

Minimum requirements:

- action count stays within the approved plan
- reclaimable-byte total stays within the approved plan
- batch-level and run-level ceilings are both enforced
- no silent expansion of the removal set

### 8. Atomicity and Rollback Guard

The destructive path needs explicit failure handling.

Minimum requirements:

- batch operations are atomic where possible
- partial mutation triggers immediate abort
- already-applied changes are either rolled back or captured in a recovery record
- no continued processing after a safety violation

### 9. Post-Mutation Verification Guard

The executor must prove the filesystem matches the approved outcome after mutation.

Minimum requirements:

- refreshed inventory after mutation
- duplicate counts change only as predicted
- protected and latest surfaces remain untouched
- audit output records the observed delta

### 10. Audit Trail Guard

Every destructive action must be reconstructable.

Minimum requirements:

- approval record id is captured
- executor identity is captured
- source artifact hashes are captured
- action log records the before/after path set
- failures are traceable back to the exact guard that stopped them

## What Still Blocks a Non-Dry-Run Executor

The following remain blocking conditions today:

- there is no mutation-authorizing executor path yet
- the current executor is explicitly report-only and delete-disabled
- the approval boundary for destructive cleanup is not recorded
- the approved plan must be regenerated against the then-current inventory before any mutation
- the current dry-run surfaces are not enough to authorize raw storage deletion

## What This Design Unlocks Later

If these guards are implemented, a future executor can safely do three things:

- delete only exact approved duplicates
- keep protected and latest surfaces immutable
- produce a verifiable post-mutation audit record

## Bottom Line

The current duplicate cleanup stack is ready for review, not mutation. A future non-dry-run executor needs explicit approval, snapshot parity, exact path safety, identity checks, protected-surface exclusion, budget enforcement, rollback handling, post-mutation verification, and a complete audit trail before it can touch raw storage.
