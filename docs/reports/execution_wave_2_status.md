# Execution Wave 2 Status

- Wave: `lightweight-library-execution-wave-2`
- Status: `active`

## Completed Local Slices

- `schema_v2_variant_structure`
  - Added additive `protein_variant` and `structure_unit` records in `core/library/summary_record.py`
  - Added focused round-trip and schema-view coverage in `tests/unit/core/test_summary_record.py`
- `summary_builder_v2_passthrough`
  - Taught `execution/library/build_summary_library.py` to preserve the new v2 record types
  - Added focused coverage in `tests/unit/execution/test_build_summary_library.py`
- `duplicate_cleanup_status_exporter`
  - Added `scripts/export_duplicate_cleanup_status.py`
  - Emitted `artifacts/status/duplicate_cleanup_status.json`
  - Emitted `docs/reports/duplicate_cleanup_status.md`
- `structure_unit_materializer_scaffold`
  - Added `execution/library/structure_unit_materializer.py`
  - Added `scripts/export_structure_unit_summary_library.py`
  - Emitted `artifacts/status/structure_unit_summary_library.json`
  - Emitted `docs/reports/structure_unit_summary_library.md`
- `structure_unit_operator_surface`
  - Taught the PowerShell/operator state surface to recognize `structure_unit_summary_library.json`
  - Extended operator dashboard coverage for summary-library inventory truth
- `duplicate_cleanup_dry_run_planner`
  - Added `scripts/export_duplicate_cleanup_dry_run_plan.py`
  - Emitted `artifacts/status/duplicate_cleanup_dry_run_plan.json`
  - Emitted `docs/reports/duplicate_cleanup_dry_run_plan.md`
- `external_cohort_audit_cli`
  - Added `scripts/audit_external_cohort.py`
  - Emitted `artifacts/status/external_cohort_audit.json`
  - Emitted `docs/reports/external_cohort_audit.md`

## Verified

- `python -m pytest tests/unit/core/test_summary_record.py tests/unit/execution/test_build_summary_library.py tests/unit/test_export_duplicate_cleanup_status.py -q`
- `python -m ruff check core/library/summary_record.py execution/library/build_summary_library.py scripts/export_duplicate_cleanup_status.py tests/unit/core/test_summary_record.py tests/unit/execution/test_build_summary_library.py tests/unit/test_export_duplicate_cleanup_status.py`

## Duplicate Inventory Truth

- Scanned roots: `5`
- Scanned files: `270011`
- Duplicate groups: `42339`
- Duplicate files: `130460`
- Reclaimable files: `87513`
- Reclaimable bytes: `100930747119`

## Safe-First Cleanup Cohorts

- `local_archive_equivalents`: `9` groups, `67588959998` reclaimable bytes
- `seed_vs_local_copy_duplicates`: `5` groups, `29857449032` reclaimable bytes
- `same_release_local_copy_duplicates`: `42148` groups, `3473651889` reclaimable bytes

## First V2-Derived Library Artifact

- `summary-library:structure-units:v1`
- Record count: `4`
- Example structure id: `4HHB`
- Example protein refs: `protein:P68871`, `protein:P69905`

## External Cohort Audit Truth

- Overall: `attention_needed` / `usable_with_notes`
- Leakage: `ok`
- Coverage-gap accessions: `Q9NZD4`, `Q2TAC2`, `P00387`, `P09105`, `Q9UCM0`

## Integrated Agent Outputs

- `p50_duplicate_cleanup_staging_map`
- `p50_dedupe_execution_safety_checklist`
- `p50_lightweight_bundle_packaging_proposal`
- `p50_motif_pathway_enrichment_tranche`
- `p50_training_set_creator_library_contract`
- `p29_summary_library_v2_bridge`
- `p51_duplicate_cleanup_dry_run_contract`
- `p51_v2_source_fusion_materialization_contract`
- `p51_protected_surface_validation_contract`

## Next Execution Slices

- protein variant materializer scaffold
- duplicate cleanup dry-run executor scaffold
- library inventory and structure operator convergence
- bundle manifest publication scaffold
