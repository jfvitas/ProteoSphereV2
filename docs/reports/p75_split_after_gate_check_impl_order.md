# P75 Split After Gate Check Implementation Order

This is a report-only proposal for the next safe implementation order after the post-staging gate-check, grounded only in the current split staging, gate, and dry-run artifacts.

## Current Truth

The repo is staged, but still blocked.

- staging preview: `blocked_report_emitted`
- staging scope: `run_scoped_only`
- gate status: `blocked_pending_unlock`
- dry-run validation: `aligned`
- dry-run issue count: `0`
- candidate rows: `1889`
- assignment rows: `1889`
- operator dashboard: `no-go`
- release grade: `blocked_on_release_grade_bar`

That means the gate-check is a real handoff boundary, but it does not authorize CV fold materialization today.

## Proposed Safe Order

The safest post-gate-check implementation order is:

1. `run_scoped_fold_export_request`
1. `run_scoped_fold_export_request_validation`
1. `cv_fold_materialization`
1. `final_split_commit_gate`

This order is narrow on purpose:

- the request comes first because the repo already has a staged, run-scoped handoff
- validation comes second because the request should be checked against the already-aligned dry-run and input previews
- fold materialization comes only after a separate unlock step
- final split commitment comes last and still requires separate release approval

## Why This Order Is Safe

The staging and gate surfaces already agree on the important facts:

- `P04637=train`
- `P68871=val`
- `P69905=test`
- `P31749=test`
- `train=1`, `val=1`, `test=9`

So the next implementation boundary should preserve that truth rather than jump straight to a fold artifact or release commit.

The key safety rule is simple:

- request first
- validate second
- materialize third
- commit last

Anything earlier than that would overstate the current state of the repo.

## What Stays Deferred

The following remain explicitly out of scope today:

- CV fold materialization
- final split commitment
- release split promotion
- rewriting protected latest surfaces
- introducing ligand or interaction rows into the split path

## Boundary

This proposal is report-only. It does not edit code, does not rewrite protected latest surfaces, and does not claim fold export readiness that the current staged and gated surfaces still deny.
