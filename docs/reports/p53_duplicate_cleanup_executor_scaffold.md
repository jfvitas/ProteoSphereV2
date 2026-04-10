# P53 Duplicate Cleanup Executor Scaffold

Report-only scaffold plan derived from the dry-run contract, the safety checklist, the staging map, and the duplicate cleanup status snapshot.

## Truth Boundary

- This artifact is report-only.
- It does not authorize deletion.
- It does not rewrite latest or protected surfaces.
- It preserves the dry-run contract and the safety checklist exactly.

## Source Artifacts

- `artifacts/status/p51_duplicate_cleanup_dry_run_contract.json`
- `artifacts/status/p50_dedupe_execution_safety_checklist.json`
- `artifacts/status/p50_duplicate_cleanup_staging_map.json`
- `artifacts/status/duplicate_cleanup_status.json`

## Scaffold Summary

- Safe-first cohorts: 2
- Validation-required cohorts: 1
- Protected latest paths: 5
- Preflight gates: 8
- Postflight gates: 6
- No-touch root roles: 3
- Deferred registry snapshot groups: 3

## Future Executor Shape

The intended executor is a fail-closed, report-only scaffold with six stages:

| Stage | Title | Purpose |
| --- | --- | --- |
| 1 | Pin inputs and freeze scope | Load the contract, checklist, staging map, and status snapshot as immutable inputs. |
| 2 | Enforce preflight gates | Evaluate the exact checklist gates before any candidate cleanup is simulated. |
| 3 | Build the candidate ledger | Separate safe-first cohorts from validation-required cohorts and keep no-touch paths out. |
| 4 | Simulate the ordered cleanup sequence | Walk the staging map order without deleting anything and attach expected reclaimable bytes. |
| 5 | Emit operator-facing reports | Write the JSON and markdown artifacts only. |
| 6 | Run post-cleanup validation hooks | Preserve the exact post-cleanup checks a real executor would need later. |

## Candidate Plan

### Safe-First Cohorts

- `mirror_only_same_release`
  - 42,148 groups
  - 129,635 files
  - 3,473,651,889 reclaimable bytes
  - Safety note: only `mirror_copy` roots and same-release fingerprints
- `mirror_only_archive_equivalent`
  - 4 groups
  - 8 files
  - 3,504,597,550 reclaimable bytes
  - Safety note: byte-identical archive payloads with no source-of-record path involved

### Validation-Required Cohort

- `mirror_vs_source_of_record`
  - 10 groups
  - 22 files
  - 93,941,811,480 reclaimable bytes
  - Safety note: requires checksum validation and explicit source-of-record preservation

### Ordered Cleanup Sequence

1. Mirror-only same-release duplicates
2. Mirror-only archive-equivalent copies
3. Mirror copies paired with source-of-record baselines

## Highest Reclaim Roots

| Root | Cleanup Mode | Reclaimable |
| --- | --- | ---: |
| `data/raw/local_copies/chembl` | mirror_only_archive_equivalent | 32.92 GiB |
| `data/raw/local_copies/alphafold_db` | mirror_only_archive_equivalent | 26.62 GiB |
| `data/raw/local_copies/alphafold_db_v2` | mirror_only_archive_equivalent | 26.62 GiB |
| `data/raw/local_copies/pdbbind` | mixed_mirror_only | 5.71 GiB |
| `data/raw/local_copies/pdbbind_pl` | mirror_only_archive_equivalent | 3.11 GiB |

## Validation Gates Before Any Dry-Run Cleanup

1. Limit the scan surface.
2. Freeze protected latest surfaces.
3. Accept only exact byte identity.
4. Preserve provenance lineage.
5. Reject role collapse.
6. Constrain cleanup targets.
7. Exclude partials and protected pointers.
8. Validate post-cleanup integrity.

### Exact Before-Gate Text

- Step 1: Limit the scan surface - Scan only the approved roots: data/raw, data/raw/local_copies, data/raw/local_registry, data/raw/bootstrap_runs, data/raw/local_registry_runs, data/packages, runs/real_data_benchmark/full_results, and data/canonical.
- Step 2: Freeze protected latest surfaces - Do not rewrite data/canonical/LATEST.json, data/packages/LATEST.json, data/packages/LATEST.partial.json, data/raw/bootstrap_runs/LATEST.json, or data/raw/local_registry_runs/LATEST.json.
- Step 3: Accept only exact byte identity - Declare a duplicate safe only when SHA-256 matches exactly for every candidate file pair; for directories, require a per-file hash inventory before inferring tree equivalence.
- Step 4: Preserve provenance lineage - Require a surviving manifest, registry snapshot, or run manifest that still points to the bytes after cleanup.
- Step 5: Reject role collapse - Do not merge source-native raw payloads, registries, packet payloads, canonical records, and derived views into one cleanup bucket.
- Step 6: Constrain cleanup targets - Treat data/raw/local_copies as the current reclamation target; all other roots are scan-only unless a future contract explicitly adds them.
- Step 7: Exclude partials and protected pointers - Skip partial transfer files and any protected latest pointer or latest-partial pointer during cleanup decisions.
- Step 8: Validate post-cleanup integrity - Rerun inventory, coverage, local-copy status, and packet-state checks after cleanup; parse all LATEST.json snapshots successfully and confirm no new regressions appear.

## Validation Gates After Any Dry-Run Cleanup

- Recompute SHA-256 for surviving copies and compare against pre-cleanup digests.
- Parse `data/raw/bootstrap_runs/LATEST.json` and `data/raw/local_registry_runs/LATEST.json` successfully.
- Rerun `scripts/audit_data_inventory.py` and confirm source counts and availability states do not regress.
- Rerun `scripts/export_source_coverage_matrix.py` and confirm effective source availability stays stable unless only redundant mirrors were removed.
- Rerun `scripts/summarize_local_copy_status.py` and confirm surviving destinations remain complete.
- If any packet artifact changed, rerun `scripts/export_packet_state_comparison.py` and require no new regressions.

## Abort Rules

- Abort if any candidate path is protected, partial, source_of_record, run_manifest, or derived_output.
- Abort if any candidate lacks exact SHA-256 identity with its retained baseline.
- Abort if any provenance path would be lost after the cleanup simulation.
- Abort if any dry-run report would imply a latest/protected surface rewrite.

## Notes

- This scaffold is a no-op plan, not an implementation.
- Source-of-record, derived-output, run-manifest, registry snapshot, protected latest, and partial files remain outside cleanup authority.
- A future executor must fail closed if the candidate set changes shape or if a protected surface becomes writable.
