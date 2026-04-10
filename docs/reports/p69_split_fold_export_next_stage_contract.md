# p69 Split Fold Export Next Stage Contract

This report-only contract defines the next executable stage after the live fold-export gate preview without unlocking folds yet.

## Next Stage

The next stage is `run_scoped_fold_export_staging`. It is staging-only: it accepts the live gate preview, reconfirms dry-run parity, and prepares a run-scoped fold export manifest, but it does not materialize CV folds.

## Required Preconditions

- The live gate preview must still show `cv_fold_export_unlock_gate` as blocked pending unlock.
- `split_engine_dry_run_validation` must remain `aligned` with no issues.
- `split_engine_input_preview` must still show `assignment_count=1889` and `fold_export_ready=false`.
- The p68 gate conditions must remain satisfied before any future fold export request is allowed.

## What This Stage May Do

- Build a run-scoped fold export staging manifest.
- Preserve the validated assignment and simulation parity.
- Surface the gate state explicitly.

## What This Stage Must Not Do

- Materialize CV folds.
- Promote a release split.
- Rewrite protected latest surfaces.
- Weaken the p67 dry-run guardrails or the p68 gate conditions.

## Current Truth

The repo has the necessary previews for the handoff, but the fold gate is still closed. `cv_folds_materialized` is false and `final_split_committed` is false, so the stage remains report-only in the current state.

## Grounding

- [`artifacts/status/p68_split_fold_export_gate_contract.json`](D:/documents/ProteoSphereV2/artifacts/status/p68_split_fold_export_gate_contract.json)
- [`artifacts/status/split_fold_export_gate_preview.json`](D:/documents/ProteoSphereV2/artifacts/status/split_fold_export_gate_preview.json)
- [`artifacts/status/split_engine_dry_run_validation.json`](D:/documents/ProteoSphereV2/artifacts/status/split_engine_dry_run_validation.json)
- [`artifacts/status/split_engine_input_preview.json`](D:/documents/ProteoSphereV2/artifacts/status/split_engine_input_preview.json)
