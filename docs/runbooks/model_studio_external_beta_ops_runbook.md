# Model Studio External Beta Ops Runbook

## Goal

Run the controlled external beta without improvisation. This runbook is the operating layer that sits on top of the technical beta.

## Daily Operator Ritual

1. Verify health and workspace load.
2. Check current launchable pools and review-pending blockers.
3. Review new participant issues.
4. Review any P1 or P2 findings from the reviewer lanes.
5. Confirm the deferred-items ledger still matches the current product truth.

Current launchable beta anchor:

- PPI benchmark trio
- `governed_ppi_blended_subset_v2`
- `governed_ppi_external_beta_candidate_v1`
- `governed_pl_bridge_pilot_subset_v1`

## Invite Workflow

Before inviting a participant:

- confirm the current beta-safe lane
- confirm the participant guide is current
- confirm issue reporting is working
- confirm rollback/disable rules are current

## Temporary Disable Rule

A pool or feature must be temporarily disabled if:

- launchability truth drifts from backend authority
- a P1 scientific-truth issue is opened
- compare/export surfaces become misleading
- a required reviewer blocks continued exposure

## Rollback Rule

Rollback or disable the affected lane if:

- a launchable path becomes unusable end to end
- blocked lanes are surfaced as if they were safe
- data governance authority becomes contradictory

## Evidence Pack

Maintain current references for:

- browser traces
- screenshots
- compare/export examples
- ligand pilot execution matrix
- reviewer signoff ledger
- deferred-items ledger
- known limitations
