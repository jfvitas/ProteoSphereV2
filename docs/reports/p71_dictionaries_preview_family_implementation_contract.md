# Dictionaries Preview Family Implementation Contract

## Summary
The next safe preview family is `dictionaries`.
It is the lowest-risk missing family after `protein_similarity_signatures` because it is packaging and lookup work, not new biological procurement.

## Current Baseline
The live bundle manifest is still `preview_generated_verified_assets` with `budget_class = A`.
It currently reports `dictionaries = 0` while `protein_similarity_signatures = 11`, `structure_similarity_signatures = 4`, and `leakage_groups = 11`.

## Files That Must Change
The clean implementation path is concentrated in three code files:
- `scripts/build_lightweight_preview_bundle_assets.py`
- `scripts/export_bundle_manifest.py`
- `scripts/validate_live_bundle_manifest.py`

Why these three:
- The bundle builder must persist the dictionaries preview surface and include it in the released bundle shape.
- The manifest exporter currently hardcodes dictionaries as zero and must pull the new preview count into `table_families`, `record_counts`, and `build_inputs`.
- The validator must add a dictionaries slice assessment so the live manifest can be checked against the current preview surface.

## Generated Surfaces To Refresh
When the preview family is added, these artifacts should be regenerated:
- `artifacts/status/lightweight_bundle_manifest.json`
- `artifacts/bundles/preview/proteosphere-lite.sqlite.zst`
- `artifacts/bundles/preview/proteosphere-lite.release_manifest.json`
- `artifacts/bundles/preview/proteosphere-lite.sha256`
- `docs/reports/proteosphere-lite.contents.md`
- `docs/reports/proteosphere-lite.schema.md`

## Test Areas That Need Updates
The bundle change is anchored by these unit tests:
- `tests/unit/test_build_lightweight_preview_bundle_assets.py`
- `tests/unit/test_export_bundle_manifest.py`
- `tests/unit/test_validate_live_bundle_manifest.py`

Those tests should cover:
- a non-zero dictionaries preview fixture
- dictionaries appearing as an included table family
- a dictionaries slice row in manifest validation

## Conditional Documentation Surfaces
The bundle contents and schema doc scripts are already manifest-driven.
They only need code changes if you want explicit dictionaries prose beyond the generic family list:
- `scripts/export_bundle_contents_doc.py`
- `scripts/export_bundle_schema_doc.py`

If the prose changes, add matching assertions in:
- `tests/unit/test_export_bundle_contents_doc.py`
- `tests/unit/test_export_bundle_schema_doc.py`

## Truth Boundary
This contract is report-only.
It does not claim implementation, completeness, or release readiness.
It only identifies the exact current surfaces that must move for a clean dictionaries preview family addition.
