# WinUI Environment Blocker

Date: 2026-03-22  
Task: `P9-A001`

## Evidence

### 1. Repository bootstrap is coherent

The repo bootstrap review already records a passing bootstrap state: the queue, orchestrator, and tests are functioning, even though branch isolation and full pipeline depth are not yet complete.

- `artifacts/reviews/bootstrap_review.md:5-8`

### 2. Current .NET state is present, but bare

The local SDK is installed and usable:

- .NET SDK `10.0.201`
- MSBuild `18.3.0`
- Windows Desktop runtime `10.0.5`
- no workloads are installed

Command evidence:

- `dotnet --info`

### 3. WinUI template is missing

The WinUI scaffold template is not installed in the current environment.

Command evidence:

- `dotnet new list winui`

Observed output:

- `No templates found matching: 'winui'.`

### 4. Fallback operator-contract path is already defined

Until the WinUI shell can be scaffolded, the current operator contract remains the PowerShell interface. The starter README says the app is not implemented yet and that the PowerShell interface is the source of truth for operator state. It also says the WinUI shell should mirror the same state model when implementation starts.

- `apps/ProteoSphereWinUI/README.md:3-5`
- `apps/ProteoSphereWinUI/README.md:19-21`

## Blocker

The environment does not currently have the `winui` template available, so the WinUI shell cannot be truthfully bootstrapped from the standard local scaffold path.

That means the correct fallback is to keep using the PowerShell operator surface as the operator-contract path until the WinUI toolchain is provisioned.

## What This Means

- We can continue validating operator behavior through `scripts/powershell_interface.ps1`.
- We should not claim that a WinUI operator app has been bootstrapped in this environment.
- Any future WinUI work should start from the missing-template remediation path, not from an assumed scaffold.
