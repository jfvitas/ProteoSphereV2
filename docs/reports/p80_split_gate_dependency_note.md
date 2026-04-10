# p80 Split Gate Dependency Note

This note is report-only. The split lane is still waiting on the unlock gate, so no split request can move beyond report-only until the dependency chain below clears in order.

## Current Operator Truth

- The operator next-actions preview marks the split lane as `blocked_report_emitted`.
- The split request preview is `blocked_report_emitted`.
- The split request validation is `aligned`, but it still validates a blocked request.
- The post-staging gate check remains `blocked_report_emitted`.

## Dependency Chain

1. The unlock gate must stop being blocked pending unlock.
2. The run-scoped request manifest must be emitted only after that gate opens.
3. The request validation must still match the post-staging gate check and split-engine input surfaces.
4. Only after validation stays aligned can CV folds be materialized.
5. Final split commitment stays deferred until a separate release approval exists.

## Blocked Boundaries

- `run_scoped_only` must remain true until the request is allowed to progress.
- No CV folds are materialized today.
- No protected latest surfaces are rewritten.
- Final split commitment is still false.

## Truth Boundary

This note does not authorize fold export. It only records the exact dependency order that must clear before the split request can move past report-only status.
