# ProteoSphere WinUI Operator App

This directory is the starter home for the WinUI operator app scope recorded by `P6-T006` and expanded by `P10-T003`.

The app is not implemented yet. The canonical operator surface today remains the PowerShell interface in [`scripts/powershell_interface.ps1`](../../scripts/powershell_interface.ps1), and the canonical operator contract is the schema/reporting path pinned by:

- [`artifacts/schemas/operator_state.schema.json`](../../artifacts/schemas/operator_state.schema.json)
- [`docs/reports/operator_state_contract.md`](../../docs/reports/operator_state_contract.md)
- [`docs/reports/operator_state_parity.md`](../../docs/reports/operator_state_parity.md)

## Current Gate

WinUI work is still blocked on local environment availability.

- The current environment still fails `dotnet new list winui`.
- The blocker is documented in [`docs/reports/winui_environment_blocker.md`](../../docs/reports/winui_environment_blocker.md).
- Until that changes, this directory is a handoff contract and not a claim that a working WinUI shell exists locally.

## Binding Contract

When implementation starts, the WinUI shell should bind to one canonical snapshot model only.

- Primary behavioral reference: [`scripts/powershell_interface.ps1`](../../scripts/powershell_interface.ps1)
- Snapshot/parity reference: [`scripts/validate_operator_state.py`](../../scripts/validate_operator_state.py)
- Combined snapshot shape: [`artifacts/schemas/operator_state.schema.json`](../../artifacts/schemas/operator_state.schema.json)
- Read-only release projection: [`runs/real_data_benchmark/full_results/operator_dashboard.json`](../../runs/real_data_benchmark/full_results/operator_dashboard.json)

The future shell should not invent a separate queue model, runtime model, or dashboard model.

## Expected Starter Surface

The first WinUI shell should stay conservative and read-only:

- queue inspection
- library inspection
- runtime inspection
- combined state inspection
- explicit missing-input diagnostics
- provenance/freshness visibility through `generated_at` and `source_files`

## Diagnostics Expectations

The first WinUI shell should surface the same failure modes the PowerShell lane already keeps explicit:

- missing queue or orchestrator-state files
- missing library status files
- missing benchmark artifacts
- parse failures for snapshot inputs
- release-grade blocked status and blocker arrays
- the active WinUI environment blocker when the local template/tooling is unavailable

## Handoff

When implementation work starts, use this order:

1. Keep the startup contract aligned with the PowerShell `state` snapshot.
2. Bind read-only views to the canonical operator snapshot rather than re-deriving state per page.
3. Add a diagnostics panel that shows freshness, source files, missing inputs, and blocker arrays.
4. Keep refresh safe and idempotent before adding any operator actions.
5. Add mutation controls only after a separate task defines those semantics explicitly.

The detailed starter structure is documented in [`docs/reports/winui_scope.md`](../../docs/reports/winui_scope.md).
