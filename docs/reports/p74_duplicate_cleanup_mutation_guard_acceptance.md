# P74 Duplicate Cleanup Mutation Guard Acceptance

Report-only acceptance checklist for the next mutation-guard step beyond the small-batch readiness contract.

## Current Boundary

The duplicate cleanup stack is still report-only and delete-disabled:

- [`artifacts/status/duplicate_cleanup_executor_status.json`](D:/documents/ProteoSphereV2/artifacts/status/duplicate_cleanup_executor_status.json)
- [`artifacts/status/duplicate_cleanup_status.json`](D:/documents/ProteoSphereV2/artifacts/status/duplicate_cleanup_status.json)
- [`artifacts/status/duplicate_cleanup_dry_run_plan.json`](D:/documents/ProteoSphereV2/artifacts/status/duplicate_cleanup_dry_run_plan.json)
- [`artifacts/status/p73_duplicate_cleanup_small_batch_execution_readiness_contract.json`](D:/documents/ProteoSphereV2/artifacts/status/p73_duplicate_cleanup_small_batch_execution_readiness_contract.json)

The current plan still has `100` actions and the live executor remains `report_only_no_delete`, so the mutation path is not yet open.

## Small-Batch Basis

The smallest acceptable mutation batch remains exactly one action from `same_release_local_copy_duplicates`.

Current exemplar:

- keep `data\raw\local_copies\raw\rcsb\5I25.json`
- remove `data\raw\local_copies\raw_rcsb\5I25.json`
- reclaim `3116` bytes
- require exact SHA-256 match
- require no protected paths, no partial paths, and no latest-surface rewrites

That exemplar is only a readiness anchor. A real mutation must re-check the live inventory before it can be approved.

## Acceptance Checklist

### 1. Separate mutation authorization exists

Pass only if there is an explicit destructive cleanup approval tied to one frozen plan identity, one executor path, and one run context.

### 2. The batch is frozen at one exact removal action

Pass only if the batch contains exactly one approved removal action, matches the small-batch exemplar, and stays inside `same_release_local_copy_duplicates`.

### 3. Snapshot parity still holds

Pass only if inventory, status, and plan snapshots still align and any drift forces regeneration and re-approval.

### 4. Path safety is exact

Pass only if the keeper/removal pair is exact, the removal path is approved, and no normalization, symlink, rename, or move can broaden scope.

### 5. Cohorts remain locked

Pass only if the cohort allowlist matches exactly and no cohort widening or duplicate-class promotion appears at runtime.

### 6. Protected surfaces stay immutable

Pass only if protected, partial, unresolved, and latest surfaces remain untouched.

### 7. Rollback visibility exists before execution

Pass only if the recovery target is known and the run would produce a visible recovery artifact or rollback note on failure.

### 8. Post-mutation verification is ready

Pass only if the refreshed inventory, removed-file count, reclaimed bytes, and audit trail can be reconciled exactly after the mutation.

## What Still Blocks Acceptance

- No mutation-authorizing executor path exists yet.
- The current executor remains report-only and delete-disabled.
- The approval boundary for destructive cleanup is still missing.
- The approved plan still needs regeneration against the then-current inventory.

## Bottom Line

This checklist is ready, but it is not yet passable. The next real step remains a single-action exact-match batch only after mutation authorization exists, the batch is frozen, and snapshot parity is refreshed.
