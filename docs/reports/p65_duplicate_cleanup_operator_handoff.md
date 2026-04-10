# P65 Duplicate Cleanup Operator Handoff

This report-only note hands the duplicate cleanup stack to an operator with the minimum safety prerequisites visible. It is grounded in the current report-only executor status and the P62-P64 guard chain.

## Current State

The executor is still report-only and delete-disabled:

- [artifacts/status/duplicate_cleanup_executor_status.json](/D:/documents/ProteoSphereV2/artifacts/status/duplicate_cleanup_executor_status.json)
- [artifacts/status/p64_duplicate_cleanup_post_mutation_verification_contract.json](/D:/documents/ProteoSphereV2/artifacts/status/p64_duplicate_cleanup_post_mutation_verification_contract.json)
- [artifacts/status/p63_duplicate_cleanup_guard_acceptance_checklist.json](/D:/documents/ProteoSphereV2/artifacts/status/p63_duplicate_cleanup_guard_acceptance_checklist.json)
- [artifacts/status/p62_duplicate_cleanup_mutation_guard_design.json](/D:/documents/ProteoSphereV2/artifacts/status/p62_duplicate_cleanup_mutation_guard_design.json)

The current boundary is still:

- report-only
- delete-disabled
- latest-surface safe
- safe-first cohorts only

## Operator-Safe Execution Prerequisites

Before any future non-dry-run cleanup is even considered, the operator must verify:

1. a separate mutation authorization exists
1. the approved plan identity matches the staged plan
1. inventory, status, and plan snapshots still align
1. protected and partial paths remain excluded
1. latest surfaces remain untouched
1. the approved cohort allowlist has not widened
1. the run has a defined rollback or recovery record path

## Safe Execution Shape

If a future destructive executor is ever approved, the operator-facing flow should stay small:

- preload the approved snapshot and run context
- validate the frozen plan against the current inventory
- execute only approved removal paths
- stop immediately on any guard failure
- record a post-mutation inventory and audit trail

## Rollback Visibility

Rollback must be visible before the run starts, not discovered after damage.

Required visibility:

- the recovery target for the run is known
- the executor records which changes were applied before failure
- the operator can see whether a batch was fully applied or aborted
- any partial mutation produces a recovery artifact or rollback note
- failures are traceable to the exact guard that blocked progress

## What Still Blocks Destructive Cleanup

Destructive cleanup is still blocked because:

- no mutation-authorizing executor path exists yet
- the current executor remains report-only and delete-disabled
- the approval boundary for destructive cleanup is not recorded
- the approved plan must be regenerated against the then-current inventory before any mutation

## Metrics That Matter Most

The operator should watch:

- `action_count`
- `planned_reclaimable_bytes`
- `duplicate_group_count`
- `duplicate_file_count`
- `reclaimable_file_count`
- `reclaimable_bytes`
- `partial_file_count`
- `protected_file_count`

Secondary visibility:

- validation status
- truth boundary flags
- cohort allowlist stability
- post-mutation inventory parity

## Bottom Line

The current duplicate cleanup executor is safe to review as a report-only handoff. It is not yet safe to mutate, and any future destructive path needs explicit authorization, snapshot parity, rollback visibility, and post-mutation verification before it can touch raw storage.
