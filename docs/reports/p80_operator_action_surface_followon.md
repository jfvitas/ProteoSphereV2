# P80 Operator Action Surface Follow-on

This is a report-only recommendation for the next smallest safe operator surface improvement after the consolidated action preview, grounded in [operator_next_actions_preview.json](D:/documents/ProteoSphereV2/artifacts/status/operator_next_actions_preview.json), [operator_dashboard.json](D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/operator_dashboard.json), and [live_bundle_manifest_validation.json](D:/documents/ProteoSphereV2/artifacts/status/live_bundle_manifest_validation.json).

## Current Truth

The live surface is aligned, but still blocked:

- `bundle_validation_status = aligned_current_preview_with_verified_assets`
- `operator_go_no_go = no-go`
- `operator_dashboard_status = blocked_on_release_grade_bar`
- `ready_for_release = false`
- `release_grade_blocked = true`

So this follow-on should improve operator readability only. It should not change release truth.

## What The Consolidated Preview Already Says

The current next-actions preview has four rows:

1. `P00387` on the ligand lane is `operator_queue_ready`
2. `P31749` on the structure lane is `aligned`
3. `split` is `blocked_report_emitted`
4. `duplicate_cleanup` is `not_yet_executable_today`

That means the next smallest safe improvement is not a new action, but a cleaner split between the actionable and blocked lanes.

## Recommended Follow-on Surface

The safest next surface is a two-panel operator view:

- an immediate-action panel for `ligand` and `structure`
- a blocked panel for `split` and `duplicate_cleanup`

### Suggested Row Shape

Immediate-action rows should keep:

- `rank`
- `lane`
- `accession`
- `status`
- `next_truthful_stage`
- `blocked_for_release`

Blocked rows should keep:

- `rank`
- `lane`
- `status`
- `next_truthful_stage`
- `blocked_for_release`

## Why This Is The Smallest Safe Step

This is the smallest improvement because it:

- preserves the existing four-row truth surface
- makes the two actionable lanes easier to scan
- keeps the blocked lanes clearly separated
- does not loosen any `blocked_for_release` flags

## Still Deferred

The following remain out of scope:

- structure join certification
- ligand row materialization
- fold export unlock
- duplicate cleanup mutation
- release-grade promotion
- bundle manifest changes

## Boundary

This note is report-only. It does not add promotion logic, does not mutate bundle assets, and does not change the current no-go release posture. It only recommends a readability-first split of the operator action preview into immediate and blocked panels.
