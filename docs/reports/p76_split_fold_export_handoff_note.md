# P76 Split Fold Export Handoff Note

This report-only note hands off the split dry-run to the fold-export execution boundary.

## Current State

The split dry-run is aligned, but fold export remains blocked:

- [artifacts/status/split_engine_dry_run_validation.json](/D:/documents/ProteoSphereV2/artifacts/status/split_engine_dry_run_validation.json)
- [artifacts/status/split_fold_export_gate_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/split_fold_export_gate_preview.json)
- [artifacts/status/split_fold_export_staging_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/split_fold_export_staging_preview.json)
- [artifacts/status/split_post_staging_gate_check_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/split_post_staging_gate_check_preview.json)
- [artifacts/status/p75_split_after_gate_check_impl_order.json](/D:/documents/ProteoSphereV2/artifacts/status/p75_split_after_gate_check_impl_order.json)

Grounded dry-run state:

- candidate rows: `1889`
- assignments: `1889`
- split groups: `train=1`, `val=1`, `test=9`
- row-level split counts: `train=1440`, `val=266`, `test=183`
- validation status: `aligned`

## Handoff Order

1. Keep the dry-run parity as the trust anchor.
1. Treat the staging preview as run-scoped only.
1. Open the CV fold-export unlock gate only by separate approval.
1. Validate the request manifest against the already-aligned dry-run surfaces.
1. Materialize CV folds only after the request validation stays aligned.
1. Defer final split commit until separate release approval exists.

The implementation order in [p75_split_after_gate_check_impl_order.json](/D:/documents/ProteoSphereV2/artifacts/status/p75_split_after_gate_check_impl_order.json) matches that progression: request manifest, request validation, fold materialization, then final split commit.

## What Is Still Blocked

The fold-export surface is still blocked because:

- `fold_export_ready` is false
- `cv_folds_materialized` is false
- `final_split_committed` is false
- the unlock gate is still report-only and blocked pending unlock
- the operator dashboard is still `no-go`

## Operator Truth

The right operator read is:

- split dry-run: aligned
- staging preview: blocked report only
- post-staging gate check: blocked report only
- fold export: not yet unlocked
- final split commit: deferred

## Low-Risk Next Improvements

- Keep the request manifest separate from fold materialization.
- Preserve the current split counts and largest groups as the validation anchor.
- Keep the staging surface run-scoped only until the unlock gate changes state.
- Do not promote any release split until the operator dashboard no longer says `no-go`.

## Bottom Line

The dry-run is stable enough to hand off, but the fold-export execution boundary is still blocked. The next safe move is a run-scoped request manifest only after a separate unlock step authorizes it.
