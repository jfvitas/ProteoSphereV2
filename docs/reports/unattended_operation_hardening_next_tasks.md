# Unattended Operation Hardening Next Tasks

Date: 2026-03-22

This note is for the weeklong Codex automation lane documented in [`docs/runbooks/weeklong_codex_automation.md`](D:/documents/ProteoSphereV2/docs/runbooks/weeklong_codex_automation.md). The current operator path is still the PowerShell surface in [`scripts/powershell_interface.ps1`](D:/documents/ProteoSphereV2/scripts/powershell_interface.ps1), with state carried through [`artifacts/status/orchestrator_state.json`](D:/documents/ProteoSphereV2/artifacts/status/orchestrator_state.json) and checked against the parity contract in [`docs/reports/operator_state_parity.md`](D:/documents/ProteoSphereV2/docs/reports/operator_state_parity.md).

## Bottom Line

The automation loop is operational, but weeklong autonomous stability still needs better heartbeat visibility, clearer restart semantics, and more honest alerting when the queue or runtime drifts.

## Next Tasks

| Priority | Task | Why it matters | Exit criterion |
| --- | --- | --- | --- |
| 1 | Add an explicit supervisor heartbeat and staleness age to `orchestrator_state.json`. | The current state file exposes workers and task counts, but not a clear “last healthy cycle” signal. Weeklong operation needs to tell the difference between “busy” and “stuck.” | The operator state reports a heartbeat timestamp, stale-age threshold, and a boolean stale/healthy signal. |
| 2 | Emit structured cycle failure records and stop after repeated identical failures. | Today the loop logs text, but it does not yet turn repeated failures into a first-class alert. That makes unattended recovery too optimistic. | A cycle failure writes a structured record with task, stage, error class, and retry count; repeated failures trip a visible stop condition. |
| 3 | Make restartability explicit in the loop contract. | The runbook describes a loop, but the restart boundary is still mostly implicit. A weeklong run needs a durable resume marker and a predictable restart check. | A restart can resume from the last recorded cycle without losing queue or review state, and the operator can say why it resumed. |
| 4 | Add honest queue-health alerts for starvation, blockage growth, and dispatch stagnation. | The operator already knows queue counts; the missing piece is telling the human when progress is no longer healthy. | The operator view surfaces queue-starvation, blocked-growth, and stalled-dispatch warnings with no false “healthy” signal. |
| 5 | Keep the PowerShell view and dashboard export in parity on release-status semantics. | [`docs/reports/operator_state_parity.md`](D:/documents/ProteoSphereV2/docs/reports/operator_state_parity.md) shows the fallback lane is valid, but it should stay truthful as the dashboard export evolves. | A focused parity check continues to pass after operator/dashboard changes, and the status fields stay aligned on the current truth boundary. |

## Suggested Follow-Up Order

1. Heartbeat and staleness.
2. Structured failure envelopes.
3. Restart marker and resume cause.
4. Queue-health alerting.
5. Parity regression gate.

## What Not To Do

- Do not widen the queue model just to make the system look active.
- Do not treat log noise as liveness.
- Do not invent a success state when the supervisor is merely looping.
- Do not move the operator truth boundary away from the current dashboard and summary artifacts.

## Summary

These tasks keep the unattended path honest: they make “healthy,” “stuck,” “restarted,” and “blocked” visible without requiring a human to infer them from raw logs.
