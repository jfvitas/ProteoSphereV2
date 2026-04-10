# Split Fold Export Staging Preview

- Status: `complete`
- Stage ID: `run_scoped_fold_export_staging`
- Surface ID: `split_fold_export_staging_preview`
- Scope: `run_scoped_only`
- Gate status: `open`
- CV fold export unlocked: `True`

## Staging Manifest

- Manifest ID: `run_scoped_fold_export_staging:protein_spine_first_split_recipe_v1`
- Recipe ID: `protein_spine_first_split_recipe_v1`
- Candidate rows: `1889`
- Assignment count: `1889`
- Next unlocked stage: `split_fold_export_materialized`

## Blocked Report

- Validation status: `aligned`
- Dry-run validation status: `aligned`
- Dry-run issue count: `0`
- Fold export ready: `True`
- CV folds materialized: `True`
- Final split committed: `False`

## Blocked Reasons


## Truth Boundary

- This staging preview is the next executable fold-export surface, but it is still run-scoped-only and blocked. It preserves dry-run parity, emits a staging manifest shape, and stops before CV fold materialization or final split commitment.
