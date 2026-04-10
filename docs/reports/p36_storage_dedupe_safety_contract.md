# Storage Dedupe Safety Contract

- Generated at: `2026-04-01T10:13:48.7623322-05:00`
- Scope: read-only safety contract for duplicate discovery and cleanup
- Basis: the current storage topology, local registry snapshots, copy-status reports, and checksum-capable materialization scripts

## Scan Roots

These roots may be scanned for duplicate discovery, but the scan itself is read-only:

- `data/raw`
- `data/raw/local_copies`
- `data/raw/local_registry`
- `data/raw/bootstrap_runs`
- `data/raw/local_registry_runs`
- `data/packages`
- `runs/real_data_benchmark/full_results`
- `data/canonical`

The intent is to compare byte content across raw mirrors, local copies, imported registries, packet surfaces, and future downloaded assets without treating any of those roots as automatically mutable.

## Never Rewrite

Cleanup must not rewrite these protected surfaces:

- `data/canonical/LATEST.json`
- `data/packages/LATEST.json`
- `data/packages/LATEST.partial.json`
- `data/raw/bootstrap_runs/LATEST.json`
- `data/raw/local_registry_runs/LATEST.json`

Timestamped bootstrap and registry snapshots are append-only evidence as well, including:

- `data/raw/bootstrap_runs/<timestamp>.json`
- `data/raw/local_registry/<timestamp>/<source>/manifest.json`
- `data/raw/local_registry/<timestamp>/<source>/inventory.json`
- `data/raw/local_registry_runs/<timestamp>.json`

## Safe Cleanup Target

The only current cleanup target is `data/raw/local_copies`, and even there the contract is narrow:

- Remove only true duplicate blobs after a verified replacement or a surviving source-of-record pointer exists.
- Replace a file with a hardlink or junction only when provenance is preserved and the filesystem supports it.
- Never collapse source-native raw payloads, registries, packet payloads, and canonical records into the same storage role.

## Evidence Required

Before anything is declared safe to remove, all of the following must be true:

- Every candidate file pair has the same SHA-256 digest.
- For directories, a full per-file manifest exists with hashes and sizes; root-path similarity is not enough.
- The duplicate sits in the same role class as the surviving copy and is not a distinct derived view.
- A surviving manifest, registry snapshot, or run manifest still points to the bytes after cleanup.
- The exact candidate paths were predeclared; fuzzy or inferred path matches are not allowed.

## Post-Cleanup Validation

After cleanup, the following checks must pass:

- Recompute SHA-256 for surviving copies and compare them to pre-cleanup digests.
- Parse `data/raw/bootstrap_runs/LATEST.json` and `data/raw/local_registry_runs/LATEST.json` successfully.
- Rerun `scripts/audit_data_inventory.py` and confirm source counts and availability states do not regress.
- Rerun `scripts/export_source_coverage_matrix.py` and confirm the effective source picture stays stable unless the cleanup intentionally removed only redundant mirrors.
- Rerun `scripts/summarize_local_copy_status.py` and confirm surviving destinations still report complete.
- If any packet artifact changed, rerun `scripts/export_packet_state_comparison.py` and require no new regressions.

## What This Contract Is Not

- No rewriting of canonical latest surfaces.
- No rewriting of packet latest surfaces.
- It is not permission to rewrite canonical latest surfaces.
- It is not permission to rewrite packet latest surfaces.
- It is not permission to silently reclaim bytes without proof.
- It is not permission to dedupe based on file names, folder shape, or byte size alone.

## Evidence Anchors

- [`data/raw/README.md`](/D:/documents/ProteoSphereV2/data/raw/README.md)
- [`docs/reports/source_storage_strategy.md`](/D:/documents/ProteoSphereV2/docs/reports/source_storage_strategy.md)
- [`docs/reports/p32_local_copy_status.md`](/D:/documents/ProteoSphereV2/docs/reports/p32_local_copy_status.md)
- [`docs/reports/p32_local_copy_priority.md`](/D:/documents/ProteoSphereV2/docs/reports/p32_local_copy_priority.md)
- [`data/raw/local_registry_runs/LATEST.json`](/D:/documents/ProteoSphereV2/data/raw/local_registry_runs/LATEST.json)
- [`data/raw/bootstrap_runs/LATEST.json`](/D:/documents/ProteoSphereV2/data/raw/bootstrap_runs/LATEST.json)
- [`data/raw/local_registry/20260330T054522Z/import_manifest.json`](/D:/documents/ProteoSphereV2/data/raw/local_registry/20260330T054522Z/import_manifest.json)
- [`data/raw/local_registry/20260330T054522Z/chembl/inventory.json`](/D:/documents/ProteoSphereV2/data/raw/local_registry/20260330T054522Z/chembl/inventory.json)
- [`execution/acquire/local_source_mirror.py`](/D:/documents/ProteoSphereV2/execution/acquire/local_source_mirror.py)
- [`execution/acquire/local_corpus_sampler.py`](/D:/documents/ProteoSphereV2/execution/acquire/local_corpus_sampler.py)
- [`scripts/download_raw_data.py`](/D:/documents/ProteoSphereV2/scripts/download_raw_data.py)
- [`scripts/download_resolver_safe_urls.py`](/D:/documents/ProteoSphereV2/scripts/download_resolver_safe_urls.py)
- [`scripts/generate_available_payload_registry.py`](/D:/documents/ProteoSphereV2/scripts/generate_available_payload_registry.py)
- [`scripts/materialize_selected_packet_cohort.py`](/D:/documents/ProteoSphereV2/scripts/materialize_selected_packet_cohort.py)
- [`execution/materialization/packet_checksum_audit.py`](/D:/documents/ProteoSphereV2/execution/materialization/packet_checksum_audit.py)
- [`scripts/audit_data_inventory.py`](/D:/documents/ProteoSphereV2/scripts/audit_data_inventory.py)
- [`scripts/export_source_coverage_matrix.py`](/D:/documents/ProteoSphereV2/scripts/export_source_coverage_matrix.py)
- [`scripts/summarize_local_copy_status.py`](/D:/documents/ProteoSphereV2/scripts/summarize_local_copy_status.py)
- [`scripts/export_packet_state_comparison.py`](/D:/documents/ProteoSphereV2/scripts/export_packet_state_comparison.py)
