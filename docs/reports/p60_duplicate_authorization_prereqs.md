# P60 Duplicate Authorization Prerequisites

Report-only prerequisite note for the next phase of duplicate cleanup authorization.

## What This Uses

- Live executor status: `artifacts/status/duplicate_cleanup_executor_status.json`
- Cleanup status: `artifacts/status/duplicate_cleanup_status.json`
- Dry-run plan: `artifacts/status/duplicate_cleanup_dry_run_plan.json`
- Validation checklist: `artifacts/status/p55_duplicate_validation_checklist.json`
- Acceptance checklist: `artifacts/status/p56_duplicate_executor_acceptance.json`
- Operator handoff: `artifacts/status/p57_duplicate_operator_handoff.json`
- Drift diagnosis: `artifacts/status/p58_duplicate_drift_diagnosis.json`

## Current Readout

The executor is still `report_only_no_delete`, still safe-first, and still delete-disabled.

The live validation warning is real, but it is narrow:

- the inventory summary and cleanup status summary no longer match exactly
- the mismatch comes from `candidate_size_bucket_count`
- the duplicate counts themselves still match

This is a summary-shape drift, not a data-loss signal.

## Protected-Surface Rules

The current protected-surface rules remain unchanged:

- no protected paths in the removal set
- no partial paths in the removal set
- no latest-surface rewrites
- exact SHA-256 match for every planned removal
- every action must have a keeper path
- the plan must stay within the safe-first cohort set

The current status still shows `9` partial files and `2` protected files, so those rules must stay hard.

## Authorization Prerequisites

### 1. Normalize the summary shape

The live executor warning is triggered because the inventory artifact carries `candidate_size_bucket_count`, while the cleanup status summary does not.

Until the status summary shape matches the inventory shape, the executor should not be treated as ready for the next phase.

### 2. Refresh the stale acceptance snapshot

The acceptance artifact still reflects a `50`-action / `1,575,085`-byte snapshot, but the live executor now reports `100` actions and `3,928,198` bytes.

That means p56 is no longer current and must be regenerated before any authorization decision.

### 3. Keep the safe-first boundary unchanged

The allowed cohorts remain:

- `local_archive_equivalents`
- `same_release_local_copy_duplicates`
- `seed_vs_local_copy_duplicates`

That boundary is still correct and should not widen during authorization review.

### 4. Keep exact-match and path-safety gates intact

The staged dry-run plan still needs every removal to remain:

- exact hash safe
- free of protected paths
- free of partial paths
- free of latest-surface rewrites

### 5. Keep protected and partial surfaces excluded

Those surfaces are still the hard stop condition. They are not a gray area for the next phase.

## Operator Read

The next phase is not authorizable yet. The executor is healthy enough to review, but the summary-shape warning and the stale acceptance snapshot mean we should refresh the artifacts first and only then reconsider authorization.

## Bottom Line

The prerequisites are simple: fix the summary-shape drift, regenerate the acceptance snapshot, and re-check the same protected-surface rules. Until then, the executor stays report-only and delete-disabled.
