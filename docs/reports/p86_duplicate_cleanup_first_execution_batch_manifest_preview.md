# Duplicate Cleanup First Execution Batch Manifest Preview

- Status: `report_only`
- Batch manifest status: `preview_frozen_not_authorized`
- Execution status: `not_yet_executable_today`
- Batch size limit: `1`
- Cohort: `same_release_local_copy_duplicates`
- Action count in frozen plan: `100`

## Frozen Action

- Keeper: `data\raw\local_copies\raw\rcsb\5I25.json`
- Removal: `data\raw\local_copies\raw_rcsb\5I25.json`
- SHA-256: `00001ec3860210cc78ffa8606b2f316a2bfe4d6130988446c79ffa3b74e7fa00`
- Reclaimable bytes: `3116`

## Validation

- Validation status: `passed`
- `first_action_matches_exemplar`: `passed`
- `executor_boundary_still_report_only`: `passed`
- `cohort_lock_preserved`: `passed`
- `protected_surface_guards_present`: `passed`

## Truth Boundary

- Report only: `True`
- Delete enabled: `False`
- Latest surfaces mutated: `False`
- Mutation allowed: `False`
- Next required state: `mutation_authorization_and_frozen_batch_approval`
