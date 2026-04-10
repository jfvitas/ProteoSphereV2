# p68 Split Fold Export Gate Contract

This report-only contract defines the exact conditions required before CV fold export can be unlocked.

## Gate

The gate is `cv_fold_export_unlock_gate`, grounded on `split_engine_input_preview` and validated by `split_engine_dry_run_validation`. It remains closed today because `fold_export_ready` is false and no CV folds are materialized.

## Conditions To Unlock

- Dry-run validation must stay `aligned` with no issues.
- Candidate, assignment, and simulation counts must remain at `1889` with `0` rejected rows.
- Split-group counts must remain `train=1`, `val=1`, and `test=9`.
- The largest groups must remain `P04637=train`, `P68871=val`, `P69905=test`, and `P31749=test`.
- The p67 dry-run contract must still require `entity_signature_row` atoms under `protein_spine_group` hard grouping.
- Protected latest surfaces must stay untouched.
- `final_split_committed` must remain false until a separate release approval exists.

## Current Truth

The repo is ready for the dry-run handoff, but not for fold export. `split_engine_input_preview.ready_for_split_engine_dry_run` is true, while `fold_export_ready` and `cv_folds_materialized` are still false.

## Grounding

- [`artifacts/status/p67_split_engine_dry_run_contract.json`](D:/documents/ProteoSphereV2/artifacts/status/p67_split_engine_dry_run_contract.json)
- [`artifacts/status/split_engine_dry_run_validation.json`](D:/documents/ProteoSphereV2/artifacts/status/split_engine_dry_run_validation.json)
- [`artifacts/status/split_engine_input_preview.json`](D:/documents/ProteoSphereV2/artifacts/status/split_engine_input_preview.json)
- [`artifacts/status/entity_split_assignment_preview.json`](D:/documents/ProteoSphereV2/artifacts/status/entity_split_assignment_preview.json)
- [`artifacts/status/entity_split_simulation_preview.json`](D:/documents/ProteoSphereV2/artifacts/status/entity_split_simulation_preview.json)

