# P70 Duplicate Cleanup Small Batch Preflight

This report-only note defines the preflight for the first genuinely executable tiny duplicate-cleanup batch beyond dry-run.

## Current Boundary

The live cleanup stack is still report-only and delete-disabled:

- [artifacts/status/duplicate_cleanup_executor_status.json](/D:/documents/ProteoSphereV2/artifacts/status/duplicate_cleanup_executor_status.json)
- [artifacts/status/duplicate_cleanup_status.json](/D:/documents/ProteoSphereV2/artifacts/status/duplicate_cleanup_status.json)
- [artifacts/status/p69_duplicate_cleanup_post_mutation_verification_contract.json](/D:/documents/ProteoSphereV2/artifacts/status/p69_duplicate_cleanup_post_mutation_verification_contract.json)
- [runs/real_data_benchmark/full_results/operator_dashboard.json](/D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/operator_dashboard.json)

The operator dashboard is still `no-go` and `blocked_on_release_grade_bar`, so the stack is not yet ready to mutate.

## Tiny Batch Definition

The first genuinely executable tiny batch must be the smallest approved subset of the existing dry-run plan that can be mutated safely under the current guard chain.

Required shape:

- exactly one approved removal action
- exact SHA-256 match between keeper and removal
- one approved duplicate cohort only
- no protected paths
- no partial or unresolved paths
- no latest-surface rewrites

## Preflight Checks

### 1. Executor boundary

Confirm the executor is still the report-only dry-run surface before any mutation attempt.

Pass criteria:

- executor status remains `report_only_no_delete`
- validation remains passed
- no mutation-capable path is implied by the preflight

### 2. Batch identity

Confirm the tiny batch is frozen before execution.

Pass criteria:

- batch identity is frozen
- batch contains exactly one action
- action identity matches the approved plan

### 3. Path safety

Confirm the batch only touches an exact approved removal path.

Pass criteria:

- keeper/removal pair is exact
- removal path is in the approved plan
- no path normalization broadens scope
- no symlink, rename, or move escape is possible

### 4. Surface protection

Confirm protected and latest surfaces are untouched.

Pass criteria:

- protected paths remain immutable
- partial or unresolved paths remain excluded
- latest surfaces remain untouched
- any protected-surface touch aborts the run

### 5. Cohort lock

Confirm the batch stays in one approved cohort only.

Pass criteria:

- cohort allowlist matches exactly
- no cohort widening at runtime
- no ad hoc duplicate-class promotion
- no mutation outside the approved cohort

### 6. Post-mutation verification readiness

Confirm the verification contract is available before mutation starts.

Pass criteria:

- refreshed inventory will be captured after mutation
- removed-file count and reclaimed bytes will be reconciled exactly
- operator dashboard will remain unchanged and still report `no-go`
- audit evidence will include approval id, executor id, source hashes, and path deltas

### 7. Rollback visibility

Confirm rollback handling is visible before the run starts.

Pass criteria:

- recovery target is known
- applied changes will be logged
- partial mutation will produce a recovery artifact or rollback note
- failures will be traceable to the exact blocking guard

## What Still Blocks Execution

The batch is not yet executable because:

- no mutation-authorizing executor path exists yet
- the current executor remains report-only and delete-disabled
- the approval boundary for destructive cleanup is not recorded
- the approved plan must be regenerated against the then-current inventory before any mutation
- the operator dashboard remains `no-go`

## Bottom Line

This preflight is ready as a report-only contract, but the first tiny batch is not yet executable. Once the mutation authorization exists and the live dashboard still preserves the no-go boundary, a one-action exact-match batch is the smallest safe starting point.
