# P61 Duplicate Cleanup Authorization Handoff

This report-only note turns the current duplicate cleanup dry-run and executor surfaces into an authorization handoff.

## Current State

The live executor is validated, report-only, and delete-disabled:

- [artifacts/status/duplicate_cleanup_executor_status.json](/D:/documents/ProteoSphereV2/artifacts/status/duplicate_cleanup_executor_status.json)
- [artifacts/status/duplicate_cleanup_dry_run_plan.json](/D:/documents/ProteoSphereV2/artifacts/status/duplicate_cleanup_dry_run_plan.json)
- [artifacts/status/duplicate_cleanup_status.json](/D:/documents/ProteoSphereV2/artifacts/status/duplicate_cleanup_status.json)

The current no-delete path is safe to review because validation passed on the shared core fields, the allowed cohorts stayed safe-first, and protected or partial paths were excluded.

## Preconditions

Before any non-dry-run cleanup is even considered, the following must still be true:

1. the executor remains `report_only_no_delete`
1. `delete_enabled` remains false
1. latest surfaces remain untouched
1. the allowed cohorts remain exactly `local_archive_equivalents`, `same_release_local_copy_duplicates`, and `seed_vs_local_copy_duplicates`
1. protected and partial paths remain out of the staged removal set
1. the inventory and status summaries still agree on the core fields

## Safety Gates

The cleanup boundary must keep these gates green:

- exact SHA-256 matches for every staged duplicate pairing
- no protected paths in the removal set
- no partial or unresolved paths in the removal set
- no latest-surface rewrites
- no move, rename, or delete side effects in the report-only executor path

## Explicit Approval Required For Non-Dry-Run Cleanup

A non-dry-run cleanup would need explicit approval for all of the following:

- a separate mutation-authorizing executor path
- a fresh post-drift inventory/status refresh
- a new destructive-plan review that is separate from the dry-run plan
- explicit confirmation that protected and latest surfaces are still immutable under the destructive path
- explicit confirmation that the allowed cohort boundary is not being widened
- explicit authorization to delete or move raw storage

Without that approval, the executor must stay in report-only mode.

## What Still Blocks Destructive Cleanup

Destructive cleanup remains blocked because:

- there is no mutation-authorizing executor yet
- the current executor is explicitly no-delete
- the plan is only staged as a report
- the approval boundary for destructive cleanup has not been recorded
- inventory drift would require plan regeneration before any further trust

## Metrics That Matter Most

The handoff should watch:

- `action_count`: 100
- `planned_reclaimable_bytes`: 3928198
- `duplicate_group_count`: 42339
- `duplicate_file_count`: 130460
- `reclaimable_file_count`: 87513
- `reclaimable_bytes`: 100930747119
- `partial_file_count`: 9
- `protected_file_count`: 2

Secondary metrics:

- `validation.status`: passed
- `truth_boundary.report_only`: true
- `truth_boundary.delete_enabled`: false
- `truth_boundary.latest_surfaces_mutated`: false

## Bottom Line

The current executor can be trusted as a report-only duplicate cleanup handoff. It cannot be used for destructive cleanup until a separate mutation-authorizing approval exists and the plan is regenerated against the then-current inventory.
