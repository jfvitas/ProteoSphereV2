# P22 Operational Resilience Report

Date: 2026-04-03
Task: `P22-I008`

## Scope

This report validates the current failure-handling, restartability, and restore-path evidence in-tree. It stays within the existing runtime and benchmark artifacts and does not claim release readiness.

## Evidence Used

- `docs/reports/p22_weeklong_soak.md`
- `docs/reports/p22_soak_rollup.md`
- `docs/reports/p22_soak_anomalies.md`
- `docs/reports/p22_operational_readiness_snapshot.md`
- `artifacts/runtime/monitor_snapshot.json`
- `artifacts/runtime/supervisor.heartbeat.json`
- `artifacts/runtime/supervisor.log`
- `artifacts/runtime/soak_ledger.jsonl`
- `artifacts/status/orchestrator_state.json`
- `scripts/powershell_interface.ps1`
- `scripts/restore_runtime_state.py`
- `tests/integration/test_failure_injection.py`
- `tests/integration/test_restore_runtime_state.py`

## Failure Handling

The current failure-injection surface is fail-closed and explicit.

- `tests/integration/test_failure_injection.py` records repeated failures as explicit envelopes and stops after the configured attempt budget.
- `tests/integration/test_failure_injection.py` rejects unsupported release-manifest payloads instead of synthesizing fallback state.
- `tests/integration/test_failure_injection.py` rejects corrupted checkpoint payloads when checkpoint identity does not match.
- `docs/reports/p22_failure_injection_plan.md` defines the intended boundary: repeated errors, bad manifests, and corrupted checkpoints should fail closed rather than repair themselves silently.

That is the right resilience shape for this phase: the system detects bad input and refuses to paper over it.

## Restartability

Restart behavior is coherent and observable rather than implied.

- `artifacts/status/orchestrator_state.json` records the current queue as restart-aware and keeps the active worker set explicit.
- `artifacts/runtime/monitor_snapshot.json` shows the queue and worker snapshot are aligned with the orchestrator state.
- `scripts/powershell_interface.ps1` now falls back to heartbeat-backed status if the PID-file check is temporarily missing, which prevents a misleading `stopped` banner when the supervisor loop is actually healthy.
- `artifacts/runtime/supervisor.heartbeat.json` shows a fresh heartbeat with the current PID and cycle iteration.
- `artifacts/runtime/supervisor.log` shows consecutive completed cycles, confirming the loop is advancing rather than stalling.

The restart story is not "we can always recover from anything." It is narrower and stronger: the loop, orchestrator, monitor, and status surfaces all carry enough state to show whether the system resumed cleanly and to avoid fabricating success.

## Restore Paths

The restore path is present, test-covered, and fail-closed.

- `scripts/restore_runtime_state.py` restores the queue and release artifacts from pinned snapshots.
- `tests/integration/test_restore_runtime_state.py` covers complete restore, partial restore, and strict rollback.
- The restore report path writes a machine-readable report and does not claim success if required artifacts are missing.
- The benchmark artifacts remain pinned and bounded by the current prototype runtime, so restore does not widen the corpus or silently upgrade the release boundary.

This is enough to say the restore mechanism is operational for recovery drills and snapshot round-trips.

## Current Health Context

The soak evidence gives the resilience report a stable baseline:

- `docs/reports/p22_soak_rollup.md` reports `10521` ledger entries across `275.36` observed hours.
- `docs/reports/p22_soak_anomalies.md` reports `4` startup incidents, all `unavailable`.
- `docs/reports/p22_operational_readiness_snapshot.md` reports `healthy` supervisor state, aligned queue drift, and `0` audit findings.
- `docs/reports/p22_weeklong_soak.md` states the weeklong claim boundary is still closed even though the evidence window is weeklong in duration.

That combination matters. It shows the system is durable enough to keep generating evidence, but it remains honest about the release boundary.

## Residual Risks

Ranked from highest to lowest practical concern:

1. `Release boundary remains closed`
   - The runtime is still a local prototype, not the production multimodal trainer stack.
   - The benchmark remains blocked on release-grade maturity.
   - This is intentional, but it is still the top operational constraint because it prevents any claim upgrade.

2. `Download/procurement instability`
   - The remaining STRING and UniRef downloads are still partial.
   - The procurement supervisor reports `attention`, and the active download lanes remain visible in the process table.
   - The system is handling this cleanly, but it remains the most obvious external source of churn.

3. `Startup incident history`
   - The ledger contains four early `unavailable` incidents.
   - Recovery has been stable since then, but the startup cluster means the soak is not incident-free from the first sample onward.

4. `Status-surface inconsistency risk`
   - The supervisor status banner previously risked saying `stopped` when the heartbeat was healthy.
   - That mismatch has been fixed in the live `status` path, but it is still worth watching because it is a user-facing trust boundary.

5. `Queue drift / stale-snapshot risk`
   - The monitor and orchestrator are currently aligned, but the system still depends on periodic snapshots and a truthful task queue.
   - Any future lag between those surfaces would make operator interpretation noisier even if execution remains healthy.

## Judgment

The current evidence validates three things:

- failure handling is fail-closed and explicit,
- restartability is observable and stable,
- restore paths are operational and test-covered.

The report also preserves the important truth boundary: these strengths do not remove the release blockers, and they do not justify a production-grade claim.
