# P58 Duplicate Drift Diagnosis

- Artifact: `p58_duplicate_drift_diagnosis`
- Status: `report_only`
- Generated at: `2026-04-01T11:47:49.2252932-05:00`

This note explains the current duplicate cleanup warning by comparing the storage inventory, cleanup status, and live executor status artifacts directly.

## What Matches

The core duplicate-cleanup counts still agree:

- scanned roots: `5`
- scanned files: `270011`
- duplicate groups: `42339`
- duplicate files: `130460`
- reclaimable files: `87513`
- reclaimable bytes: `100930747119`
- partial files: `9`
- protected files: `2`

The safe-first boundary also still agrees:

- `local_archive_equivalents`
- `seed_vs_local_copy_duplicates`
- `same_release_local_copy_duplicates`

The live executor remains report-only and delete-disabled.

## What Drifted

The warning comes from a summary-shape mismatch, not from the core duplicate counts.

The inventory summary includes one field that the cleanup status summary does not propagate:

- `candidate_size_bucket_count = 12423`

That field is present in [duplicate_storage_inventory.json](D:/documents/ProteoSphereV2/artifacts/status/duplicate_storage_inventory.json), but it is absent from [duplicate_cleanup_status.json](D:/documents/ProteoSphereV2/artifacts/status/duplicate_cleanup_status.json). The live executor then compares the two summary surfaces and emits:

- `inventory_summary_match`
- `inventory/status summaries differ`

## Precise Meaning Of The Warning

This is not a data-loss warning. It is a contract-shape warning.

The compared artifacts still agree on the actual duplicate cleanup boundary, but one artifact carries an extra aggregate field that the other does not. That is enough to make the live executor flag a warning even though the no-delete boundary is still intact.

## Operator Read

Treat the warning as a refresh-needed signal for the status summary shape. The right next step is to normalize the cleanup status summary so it carries the same aggregate fields as the inventory summary, then rerun the executor validation.

Do not read this as a deletion problem. The executor is still report-only, safe-first, and delete-disabled.

## Recommendation

Refresh or normalize the cleanup status summary, rerun validation, and only then treat the live executor status as clean again.
