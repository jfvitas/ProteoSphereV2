# P69 Split Fold Export Truth Review

This is a report-only review of [split_fold_export_gate_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/split_fold_export_gate_preview.json), grounded in [split_engine_dry_run_validation.json](/D:/documents/ProteoSphereV2/artifacts/status/split_engine_dry_run_validation.json), [split_engine_input_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/split_engine_input_preview.json), and [operator_dashboard.json](/D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/operator_dashboard.json). It focuses on whether the gate cleanly captures why export is blocked, any drift risks, and the safest next executable step.

## What The Gate Proves Now

The gate preview cleanly says the dry-run chain is aligned, but fold export is still blocked.

It does that with a tight set of explicit reasons:

- `fold_export_ready=false`
- `cv_folds_materialized=false`
- `final_split_committed=false`

It also stays consistent with the dry-run validator and the input preview:

- dry-run validation is `aligned`
- candidate rows and assignment rows both equal `1889`
- the next unlocked stage is still `split_engine_dry_run`

So the gate is truthful about the current fold-export boundary. It does not pretend that dry-run parity alone unlocks export.

## Drift Risks

The main drift risk is scope mismatch.

The gate preview explains why fold export is blocked, but the benchmark dashboard shows a broader release-grade bar is still active:

- `operator_go_no_go = no-go`
- `release_grade_status = blocked_on_release_grade_bar`
- `ready_for_release = false`

That means the fold gate should not be read as a general release-ready signal.

There is also a small structural drift risk in the gate metadata itself:

- `required_condition_count = 4`
- only 3 blocked reasons are surfaced explicitly

That does not make the gate wrong, but it does mean the operator should not infer a simple 3-of-4 progress model without checking the underlying gate logic.

The dashboard also reminds us that the release-grade blockers are broader than fold export:

- runtime maturity
- source coverage depth
- provenance/reporting depth

## Safest Next Executable Step

The safest next executable step is to keep this gate report-only and, if a new stage is introduced, make it run-scoped fold-prep only after an explicit unlock.

Do not export CV folds yet. Do not promote a release split yet. The truthful state is still:

- dry-run parity is proven
- fold export is blocked
- release-grade is blocked

## Grounded Examples

- `protein:P04637` is still a stable dry-run cluster, so the gate is not failing because of assignment drift in the largest group.
- `protein:P68871` and `protein:P69905` show that the structure-overlap clusters are also stable, but that stability is still only dry-run stability.

## Boundary

This review is report-only. It does not edit code, does not rewrite protected latest surfaces, and does not claim CV fold export or release readiness that the current gate and dashboard explicitly deny.
