# P76 Duplicate Cleanup First Execution Checklist

Report-only checklist for the first authorized duplicate cleanup execution.

## Current Boundary

The live cleanup stack is still report-only and delete-disabled:

- [`artifacts/status/duplicate_cleanup_status.json`](D:/documents/ProteoSphereV2/artifacts/status/duplicate_cleanup_status.json)
- [`artifacts/status/duplicate_cleanup_executor_status.json`](D:/documents/ProteoSphereV2/artifacts/status/duplicate_cleanup_executor_status.json)
- [`artifacts/status/p74_duplicate_cleanup_mutation_guard_acceptance.json`](D:/documents/ProteoSphereV2/artifacts/status/p74_duplicate_cleanup_mutation_guard_acceptance.json)
- [`artifacts/status/p61_duplicate_cleanup_authorization_handoff.json`](D:/documents/ProteoSphereV2/artifacts/status/p61_duplicate_cleanup_authorization_handoff.json)

That means this checklist is not authorization. It is the first-run bar to use after authorization exists.

## First Authorized Execution Shape

- batch size: `1`
- cohort: `same_release_local_copy_duplicates`
- exemplar removal: `data\raw\local_copies\raw_rcsb\5I25.json`
- exemplar keeper: `data\raw\local_copies\raw\rcsb\5I25.json`
- exact SHA-256 match required

## Checklist

### 1. Mutation authorization exists

Pass only if there is a separate destructive cleanup authorization record that binds the executor path, run context, and frozen plan identity.

### 2. The first batch is frozen

Pass only if the first run contains exactly one approved removal action and matches the small-batch exemplar.

### 3. The live snapshot still matches

Pass only if inventory and status parity still hold at execution time and any drift forces re-approval before mutation.

### 4. Path and identity safety are exact

Pass only if the keeper/removal SHA-256 match is exact and the removal path is an exact approved member of the plan.

### 5. Protected surfaces stay immutable

Pass only if protected, partial, unresolved, and latest surfaces remain untouched.

### 6. Rollback and audit are visible

Pass only if the run has a known recovery target and capture-ready audit fields before the first removal starts.

### 7. Post-mutation verification is defined

Pass only if the refreshed inventory, removed-file count, reclaimed bytes, and audit trail can be reconciled exactly after the first action.

## What Still Blocks Today

- No mutation-authorizing executor exists yet.
- The current executor is still report-only and delete-disabled.
- The approval boundary for destructive cleanup is still missing.
- The plan must be regenerated against the live inventory before any real mutation.

## Bottom Line

Use this checklist only when authorization exists. Until then, the first execution remains not yet executable, even though the safe one-action batch shape is already known.
