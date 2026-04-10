# P73 Split Fold Export Staging Contract

Report-only contract for the next executable fold-export staging surface.

## Current Readout

The dry-run chain is aligned:

- dry-run validation status: `aligned`
- dry-run issue count: `0`
- candidate rows: `1889`
- assignment rows: `1889`

The fold-export gate preview is still blocked:

- gate status: `blocked_pending_unlock`
- `fold_export_ready = false`
- `cv_folds_materialized = false`
- `final_split_committed = false`

## Staging Surface

The next executable surface is `run_scoped_fold_export_staging`.

It should produce either:

- a run-scoped fold-export staging manifest, or
- a blocked report

It should not materialize CV folds.

## Required Staging Shape

A staging manifest should carry:

- `stage_id`
- `gate_id`
- `gate_status`
- `gate_surface`
- `dry_run_validation_status`
- `candidate_row_count`
- `assignment_count`
- `split_group_counts`
- `row_level_split_counts`
- `largest_groups`
- `blocked_reasons`
- `run_scoped_only`
- `cv_folds_materialized`
- `final_split_committed`
- `truth_note`

The values should remain anchored to the current preview surfaces, including the `train=1`, `val=1`, `test=9` group shape and the `P04637=train`, `P68871=val`, `P69905=test`, `P31749=test` largest-group layout.

## What This Stage May Do

- Accept the live fold-export gate preview as the handoff surface.
- Reconfirm dry-run and input-preview parity.
- Emit a run-scoped staging manifest or a blocked report.
- Carry the gate state explicitly for operators.

## What This Stage Must Not Do

- Materialize CV folds.
- Rewrite protected latest surfaces.
- Promote a release split.
- Introduce ligand or interaction rows.
- Weaken the p67 dry-run guardrails or the p68 gate conditions.

## Truth Boundary

This is a staging contract, not a fold-export authorization.

It is valid only while the gate remains blocked pending unlock. If the gate later opens, the staging surface must still keep the run-scoped boundary and should not be mistaken for a committed split.

## Operator Read

Use this contract as the next report-only staging handoff after the live fold-export gate preview. Keep the surface narrow, run-scoped, and blocked until a separate unlock step exists.
