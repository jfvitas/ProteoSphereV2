# P73 Duplicate Cleanup Small Batch Execution Readiness Contract

This report-only contract defines the smallest safe execution-readiness bar for a gated small-batch duplicate cleanup step.

## Current Boundary

The cleanup stack is still report-only and delete-disabled:

- [`artifacts/status/duplicate_cleanup_executor_status.json`](D:/documents/ProteoSphereV2/artifacts/status/duplicate_cleanup_executor_status.json)
- [`artifacts/status/duplicate_cleanup_status.json`](D:/documents/ProteoSphereV2/artifacts/status/duplicate_cleanup_status.json)
- [`artifacts/status/duplicate_cleanup_dry_run_plan.json`](D:/documents/ProteoSphereV2/artifacts/status/duplicate_cleanup_dry_run_plan.json)
- [`artifacts/status/p70_duplicate_cleanup_small_batch_preflight.json`](D:/documents/ProteoSphereV2/artifacts/status/p70_duplicate_cleanup_small_batch_preflight.json)
- [`runs/real_data_benchmark/full_results/operator_dashboard.json`](D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/operator_dashboard.json)

The operator dashboard is still `no-go` and `blocked_on_release_grade_bar`, so the cleanup step is not yet executable.

## Smallest Safe Batch

The smallest safe batch is exactly one removal action from `same_release_local_copy_duplicates`.

Current exemplar:

- keep `data\raw\local_copies\raw\rcsb\5I25.json`
- remove `data\raw\local_copies\raw_rcsb\5I25.json`
- reclaim `3116` bytes
- require exact SHA-256 match
- require no protected paths, no partial paths, and no latest-surface rewrites

This exemplar is only a plan anchor. A real mutation must regenerate the plan against the then-current inventory before it can be approved.

## Readiness Conditions

The next gated batch can only become executable if all of these hold:

1. A mutation-authorizing executor path exists.
1. The approval boundary is recorded and frozen.
1. The plan is regenerated against the current inventory.
1. The keeper/removal pair still matches exactly by SHA-256.
1. No protected, partial, unresolved, or latest-surface path can be touched.
1. The post-mutation verification contract is ready.
1. Rollback visibility is defined.

## What Still Blocks Execution

- No mutation-authorizing executor path exists yet.
- The current executor remains report-only and delete-disabled.
- The approval boundary for destructive cleanup is not recorded.
- The approved plan must be regenerated against the then-current inventory before any mutation.
- The operator dashboard remains no-go.

## Grounding

- [`artifacts/status/p70_duplicate_cleanup_small_batch_preflight.json`](D:/documents/ProteoSphereV2/artifacts/status/p70_duplicate_cleanup_small_batch_preflight.json)
- [`artifacts/status/duplicate_cleanup_dry_run_plan.json`](D:/documents/ProteoSphereV2/artifacts/status/duplicate_cleanup_dry_run_plan.json)
- [`artifacts/status/duplicate_cleanup_executor_status.json`](D:/documents/ProteoSphereV2/artifacts/status/duplicate_cleanup_executor_status.json)
- [`artifacts/status/duplicate_cleanup_status.json`](D:/documents/ProteoSphereV2/artifacts/status/duplicate_cleanup_status.json)
- [`artifacts/status/p69_duplicate_cleanup_post_mutation_verification_contract.json`](D:/documents/ProteoSphereV2/artifacts/status/p69_duplicate_cleanup_post_mutation_verification_contract.json)
- [`runs/real_data_benchmark/full_results/operator_dashboard.json`](D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/operator_dashboard.json)
