# P55 Duplicate Validation Checklist

- Artifact: `p55_duplicate_validation_checklist`
- Status: `report_only`
- Generated at: `2026-04-01T11:27:56.1622030-05:00`
- Executor path: `scripts/export_duplicate_cleanup_dry_run_plan.py`
- Mode: `no_delete_dry_run`

This sidecar is the validation checklist for the no-delete dry-run executor path. It does not authorize cleanup, deletion, or any manifest rewrite. It only describes the checks an operator should clear before trusting the staged duplicate-cleanup plan.

## Current Boundary

- Scanned roots: `5`
- Scanned files: `270011`
- Duplicate groups: `42339`
- Duplicate files: `130460`
- Reclaimable files: `87513`
- Reclaimable bytes: `100930747119`
- Partial files: `9`
- Protected files: `2`

The dry-run plan itself is intentionally tiny relative to the full inventory:

- Action count: `50`
- Planned reclaimable bytes: `1575085`
- Allowed cohorts:
  - `local_archive_equivalents`
  - `seed_vs_local_copy_duplicates`
  - `same_release_local_copy_duplicates`

## Checklist

1. Confirm the executor reads only the current duplicate inventory, cleanup status, and dry-run plan artifacts.
2. Verify the current inventory summary still matches the staged safety boundary.
3. Confirm the dry-run plan is limited to the three safe-first cohorts.
4. Spot-check one action from each allowed cohort and confirm the keeper/removal relationship is a byte-identical duplicate pairing.
5. Verify every action carries the exact-match and safety gates:
   - `exact_sha256_match`
   - `no_protected_paths`
   - `no_partial_paths`
   - `no_latest_surface_rewrites`
6. Confirm the no-delete executor writes report files only and performs no filesystem mutation.
7. Confirm protected files and partial files remain outside the removal set.
8. Reconcile the reported action count and planned reclaimable bytes back to the current dry-run plan.

## What Success Looks Like

- The operator can read the plan without guessing which cohort is safe.
- No protected path appears in a removal list.
- No partial file is scheduled for removal.
- The executor leaves `data/raw` and `data/packages` untouched.
- The report-only outputs land in `artifacts/status` and `docs/reports` only.

## Failure Conditions

- The inventory summary no longer matches the current counts.
- Any action loses the exact SHA match gate.
- Any protected or partial file is included in the removal set.
- The executor performs a mutation instead of a dry-run report.
- The allowed cohort set expands beyond the safe-first cohorts listed above.

## Operator Read

This is a validation path, not a cleanup authorization. If any check fails, refresh the inventory and cleanup status artifacts first, then re-run the dry-run plan. If all checks pass, the no-delete executor path is safe to trust as a staged report.
