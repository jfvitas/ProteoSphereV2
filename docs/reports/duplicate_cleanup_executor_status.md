# Duplicate Cleanup Executor Status

- Mode: `report_only_no_delete`
- Status: `usable_with_notes`
- Generated at: `2026-04-01T16:17:47.577796+00:00`
- Action count: `100`
- Planned reclaimable bytes: `3928198`
- Validation status: `passed`

## Validation Checks
- `inventory_summary_match`: `passed` (inventory/status summaries match on shared core fields)
- `allowed_cohorts_safe_first`: `passed` (all allowed cohorts stay within safe-first cohorts)
- `allowed_cohorts_status_alignment`: `passed` (plan cohorts align with cleanup status surface)
- `non_delete_plan_only`: `passed` (executor rewrites plan/status artifacts only)
- `partial_and_protected_excluded`: `passed` (each action keeps the required validation gates)
