# P21 Operator Workflow Parity

Date: 2026-03-23  
Task: `P21-I007`  
Status: `validated_with_winui_handoff_blocker`

## Bottom Line

The operator workflow surface is now parity-checked across the live PowerShell lane and the current WinUI handoff contract.

This is intentionally not a claim that a runnable WinUI shell exists. The truthful state is:

- the active operator workflow is PowerShell-first,
- the workflow modules behind it now line up end to end, and
- the WinUI surface remains a documented handoff plus blocker boundary until the local environment can scaffold an official project.

## What Was Checked

The parity pass binds together these landed operator workflow surfaces:

- `scripts/powershell_interface.ps1`
- `scripts/operator_recipes.ps1`
- `scripts/dataset_design_wizard.py`
- `scripts/export_provenance_drilldown.py`
- `scripts/review_workspace.py`
- `scripts/validate_operator_state.py`
- `docs/reports/winui_scope.md`
- `apps/ProteoSphereWinUI/README.md`

## Verified Live Results

The current integration state is coherent:

- operator-state validation passes with `completion_status = blocked_on_release_grade_bar`
- the frozen operator cohort remains `12` accessions with `8 train / 2 val / 2 test`
- the dataset design wizard emits `12` proposals:
  - `1` supported
  - `1` weak
  - `10` blocked
- the review workspace stays honest at `1` promoted, `4` weak, `1` blocked
- the provenance drilldown emits:
  - `12` entity traces
  - `12` pair traces
  - `12` packet traces
  - `80` unresolved lanes

The result is useful because the operator can move from:

- recipe dispatch,
- to cohort proposal,
- to provenance drilldown,
- to review triage,

without any silent state-model fork between the live PowerShell flow and the future WinUI binding contract.

## WinUI Relationship

The WinUI side of parity is contract-level, not runtime-level.

That means parity is considered valid here when all of the following remain true:

- the WinUI handoff docs point to the same canonical operator snapshot
- the PowerShell lane remains the active source of truth
- the environment blocker remains explicit
- no report or test implies that a local WinUI shell is already buildable

The current handoff continues to satisfy that bar:

- `docs/reports/winui_scope.md` points WinUI at the PowerShell/operator-state contract
- `apps/ProteoSphereWinUI/README.md` states that the app is not implemented yet
- the local blocker still centers on `dotnet new list winui`

## Truth Boundary

This task validates workflow parity, not product completeness.

It does not prove:

- release readiness
- a working WinUI runtime
- weeklong unattended durability
- release-grade benchmark maturity

It does prove that the operator workflow surfaces we have today are aligned and conservative about those missing pieces.

## Verification

- `python -m pytest tests\integration\test_operator_workflow_parity.py -q`
- `python -m ruff check tests\integration\test_operator_workflow_parity.py`
- `python scripts\validate_operator_state.py --json`
- `python scripts\dataset_design_wizard.py --as-json > $null`
- `python scripts\export_provenance_drilldown.py --output runs\real_data_benchmark\full_results\provenance_drilldown.json`
- `python scripts\review_workspace.py --json`

## Outcome

`P21-I007` is complete as a truthful operator-workflow parity gate.

The next operator-facing work should build on this validated PowerShell lane while keeping the WinUI scaffold blocked until the local environment is actually ready.
