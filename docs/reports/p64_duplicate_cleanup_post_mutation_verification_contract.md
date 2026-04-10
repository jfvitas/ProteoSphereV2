# P64 Duplicate Cleanup Post-Mutation Verification Contract

This report-only note defines the minimum verification contract that any future non-dry-run duplicate cleanup executor must satisfy after it mutates files.

## Current Boundary

The present cleanup path is still report-only and delete-disabled:

- [artifacts/status/p63_duplicate_cleanup_guard_acceptance_checklist.json](/D:/documents/ProteoSphereV2/artifacts/status/p63_duplicate_cleanup_guard_acceptance_checklist.json)
- [artifacts/status/p62_duplicate_cleanup_mutation_guard_design.json](/D:/documents/ProteoSphereV2/artifacts/status/p62_duplicate_cleanup_mutation_guard_design.json)
- [artifacts/status/p61_duplicate_cleanup_authorization_handoff.json](/D:/documents/ProteoSphereV2/artifacts/status/p61_duplicate_cleanup_authorization_handoff.json)
- [artifacts/status/duplicate_cleanup_executor_status.json](/D:/documents/ProteoSphereV2/artifacts/status/duplicate_cleanup_executor_status.json)
- [artifacts/status/duplicate_cleanup_dry_run_plan.json](/D:/documents/ProteoSphereV2/artifacts/status/duplicate_cleanup_dry_run_plan.json)
- [artifacts/status/duplicate_cleanup_status.json](/D:/documents/ProteoSphereV2/artifacts/status/duplicate_cleanup_status.json)

The safe-first boundary still means:

- exact SHA-256 matching
- no protected paths
- no partial or unresolved paths
- no latest-surface rewrites
- allowed cohorts only

## Minimum Post-Mutation Verification Contract

### 1. Refresh the Inventory

The executor must rebuild or re-read the inventory immediately after mutation.

Required checks:

- refreshed inventory is captured after the run
- refreshed counts are compared to the approved pre-mutation snapshot
- any unexpected file, path, or count delta is treated as a failure

### 2. Reconcile the Approved Delta

The observed cleanup result must match the approved plan exactly.

Required checks:

- observed removed-file count matches the approved action count
- observed reclaimable-byte reduction matches the approved byte budget
- every approved removal path is accounted for
- no extra paths disappear

### 3. Preserve Protected and Latest Surfaces

Post-mutation state must prove the guard rails were respected.

Required checks:

- protected paths remain present and unchanged
- partial or unresolved paths remain present and unchanged
- latest surfaces remain untouched
- no protected-surface deletion or rewrite occurred

### 4. Preserve Cohort Boundaries

The run must not mutate beyond the approved cohorts.

Required checks:

- only approved cohorts show changes
- no cohort widening appears in the observed delta
- the resulting cleanup surface stays within the frozen approval set

### 5. Preserve Identity Proof

The run must still be explainable by exact duplicate identity.

Required checks:

- keeper/removal SHA-256 relationships remain the same as approved
- no post-mutation mismatch appears between the approved pairing and the final state
- any identity mismatch aborts acceptance

### 6. Capture Audit Evidence

The run must leave a reconstructable record.

Required checks:

- approval record id is recorded
- executor id and run context are recorded
- source artifact hashes are recorded
- before/after path sets are recorded
- observed delta is recorded in a machine-readable artifact

### 7. Fail Closed on Drift

Any mismatch between the approved plan and the observed result is a failure, not a warning.

Required checks:

- inventory drift causes rejection of the mutation result
- status-summary drift causes rejection of the mutation result
- plan drift causes rejection of the mutation result
- partial success is not accepted as completion

## Acceptance Standard

A future non-dry-run executor is acceptable only if the post-mutation verification proves that:

- the approved files were removed and nothing else was removed
- protected and latest surfaces stayed immutable
- the observed cleanup delta matches the approved plan
- the audit trail is sufficient to reconstruct the run

## What Still Blocks Acceptance Today

This contract is not yet satisfiable because:

- there is no mutation-authorizing executor path yet
- the current executor remains report-only and delete-disabled
- the approved destructive boundary is not recorded
- the approved plan must be regenerated against the then-current inventory before any mutation

## Bottom Line

This is the minimum post-mutation verification bar for a future destructive duplicate cleanup executor. If the refreshed inventory, observed delta, and audit trail do not all line up, the run must be rejected.
