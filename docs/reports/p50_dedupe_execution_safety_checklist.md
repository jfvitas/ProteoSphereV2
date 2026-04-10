# Dedupe Execution Safety Checklist

- Generated at: `2026-04-01T11:00:13.4504657-05:00`
- Scope: report-only duplicate cleanup safety checklist grounded in the finished duplicate inventory and protected latest surfaces
- Basis: [`duplicate_storage_inventory.json`](/D:/documents/ProteoSphereV2/artifacts/status/duplicate_storage_inventory.json), [`duplicate_storage_inventory_primary.json`](/D:/documents/ProteoSphereV2/artifacts/status/duplicate_storage_inventory_primary.json), [`p36_storage_dedupe_safety_contract.json`](/D:/documents/ProteoSphereV2/artifacts/status/p36_storage_dedupe_safety_contract.json), and the current latest surfaces

## Inventory Baseline

- Scanned files: `268635`
- Duplicate groups: `42169`
- Duplicate files: `129679`
- Reclaimable files estimate: `87510`
- Reclaimable bytes estimate: `100930620625`
- Partial files excluded: `9`
- Protected latest files excluded: `0`

The duplicate inventory is large enough to justify cleanup planning, but the numbers alone are not enough to authorize deletion. The proof still has to come from byte identity, lineage, and post-cleanup validation.

## Protected Surfaces

These surfaces stay read-only:

- `data/canonical/LATEST.json`
- `data/packages/LATEST.json`
- `data/packages/LATEST.partial.json`
- `data/raw/bootstrap_runs/LATEST.json`
- `data/raw/local_registry_runs/LATEST.json`

Current package latest state is still held:

- `status`: `partial`
- `latest_promotion_state`: `held`
- `release_grade_ready`: `false`
- `packet_count`: `12`
- `complete_count`: `7`
- `partial_count`: `5`
- `unresolved_count`: `0`

## Checklist

1. Scan only the approved roots: `data/raw`, `data/raw/local_copies`, `data/raw/local_registry`, `data/raw/bootstrap_runs`, `data/raw/local_registry_runs`, `data/packages`, `runs/real_data_benchmark/full_results`, and `data/canonical`.
1. Do not rewrite the protected latest surfaces listed above.
1. Declare a duplicate safe only when SHA-256 matches exactly for every candidate file pair.
1. Require a per-file hash inventory before inferring directory equivalence.
1. Require a surviving manifest, registry snapshot, or run manifest that still points to the bytes after cleanup.
1. Do not collapse source-native raw payloads, registries, packet payloads, canonical records, and derived views into one cleanup bucket.
1. Treat `data/raw/local_copies` as the current reclamation target; keep every other root scan-only unless a future contract expands scope.
1. Skip partial transfer files and any protected latest pointer or latest-partial pointer.
1. After cleanup, rerun the inventory, coverage, local-copy status, and packet-state checks.
1. Confirm that all `LATEST.json` snapshots still parse and that no new regressions appear.

## Required Evidence Before Removal

- Full SHA-256 identity for the candidate files.
- A manifest or registry snapshot that preserves the source-of-record path.
- A role match so the candidate is not a distinct derived view.
- An allowlisted candidate path pair or group.
- A rebuild path that can recreate the removed bytes from surviving evidence.

## Required Post-Cleanup Validation

- Recompute SHA-256 for surviving copies and compare them with pre-cleanup digests.
- Parse `data/raw/bootstrap_runs/LATEST.json` and `data/raw/local_registry_runs/LATEST.json` successfully.
- Rerun [`scripts/audit_data_inventory.py`](/D:/documents/ProteoSphereV2/scripts/audit_data_inventory.py) and confirm source counts and availability states do not regress.
- Rerun [`scripts/export_source_coverage_matrix.py`](/D:/documents/ProteoSphereV2/scripts/export_source_coverage_matrix.py) and confirm effective source availability stays stable unless only redundant mirrors were removed.
- Rerun [`scripts/summarize_local_copy_status.py`](/D:/documents/ProteoSphereV2/scripts/summarize_local_copy_status.py) and confirm surviving destinations remain complete.
- If any packet artifact changed, rerun [`scripts/export_packet_state_comparison.py`](/D:/documents/ProteoSphereV2/scripts/export_packet_state_comparison.py) and require no new regressions.

## What This Is Not

- No code edits.
- No cleanup execution.
- No canonical latest rewrites.
- No packet latest rewrites.
- No dedupe decisions from filename or size alone.

## Evidence Anchors

- [`duplicate_storage_inventory.md`](/D:/documents/ProteoSphereV2/docs/reports/duplicate_storage_inventory.md)
- [`duplicate_storage_inventory_primary.md`](/D:/documents/ProteoSphereV2/docs/reports/duplicate_storage_inventory_primary.md)
- [`p36_storage_dedupe_safety_contract.md`](/D:/documents/ProteoSphereV2/docs/reports/p36_storage_dedupe_safety_contract.md)
- [`packet_state_comparison.md`](/D:/documents/ProteoSphereV2/docs/reports/packet_state_comparison.md)
- [`data_inventory_audit.md`](/D:/documents/ProteoSphereV2/docs/reports/data_inventory_audit.md)
- [`source_coverage_matrix.md`](/D:/documents/ProteoSphereV2/docs/reports/source_coverage_matrix.md)
- [`p32_local_copy_status.md`](/D:/documents/ProteoSphereV2/docs/reports/p32_local_copy_status.md)
- [`p32_local_copy_priority.md`](/D:/documents/ProteoSphereV2/docs/reports/p32_local_copy_priority.md)

