# P50 Duplicate Cleanup Staging Map

Source of truth: `artifacts/status/duplicate_storage_inventory.json`

Inventory summary: 42339 duplicate groups, 130460 duplicate files, 94.00 GiB reclaimable, 9 partial files, 2 protected files.

## Highest Reclaim Roots

| Root | Mode | Reclaimable | Groups | Files |
| --- | --- | ---: | ---: | ---: |
| `data/raw/local_copies/chembl` | mirror_only_archive_equivalent | 32.92 GiB | 3 | 3 |
| `data/raw/local_copies/alphafold_db` | mirror_only_archive_equivalent | 26.62 GiB | 1 | 1 |
| `data/raw/local_copies/alphafold_db_v2` | mirror_only_archive_equivalent | 26.62 GiB | 1 | 1 |
| `data/raw/local_copies/pdbbind` | mixed_mirror_only | 5.71 GiB | 2807 | 2807 |
| `data/raw/local_copies/pdbbind_pl` | mirror_only_archive_equivalent | 3.11 GiB | 1 | 1 |
| `data/raw/local_copies/pdbbind_pp` | mirror_only | 2.44 GiB | 2798 | 2798 |
| `data/raw/local_copies/biolip` | mirror_only | 1.02 GiB | 1 | 2 |
| `data/raw/local_copies/uniprot` | mirror_only_archive_equivalent | 660.5 MiB | 1 | 1 |
| `data/raw/local_copies/raw` | mixed_mirror_only | 479.6 MiB | 39321 | 39321 |
| `data/raw/local_copies/bindingdb` | mirror_only_archive_equivalent | 276.2 MiB | 1 | 1 |

## Safe-First Cleanup Cohorts

- **Mirror-only same-release duplicates**: 42148 groups, 3.24 GiB, root roles `mirror_copy`.
  - Safety: Safe-first because the inventory only shows mirror_copy roots and the same-release fingerprints match.
  - Examples: `data\raw\local_copies\raw\rcsb\5I25.json`, `data\raw\local_copies\raw_rcsb\5I25.json`, `data\raw\local_copies\raw\rcsb\9MSG.json`
- **Mirror-only archive-equivalent copies**: 4 groups, 3.26 GiB, root roles `mirror_copy`.
  - Safety: Safe-first because the archive payloads are byte-identical and no source_of_record path is involved.
  - Examples: `data\raw\local_copies\pdbbind\P-L.tar.gz`, `data\raw\local_copies\pdbbind_pl\P-L.tar.gz`, `data\raw\local_copies\pdbbind\P-NA.tar.gz`

## Validation-Required Cohort

- **Mirror copies paired with source-of-record baselines**: 10 groups, 87.49 GiB.
  - Safety: Requires checksum validation and explicit source-of-record preservation before any deletion.
  - Examples: `data\raw\local_copies\interpro\interpro.xml.gz`, `data\raw\protein_data_scope_seed\interpro\interpro.xml.gz`, `data\raw\local_copies\alphafold_db\swissprot_pdb_v6.tar`, `data\raw\local_copies\alphafold_db_v2\swissprot_pdb_v6.tar`

## Must Never Be Touched

- Protected files:
  - `data\raw\bootstrap_runs\LATEST.json`
  - `data\packages\LATEST.json`
- Active partials:
  - `data\raw\protein_data_scope_seed\string\evidence_schema.v12.0.sql.gz.part`
  - `data\raw\protein_data_scope_seed\string\network_schema.v12.0.sql.gz.part`
  - `data\raw\protein_data_scope_seed\string\protein.links.detailed.v12.0.txt.gz.part`
  - `data\raw\protein_data_scope_seed\string\protein.links.v12.0.txt.gz.part`
  - `data\raw\protein_data_scope_seed\uniprot\uniref100.fasta.gz.part`
  - `data\raw\protein_data_scope_seed\uniprot\uniref100.xml.gz.part`
  - `data\raw\protein_data_scope_seed\uniprot\uniref50.fasta.gz.part`
  - `data\raw\protein_data_scope_seed\uniprot\uniref50.xml.gz.part`
  - `data\raw\protein_data_scope_seed\uniprot\uniref90.xml.gz.part`
- Root roles to keep out of cleanup:
  - `source_of_record`: 17 groups, 24 files.
  - `run_manifest`: 1 groups, 2 files.
  - `derived_output`: 166 groups, 771 files.

## Deferred, Not Staged

- Registry snapshots: 3 groups, 6 files, 247.1 KiB observed.
- Examples: `data\raw\local_registry\20260330T215002Z\import_manifest.json`, `data\raw\local_registry\20260330T221329Z\import_manifest.json`, `data\raw\local_registry\20260323T003221Z\import_manifest.json`

## Ordered Cleanup Sequence

1. **Mirror-only same-release duplicates**
   - Action: Remove redundant mirror copies where every file sits in mirror_copy roots and the content is the same release.
   - Validation: Re-run the inventory and confirm no source_of_record, derived_output, or partial paths were changed.
   - Expected cleanup size: 3.24 GiB across 42148 groups.
2. **Mirror-only archive-equivalent copies**
   - Action: Collapse mirror-only archive twins after verifying the payload bytes match.
   - Validation: Re-run the inventory and verify the source-of-record baseline remains untouched.
   - Expected cleanup size: 3.26 GiB across 4 groups.
3. **Mirror copies paired with source-of-record baselines**
   - Action: Remove only the mirror-side duplicates after a fresh checksum comparison with the seed copy.
   - Validation: Confirm the seed/root-of-record copy still exists and matches the duplicate fingerprint before deleting any mirror file.
   - Expected cleanup size: 87.49 GiB across 10 groups.

## Scope Notes

- Cleanup-byte totals are per-root attribution from the inventory and are intended for staging order, not as a deduplicated global sum across roots.
- No code or manifest files were modified to produce this report.
