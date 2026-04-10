# WinUI Fallback Operator Lane Note

Date: 2026-03-22
Context: WinUI template unavailable in the local environment, so the operator surface must keep improving through the PowerShell/state-contract lane until the desktop shell can be scaffolded truthfully.

## Strongest Next Improvements

1. Make the PowerShell operator surface the strongest possible canonical snapshot by keeping `scripts/powershell_interface.ps1` as the single read path for queue, library, runtime, benchmark, and combined state, with explicit missing-input diagnostics instead of implied defaults.
2. Harden the operator-state validator so `scripts/validate_operator_state.py` can continue acting as the release gate for parity, freshness, and truth-boundary checks between the PowerShell snapshot and the benchmark dashboard.
3. Keep the benchmark dashboard and source-coverage semantics aligned with the conservative contract so the operator view remains release-grade honest even while the runtime is still prototype-bound.
4. Treat `apps/ProteoSphereWinUI/README.md` as the handoff contract for a read-only shell: the future UI should mirror the current snapshot model, not invent a second operator model.

## Concrete Next Tasks

| Task | Primary file ownership | Why it is the next useful increment |
| --- | --- | --- |
| Add richer missing-input diagnostics and a stable JSON snapshot shape to the PowerShell operator surface. | `scripts/powershell_interface.ps1` | This is the most direct way to improve operator visibility before WinUI exists, because it is already the live source of truth for queue, library, runtime, and benchmark state. |
| Tighten schema and parity validation for the combined operator snapshot. | `scripts/validate_operator_state.py`, `artifacts/schemas/operator_state.schema.json` | This keeps the fallback lane honest by detecting drift between the PowerShell view, the benchmark dashboard, and the pinned operator contract. |
| Add a small automated smoke test for the operator snapshot contract and validator output. | `tests/integration/test_operator_state.py` or `tests/unit/...` | A dedicated test gives us a repeatable gate for the fallback lane while WinUI remains blocked. |
| Expand the WinUI starter README into a binding guide for the read-only shell and its diagnostics panel. | `apps/ProteoSphereWinUI/README.md`, `docs/reports/winui_scope.md` | This keeps future desktop work aligned with the landed operator model and prevents a second ad hoc state graph from appearing. |
| Keep the operator dashboard export aligned with the conservative benchmark interpretation. | `scripts/export_operator_dashboard.py`, `runs/real_data_benchmark/full_results/operator_dashboard.json` | The dashboard is part of the operator surface, so it should continue to reflect blocked release-grade status, prototype-runtime limits, and conservative source-coverage semantics. |
| Preserve the WinUI blocker evidence and environment notes as the gate for starting desktop work. | `docs/reports/winui_environment_blocker.md` | This keeps the environment truth visible and prevents the team from assuming the template or workloads are available when they are not. |

## Environment Checks To Keep Running

- `dotnet --info` to confirm the local SDK/runtime state has not changed.
- `dotnet new list winui` to re-check whether the WinUI template is finally available.
- `powershell.exe -File scripts/powershell_interface.ps1 -Mode state -AsJson` to verify the canonical operator snapshot still parses and stays coherent.
- `python scripts/validate_operator_state.py --json` to keep the operator-state contract, dashboard projection, and benchmark summary in parity.
- If the fallback lane changes, rerun the same checks before any claim that the UI layer is ready for WinUI binding.

## Bottom Line

The highest-value work before WinUI exists is not desktop rendering. It is tightening the PowerShell snapshot, validator, and operator documentation so the future shell can bind to one stable state contract with explicit blockers and no invented behavior.
