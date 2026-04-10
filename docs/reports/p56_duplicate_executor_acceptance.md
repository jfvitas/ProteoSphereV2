# P56 Duplicate Executor Acceptance

- Artifact: `p56_duplicate_executor_acceptance`
- Status: `report_only`
- Generated at: `2026-04-01T11:38:43.6210002-05:00`
- Executor path: `scripts/export_duplicate_cleanup_dry_run_plan.py`
- Mode: `no_delete_dry_run_acceptance`

This sidecar turns the P55 validation checklist into an acceptance gate for the no-delete duplicate cleanup executor path. It is still report-only. It does not authorize deletion, rename, move, or any manifest rewrite.

## What It Builds On

- [p55_duplicate_validation_checklist.json](D:/documents/ProteoSphereV2/artifacts/status/p55_duplicate_validation_checklist.json)
- [duplicate_cleanup_status.json](D:/documents/ProteoSphereV2/artifacts/status/duplicate_cleanup_status.json)
- [duplicate_cleanup_dry_run_plan.json](D:/documents/ProteoSphereV2/artifacts/status/duplicate_cleanup_dry_run_plan.json)
- [duplicate_storage_inventory.json](D:/documents/ProteoSphereV2/artifacts/status/duplicate_storage_inventory.json)

## Current Acceptance Boundary

- Scanned roots: `5`
- Scanned files: `270011`
- Duplicate groups: `42339`
- Duplicate files: `130460`
- Reclaimable files: `87513`
- Reclaimable bytes: `100930747119`
- Partial files: `9`
- Protected files: `2`

The staged dry-run plan remains intentionally small relative to the inventory:

- Action count: `50`
- Planned reclaimable bytes: `1575085`
- Allowed cohorts:
  - `local_archive_equivalents`
  - `seed_vs_local_copy_duplicates`
  - `same_release_local_copy_duplicates`

## Acceptance Gates

1. Inputs and outputs stay report-only.
2. The current inventory still matches the P55 boundary.
3. The dry-run plan stays limited to the safe-first cohorts.
4. Every planned removal is exact-match safe.
5. The acceptance scope stays smaller than the raw inventory boundary.
6. Protected and partial files remain excluded.

## What Acceptance Means

Acceptance here means the executor path can be trusted as a no-delete report generator for the staged plan. It does not mean any duplicate cleanup has been executed.

The executor is acceptable only if:

- it reads the current inventory, cleanup status, and dry-run plan
- it writes only JSON and markdown outputs
- it leaves `data/raw` and `data/packages` unchanged
- it keeps protected and partial files out of the removal set
- it does not expand the allowed cohorts

## Operator Read

The right interpretation is narrow: the report-only executor path may be accepted for review, but it becomes actionable only when the staged plan still matches the current counts and every path-safety gate passes.

If the counts drift, the cohorts change, or any removal path touches protected or partial data, the acceptance gate should fail closed and the inventory should be refreshed before another attempt.
