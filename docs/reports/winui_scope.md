# WinUI Operator App Scope

Date: 2026-03-22  
Tasks: `P6-T006`, `P10-T003`

## Purpose

`P6-T006` defines the documentation-level starter scope for the WinUI operator app. This task does not create a full desktop application yet. Instead, it records the initial structure, the operator flows the future app should expose, and the handoff path from the landed PowerShell operator interface.

## Grounding

The current source of truth for operator state is the PowerShell interface in [`scripts/powershell_interface.ps1`](../../scripts/powershell_interface.ps1). It already exposes the queue, library, runtime, and combined state views by reading the landed task queue and status artifacts.

The WinUI app should mirror that state model rather than invent a new one. The binding should be anchored to the canonical operator snapshot contract:

- [`artifacts/schemas/operator_state.schema.json`](../../artifacts/schemas/operator_state.schema.json)
- [`docs/reports/operator_state_contract.md`](../../docs/reports/operator_state_contract.md)
- [`docs/reports/operator_state_parity.md`](../../docs/reports/operator_state_parity.md)

At implementation time, the shell should treat the PowerShell state view as the coarse live operator source and the dashboard export as a read-only projection inside the same snapshot model.

The bound sections are:

- task queue state from `tasks/task_queue.json`
- library state from the summary-library status/materialization artifacts
- runtime state from `artifacts/status/orchestrator_state.json`
- combined operator state from the PowerShell `state` view
- dashboard projection from `runs/real_data_benchmark/full_results/operator_dashboard.json`

The WinUI work here stays conservative and read-only at the starter stage.

## Environment Gate

This scope does not claim the environment is ready for a WinUI scaffold.

- The active blocker remains the missing local `winui` template.
- The exact evidence is captured in [`docs/reports/winui_environment_blocker.md`](../../docs/reports/winui_environment_blocker.md).
- The correct preflight checks remain `dotnet --info` and `dotnet new list winui`.

Desktop implementation should not start until that blocker changes or a separate environment-remediation task lands.

## Starter Structure

The initial WinUI shell should be documented as a thin operator surface with these areas:

1. Shell window with a stable navigation frame
2. Queue view for task counts and task IDs
3. Library view for schema/builder/materialization state
4. Runtime view for supervisor and orchestrator state
5. Combined state view for the full operator snapshot
6. Dashboard view for release-grade status, blockers, and truth boundary
7. Status/diagnostics area for missing inputs, parse failures, and snapshot freshness

No implementation files exist yet in `apps/ProteoSphereWinUI/`; this scope only defines the shape of the starter app so the later implementation can be aligned with the landed runtime.

## Operator Flows

The first WinUI release should support these flows:

- Inspect queue readiness, running tasks, dispatched tasks, blocked tasks, and completed tasks
- Inspect summary-library readiness, materialization presence, and record counts
- Inspect supervisor/runtime status and the current orchestrator state snapshot
- Open the combined state view for a quick operator check
- Inspect the dashboard projection for release-grade status, blocker arrays, and the active truth boundary
- Surface missing or malformed inputs explicitly instead of synthesizing fallback state
- Surface source-file provenance and generation timestamp so stale data is obvious

The flows are intentionally read-only at this stage. Action-oriented controls, if added later, should be introduced only after the runtime contract is stable.

## Binding Rules

The first WinUI implementation should follow these rules:

1. Bind to the canonical snapshot shape rather than per-view ad hoc models.
2. Keep `queue`, `library`, `benchmark`, `runtime`, and `dashboard` as first-class sections.
3. Preserve blocker arrays and explicit blocked status labels exactly.
4. Preserve `generated_at` and `source_files` so freshness and provenance stay visible.
5. Treat missing data as a diagnosable state, not as an invitation to synthesize defaults.
6. Keep the shell read-only until a separate task defines mutation semantics.

## Diagnostics Panel Expectations

The diagnostics area should make these conditions visible without requiring the operator to open raw files:

- missing queue file
- missing orchestrator-state file
- missing library status files
- missing benchmark artifacts
- snapshot parse failures
- release-grade blocked status and blocker arrays
- local WinUI environment blocker status

This is especially important because the near-term operator path remains PowerShell-backed and the desktop shell must not hide or normalize missing evidence.

## Handoff Path

The implementation handoff should proceed in this order:

1. Reuse the existing PowerShell interface as the behavioral reference for state fields and missing-input handling
2. Reuse the operator-state schema and parity validation as the binding contract
3. Add the WinUI shell and bind it to the same JSON/state sources
4. Keep the initial views read-only until operator actions are separately specified
5. Add refresh and diagnostics affordances before any mutation workflows
6. Only then add task-control or runtime-control surfaces, if the queue calls for them

This keeps the WinUI app aligned with the current runtime/library state and avoids pretending that the desktop app is already feature-complete.

## Non-Goals

- No XAML/C# implementation in this task
- No new runtime semantics
- No mutation or dispatch controls
- No widening of the operator data model beyond the landed PowerShell interface

## Verification Notes

This scope was validated by:

- checking the landed PowerShell operator interface
- checking the pinned operator-state schema and parity report
- confirming the WinUI documentation files are present
- confirming the local WinUI template remains unavailable

This task remains documentation-only, so no desktop build is claimed here.
