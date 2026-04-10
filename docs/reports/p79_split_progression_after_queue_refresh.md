# p79 Split Progression After Queue Refresh

This note is report-only. The new ligand operator queue refresh adds actionable operator guidance for the ligand lane, but it does not change the split gate state. The next safe split progression remains the run-scoped fold-export request manifest, and it is still blocked from emission because the unlock gate is closed and the operator dashboard is no-go.

## Current Split State

- Dry-run validation is `aligned`.
- The split request preview is `blocked_report_emitted`.
- The split request validation is `aligned`.
- The post-staging gate check is still `blocked_report_emitted`.
- The unlock gate remains `blocked_pending_unlock`.
- The operator dashboard is still `no-go` and `blocked_on_release_grade_bar`.

## Queue Refresh Meaning

The ligand stage-1 operator queue is useful for operator prioritization, but it is not a split authorization signal.

- `P00387` is the lead anchor and is only actionable as a local bulk-assay ingest lane.
- `Q9NZD4` is the bridge rescue candidate and still depends on a materialized structure bridge.
- `P09105` and `Q2TAC2` remain support candidates without local ligand evidence.
- `Q9UCM0` stays deferred and requires fresh acquisition.

## Exact Next Safe Split Progression

1. Keep the dry-run parity as the trust anchor.
2. Keep the run-scoped request manifest as the next split progression target.
3. Do not emit the request until the unlock gate changes state.
4. Revalidate the request only after the gate opens.
5. Materialize CV folds only after request validation remains aligned.

## Split Snapshot

- Candidate rows: `1889`
- Assignment count: `1889`
- Linked groups: `11`
- Split groups: train `1`, val `1`, test `9`
- Row-level split counts: train `1440`, val `266`, test `183`
- Largest groups: `protein:P04637` train `1440`, `protein:P68871` val `266`, `protein:P69905` test `152`, `protein:P31749` test `24`

## Blocked Boundaries

- `fold_export_ready` is `false`.
- `cv_folds_materialized` is `false`.
- `final_split_committed` is `false`.
- No protected latest surfaces should be rewritten.

## Truth Boundary

This note does not authorize fold export, fold materialization, or release split commitment. The ligand queue refresh is advisory only and should not be read as a split unlock.
