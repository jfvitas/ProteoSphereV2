# p77 Split Request Unlock Progression Note

This note is report-only. The split request preview and its validation are aligned, but the unlock gate is still blocked pending approval, so the run-scoped fold-export request cannot progress into materialization yet.

## Current State

- The request preview is `blocked_report_emitted`.
- The request validation is `aligned`.
- The request remains `run_scoped_only`.
- The unlock gate is `blocked_pending_unlock`.
- The operator dashboard is still `no-go` and `blocked_on_release_grade_bar`.

## Grounded Progression

The current progression target is the run-scoped request manifest, not fold export itself. The request preview already defines the manifest shape, counts, and largest groups, but it stays blocked until the unlock gate changes state.

- Candidate rows: `1889`
- Assignment count: `1889`
- Linked group count: `11`
- Split groups: train `1`, val `1`, test `9`
- Row-level split counts: train `1440`, val `266`, test `183`
- Largest groups: `protein:P04637` train `1440`, `protein:P68871` val `266`, `protein:P69905` test `152`, `protein:P31749` test `24`

## What Unlock Would Allow Next

1. Emit the run-scoped request manifest only after the unlock gate opens.
2. Revalidate the request manifest against the already aligned dry-run surfaces.
3. Materialize CV folds only after request validation stays aligned.
4. Keep final split commitment deferred until a separate release approval exists.

## What Is Still Blocked

- CV fold export is not unlocked.
- No CV folds are materialized.
- Final split commit is deferred.
- The operator dashboard still says no-go.

## Truth Boundary

This note does not authorize fold export, materialization, or release commit. It only records the next progression step and the conditions that must change before the request can leave report-only status.
