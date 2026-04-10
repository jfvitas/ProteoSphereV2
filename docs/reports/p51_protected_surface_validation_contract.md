# Protected Surface Validation Contract

- Generated at: `2026-04-01T11:08:20.7756814-05:00`
- Scope: report-only validation contract for duplicate cleanup and lightweight bundle publication
- Basis: the finished duplicate inventory, the dedupe safety contract, the dedupe execution checklist, and the protected latest surfaces

## Protected Surfaces

These surfaces are immutable for cleanup and lightweight publication:

- `data/canonical/LATEST.json`
- `data/packages/LATEST.json`
- `data/packages/LATEST.partial.json`
- `data/raw/bootstrap_runs/LATEST.json`
- `data/raw/local_registry_runs/LATEST.json`

Current package latest state is still held:

- `status`: `partial`
- `latest_promotion_state`: `held`
- `release_grade_ready`: `false`

Current canonical latest state is `ready`, and the latest bootstrap and local-registry snapshots remain protected evidence.

## Cleanup Checks

Before any duplicate cleanup runs, verify:

- candidate paths are inside the approved scan roots
- every candidate duplicate file pair has identical SHA-256
- directory duplicates are backed by per-file manifests with hashes and sizes
- the candidate is the same storage role as the surviving copy
- a surviving manifest, registry snapshot, or run manifest still points to the bytes after cleanup
- no candidate path resolves to a protected latest or canonical surface
- partial transfer files are excluded from reclamation

The current safe cleanup target remains `data/raw/local_copies`.

## Lightweight Bundle Publication Checks

Before any lightweight bundle is published, verify:

- publication writes only to versioned or run-scoped outputs
- no output path uses a `LATEST.json` or `LATEST.partial.json` filename
- bundle manifests include exact file inventory, sizes, and checksums
- schema and manifest versions are pinned before publication
- publication outputs stay separate from canonical, bootstrap, registry, and package latest surfaces
- any emitted package artifact lives under a run-specific root, not a protected pointer

The current bundle guidance in [`p50_lightweight_bundle_packaging_proposal.md`](/D:/documents/ProteoSphereV2/docs/reports/p50_lightweight_bundle_packaging_proposal.md) and [`release_benchmark_bundle.md`](/D:/documents/ProteoSphereV2/docs/reports/release_benchmark_bundle.md) stays intact.

## Post-Action Validation

After cleanup:

- recompute SHA-256 for surviving copies and compare them to pre-cleanup digests
- rerun [`scripts/audit_data_inventory.py`](/D:/documents/ProteoSphereV2/scripts/audit_data_inventory.py)
- rerun [`scripts/export_source_coverage_matrix.py`](/D:/documents/ProteoSphereV2/scripts/export_source_coverage_matrix.py)
- rerun [`scripts/summarize_local_copy_status.py`](/D:/documents/ProteoSphereV2/scripts/summarize_local_copy_status.py)
- if packet artifacts changed, rerun [`scripts/export_packet_state_comparison.py`](/D:/documents/ProteoSphereV2/scripts/export_packet_state_comparison.py)

After publication:

- parse all protected `LATEST.json` snapshots successfully
- confirm none of those protected files changed as a side effect
- confirm the new bundle manifest or release asset lives outside the protected latest paths

## What This Contract Is Not

- No code edits.
- No cleanup execution.
- No bundle publication execution.
- No canonical latest rewrites.
- No package latest rewrites.
- No bootstrap or local registry latest rewrites.
- No decisions based on filename or size alone.

## Evidence Anchors

- [`duplicate_storage_inventory.md`](/D:/documents/ProteoSphereV2/docs/reports/duplicate_storage_inventory.md)
- [`duplicate_storage_inventory_primary.md`](/D:/documents/ProteoSphereV2/docs/reports/duplicate_storage_inventory_primary.md)
- [`p36_storage_dedupe_safety_contract.md`](/D:/documents/ProteoSphereV2/docs/reports/p36_storage_dedupe_safety_contract.md)
- [`p50_dedupe_execution_safety_checklist.md`](/D:/documents/ProteoSphereV2/docs/reports/p50_dedupe_execution_safety_checklist.md)
- [`p50_lightweight_bundle_packaging_proposal.md`](/D:/documents/ProteoSphereV2/docs/reports/p50_lightweight_bundle_packaging_proposal.md)
- [`release_benchmark_bundle.md`](/D:/documents/ProteoSphereV2/docs/reports/release_benchmark_bundle.md)
- [`packet_operator_blocker_surface.md`](/D:/documents/ProteoSphereV2/docs/reports/packet_operator_blocker_surface.md)
- [`package_materialization_notes.md`](/D:/documents/ProteoSphereV2/docs/reports/package_materialization_notes.md)
- [`source_storage_strategy.md`](/D:/documents/ProteoSphereV2/docs/reports/source_storage_strategy.md)

