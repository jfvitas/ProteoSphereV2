# p85 Split Lane After Identity-Core Preview

This note is report-only. Including `ligand_identity_core_materialization_preview` in the preview bundle does not change split or leakage claims.

## Current Reading

- The bundle manifest is `preview_generated_verified_assets`.
- `ligand_identity_core_materialization_preview` is included in the preview bundle.
- The bundle still excludes ligands globally.
- The split lane remains `blocked_report_emitted`.
- The leakage surfaces remain the same protein-spine previews.

## What Does Not Change

- Split claims do not change.
- Leakage claims do not change.
- No CV folds are unlocked or materialized.
- No ligand rows are materialized.
- `bundle_ligands_included` remains `false`.

## Why The Claims Stay Stable

The identity-core preview is a candidate-family preview, not a global ligand materialization. The bundle validation confirms the preview assets are aligned, but the split and leakage truth still comes from the protein split previews and leakage-group/signature surfaces.

## Truth Boundary

This note does not authorize split progression or leakage recalculation. It only records that the identity-core preview being present in the preview bundle does not by itself alter the current split or leakage truth.
