# Overnight Execution Contract Preview

- Status: `report_only`
- Window hours: `12`
- Total jobs: `22`
- Health checkpoints: `4`

## Phase Plan

- `observe_and_protect` hours `0-3`: Keep the observed active download families running and avoid any duplicate launch while the gap matrix remains stable.
- `stabilize_and_review` hours `3-6`: Reconcile the supervisor pending jobs against the backlog and keep the missing STRING lane report-only.
- `drain_overnight_catalog` hours `6-12`: Advance the top catalog jobs only after the observed and pending jobs stay in a consistent truth boundary.

## Health Checkpoints

- `t0_reconcile_runtime` @ +0h
  required: artifacts/runtime/procurement_supervisor_state.json, artifacts/runtime/procurement_supervisor.pid
  pass: The supervisor snapshot still reports the same active observed download families and no duplicate launch has been queued.
- `t3_validate_gap_matrix` @ +3h
  required: artifacts/status/scrape_gap_matrix_preview.json, artifacts/status/source_coverage_matrix.json, artifacts/status/scrape_readiness_registry_preview.json
  pass: The gap matrix still reports only implemented, partial, or missing lane states and the missing STRING lane remains the same blocker.
- `t6_reconcile_backlog` @ +6h
  required: artifacts/status/overnight_queue_backlog_preview.json, artifacts/status/procurement_status_board.json, artifacts/runtime_checkpoints
  pass: The backlog still ranks the observed active jobs first, the pending supervisor jobs next, and the catalog jobs after that.
- `t12_bundle_and_queue_health` @ +12h
  required: artifacts/status/live_bundle_manifest_validation.json, artifacts/status/procurement_status_board.json, artifacts/runtime_checkpoints
  pass: The live bundle validation still reports aligned status and the queue contract remains consistent with the runtime checkpoints.

## Truth Boundary

- This is a 12-hour execution contract preview. It describes queue ordering and health checkpoints only; it does not launch jobs or override the current active download families.
