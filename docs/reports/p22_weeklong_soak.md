# P22 Weeklong Soak Validation

Date: 2026-04-03
Task: `P22-I007`

## Scope

This report validates the unattended soak evidence that is now present in-tree and captures the current blocker boundaries. It is not a release-grade claim and it does not upgrade the benchmark beyond the evidence on disk.

## Evidence Used

- `artifacts/runtime/monitor_snapshot.json`
- `artifacts/runtime/supervisor.heartbeat.json`
- `artifacts/runtime/soak_ledger.jsonl`
- `artifacts/status/orchestrator_state.json`
- `docs/reports/p22_soak_rollup.md`
- `docs/reports/p22_soak_anomalies.md`
- `docs/reports/p22_operational_readiness_snapshot.md`
- `runs/real_data_benchmark/full_results/run_manifest.json`
- `runs/real_data_benchmark/full_results/release_bundle_manifest.json`
- `scripts/powershell_interface.ps1`
- `scripts/restore_runtime_state.py`
- `tests/integration/test_failure_injection.py`
- `tests/integration/test_restore_runtime_state.py`

## Health and Duration

The soak ledger now spans more than a week of observed runtime evidence:

- `docs/reports/p22_soak_rollup.md` reports `10519` ledger entries across `275.33` observed hours.
- `docs/reports/p22_soak_rollup.md` reports `progress_ratio = 1.0` and `remaining_hours = 0.0`.
- `docs/reports/p22_operational_readiness_snapshot.md` reports the current supervisor heartbeat as `healthy`.
- `artifacts/runtime/supervisor.heartbeat.json` shows a fresh supervisor heartbeat with the current PID and cycle iteration.

This is enough to say the runtime has weeklong-duration ledger coverage. It is not enough to say the runtime is release-ready or that the benchmark has crossed its truth boundary.

## Stalls and Recoveries

The ledger shows a short startup incident cluster and then a long healthy recovery streak:

- `docs/reports/p22_soak_anomalies.md` reports `4` incidents, all with status `unavailable`.
- All four incidents occurred at the start of the observed window on `2026-03-23`.
- `docs/reports/p22_soak_anomalies.md` reports a longest healthy streak of `10515` samples and a current healthy streak of `10515` samples.
- `docs/reports/p22_operational_readiness_snapshot.md` reports queue drift as `aligned`.

That means the current evidence supports the claim that the unattended surface recovered cleanly from its startup instability and has remained stable afterward.

## No Silent Healthy-State Overclaims

The current status path no longer silently overclaims the supervisor as stopped when the heartbeat says otherwise:

- `scripts/powershell_interface.ps1` now falls back to heartbeat-backed status when the PID-file path is temporarily missing.
- The live `status` output now reports `Supervisor: running (heartbeat-only, PID 43776)` rather than printing a misleading stopped banner.
- `docs/reports/p22_operational_readiness_snapshot.md` still keeps `ready = False` and `weeklong_claim_allowed = False`.

That closes the earlier mismatch where the status banner could imply a false unhealthy state while the heartbeat and monitor surfaces showed a healthy loop.

## Blocker Boundaries

The truth boundary is still intentionally closed:

- `docs/reports/p22_soak_rollup.md` reports `weeklong_claim_allowed = False`.
- `docs/reports/p22_operational_readiness_snapshot.md` reports `blocking_reasons = ['weeklong_claim_boundary_closed', 'benchmark_status=blocked_on_release_grade_bar']`.
- `runs/real_data_benchmark/full_results/run_manifest.json` still describes the runtime as a local prototype.
- `runs/real_data_benchmark/full_results/release_bundle_manifest.json` still keeps the benchmark blocked on release-grade maturity.

So the correct claim is:

- the unattended soak evidence is now substantial and weeklong in duration,
- the runtime health story is explicit about incidents and recovery,
- the operator surface no longer silently misreports the supervisor state,
- the benchmark still remains blocked from release-grade claims.

## Judgment

`P22-I007` is satisfied as a validation/reporting task.

The weeklong soak evidence is present, the report now captures health, stalls, recoveries, and blocker boundaries, and the status surface no longer silently overclaims a contradictory healthy-state result.

The release boundary remains closed by design.
