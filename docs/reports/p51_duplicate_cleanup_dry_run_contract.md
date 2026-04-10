# P51 Duplicate Cleanup Dry-Run Contract

Report-only contract based on the finished duplicate cleanup staging map, cleanup status snapshot, and safety checklist.

## Truth Boundary

- This checklist is report-only. It turns the finished duplicate inventory into a preflight contract for future cleanup while keeping latest/protected surfaces immutable and requiring byte identity plus provenance lineage before any reclamation.
- latest promotion untouched: `true`
- cleanup execution: `false`
- report-only: `true`

## Source Artifacts

- `artifacts/status/p50_duplicate_cleanup_staging_map.json` (staging_map)
- `artifacts/status/duplicate_cleanup_status.json` (cleanup_status)
- `artifacts/status/p50_dedupe_execution_safety_checklist.json` (safety_checklist)

## Status Snapshot

- 42339 duplicate groups
- 130460 duplicate files
- 100930747119 reclaimable bytes
- 9 partial files
- 2 protected files

## Dry-Run Scope

The dry-run is report-only. It may simulate the staging-map order, but it may not mutate files or rewrite latest pointers.

### Allowed Cohorts
- **Mirror-only same-release duplicates**: 42148 groups, 3473651889 bytes reclaimable.
  - Safety note: Safe-first because the inventory only shows mirror_copy roots and the same-release fingerprints match.
- **Mirror-only archive-equivalent copies**: 4 groups, 3504597550 bytes reclaimable.
  - Safety note: Safe-first because the archive payloads are byte-identical and no source_of_record path is involved.

### Validation-Required Cohort
- **Mirror copies paired with source-of-record baselines**: 10 groups, 93941811480 bytes reclaimable.
  - Safety note: Requires checksum validation and explicit source-of-record preservation before any deletion.

### Excluded From Any Cleanup
- Protected latest paths:
  - `data/canonical/LATEST.json`
  - `data/packages/LATEST.json`
  - `data/packages/LATEST.partial.json`
  - `data/raw/bootstrap_runs/LATEST.json`
  - `data/raw/local_registry_runs/LATEST.json`
- Protected-latest state snapshot:
  - `package_latest`: data/packages/LATEST.json (partial)
  - `package_latest_partial`: data/packages/LATEST.partial.json (held)
  - `bootstrap_latest`: data/raw/bootstrap_runs/LATEST.json (protected_latest)
  - `local_registry_latest`: data/raw/local_registry_runs/LATEST.json (authoritative_refresh_only)
- Staging-map no-touch set:
  - Protected: `data\raw\bootstrap_runs\LATEST.json`
  - Protected: `data\packages\LATEST.json`
  - Partial: `data\raw\protein_data_scope_seed\string\evidence_schema.v12.0.sql.gz.part`
  - Partial: `data\raw\protein_data_scope_seed\string\network_schema.v12.0.sql.gz.part`
  - Partial: `data\raw\protein_data_scope_seed\string\protein.links.detailed.v12.0.txt.gz.part`
  - Partial: `data\raw\protein_data_scope_seed\string\protein.links.v12.0.txt.gz.part`
  - Partial: `data\raw\protein_data_scope_seed\uniprot\uniref100.fasta.gz.part`
  - Partial: `data\raw\protein_data_scope_seed\uniprot\uniref100.xml.gz.part`
  - Partial: `data\raw\protein_data_scope_seed\uniprot\uniref50.fasta.gz.part`
  - Partial: `data\raw\protein_data_scope_seed\uniprot\uniref50.xml.gz.part`
  - Partial: `data\raw\protein_data_scope_seed\uniprot\uniref90.xml.gz.part`
  - Role `derived_output`: 166 groups, 771 files.
  - Role `run_manifest`: 1 groups, 2 files.
  - Role `source_of_record`: 17 groups, 24 files.

### Deferred, Not Staged
- Registry snapshots: 3 groups, 6 files.

## Ordered Dry-Run Sequence
1. **Mirror-only same-release duplicates**
   - Cohort: `mirror_only_same_release`
   - Action: Remove redundant mirror copies where every file sits in mirror_copy roots and the content is the same release.
   - Validation: Re-run the inventory and confirm no source_of_record, derived_output, or partial paths were changed.
   - Expected reclaimable bytes: 3473651889
2. **Mirror-only archive-equivalent copies**
   - Cohort: `mirror_only_archive_equivalent`
   - Action: Collapse mirror-only archive twins after verifying the payload bytes match.
   - Validation: Re-run the inventory and verify the source-of-record baseline remains untouched.
   - Expected reclaimable bytes: 3504597550
3. **Mirror copies paired with source-of-record baselines**
   - Cohort: `mirror_vs_source_of_record`
   - Action: Remove only the mirror-side duplicates after a fresh checksum comparison with the seed copy.
   - Validation: Confirm the seed/root-of-record copy still exists and matches the duplicate fingerprint before deleting any mirror file.
   - Expected reclaimable bytes: 93941811480

## Exact Validation Gates Before Any Dry-Run Cleanup
- Step 1: Limit the scan surface - Scan only the approved roots: data/raw, data/raw/local_copies, data/raw/local_registry, data/raw/bootstrap_runs, data/raw/local_registry_runs, data/packages, runs/real_data_benchmark/full_results, and data/canonical.
- Step 2: Freeze protected latest surfaces - Do not rewrite data/canonical/LATEST.json, data/packages/LATEST.json, data/packages/LATEST.partial.json, data/raw/bootstrap_runs/LATEST.json, or data/raw/local_registry_runs/LATEST.json.
- Step 3: Accept only exact byte identity - Declare a duplicate safe only when SHA-256 matches exactly for every candidate file pair; for directories, require a per-file hash inventory before inferring tree equivalence.
- Step 4: Preserve provenance lineage - Require a surviving manifest, registry snapshot, or run manifest that still points to the bytes after cleanup.
- Step 5: Reject role collapse - Do not merge source-native raw payloads, registries, packet payloads, canonical records, and derived views into one cleanup bucket.
- Step 6: Constrain cleanup targets - Treat data/raw/local_copies as the current reclamation target; all other roots are scan-only unless a future contract explicitly adds them.
- Step 7: Exclude partials and protected pointers - Skip partial transfer files and any protected latest pointer or latest-partial pointer during cleanup decisions.
- Step 8: Validate post-cleanup integrity - Rerun inventory, coverage, local-copy status, and packet-state checks after cleanup; parse all LATEST.json snapshots successfully and confirm no new regressions appear.

## Exact Validation Gates After Any Dry-Run Cleanup
1. Recompute SHA-256 for surviving copies and compare against pre-cleanup digests.
2. Parse data/raw/bootstrap_runs/LATEST.json and data/raw/local_registry_runs/LATEST.json successfully.
3. Rerun scripts/audit_data_inventory.py and confirm source counts and availability states do not regress.
4. Rerun scripts/export_source_coverage_matrix.py and confirm effective source availability stays stable unless only redundant mirrors were removed.
5. Rerun scripts/summarize_local_copy_status.py and confirm surviving destinations remain complete.
6. If any packet artifact changed, rerun scripts/export_packet_state_comparison.py and require no new regressions.

## Abort Rules
- Abort if any candidate path is protected, partial, source_of_record, run_manifest, or derived_output.
- Abort if any candidate lacks exact SHA-256 identity with its retained baseline.
- Abort if any provenance path would be lost after the cleanup simulation.
- Abort if any dry-run report would imply a latest/protected surface rewrite.

## Success Condition

- All post-dry-run validation gates pass and no protected or latest surface changes are observed.

## Notes
- This contract does not authorize deletion; it only defines the report-only dry-run boundary.
- The only cleanup candidates in scope are the staging-map cohorts rooted in mirror_copy evidence.
- Source-of-record, derived-output, run-manifest, registry snapshot, protected latest, and partial files remain outside cleanup authority.
