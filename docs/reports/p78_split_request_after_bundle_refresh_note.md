# p78 Split Request After Bundle Refresh Note

This note is report-only. The split request chain remains aligned end-to-end, but the unlock gate is still blocked and the operator dashboard is still no-go, so the next safe progression after the current bundle refresh is still the run-scoped request manifest, not fold materialization.

## Current Grounding

- Dry-run validation is `aligned`.
- The request preview is `blocked_report_emitted`.
- The request validation is `aligned`.
- The post-staging gate check is still `blocked_report_emitted`.
- The operator dashboard is `no-go` and `blocked_on_release_grade_bar`.

## Exact Safe Progression

1. Keep the run-scoped fold-export request manifest as the next progression point.
2. Preserve the aligned request counts as the validation anchor.
3. Wait for the unlock gate to change state before any request emission can move forward.
4. Only after that gate opens should request validation be rechecked and CV folds be materialized.

## Request Snapshot

- Candidate rows: `1889`
- Assignment count: `1889`
- Linked groups: `11`
- Split groups: train `1`, val `1`, test `9`
- Row-level split counts: train `1440`, val `266`, test `183`
- Largest groups: `protein:P04637` train `1440`, `protein:P68871` val `266`, `protein:P69905` test `152`, `protein:P31749` test `24`

## Blocked Boundaries

- The unlock gate is still `blocked_pending_unlock`.
- `fold_export_ready` is `false`.
- `cv_folds_materialized` is `false`.
- `final_split_committed` is `false`.
- No protected latest surfaces should be rewritten.

## Truth Boundary

This note does not authorize fold export or final split commitment. It records the safe post-bundle-refresh progression target and keeps the blocked boundary explicit until separate unlock approval exists.
