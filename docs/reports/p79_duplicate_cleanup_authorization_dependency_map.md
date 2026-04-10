# P79 Duplicate Cleanup Authorization Dependency Map

This is a report-only map of what still has to happen before any first duplicate-cleanup mutation could be considered.

## Current Boundary

- The preview is still `not_yet_executable_today`.
- The executor is still `report_only_no_delete`.
- The operator dashboard is still `no-go` and `blocked_on_release_grade_bar`.
- Nothing here authorizes deletion or moves any raw storage.

## Dependency Map

1. `Separate mutation authorization record`
   - Still missing.
   - Why it matters: the preview and executor are still report-only, so there is no destructive approval yet.

2. `Frozen one-action batch`
   - Still missing.
   - Why it matters: the first considered mutation must stay at exactly one approved removal action from `same_release_local_copy_duplicates`.

3. `Execution-time snapshot parity`
   - Still pending.
   - Why it matters: the live inventory and status surfaces must still match the approved plan at the moment of execution.

4. `Dashboard no-go lifted`
   - Still blocked.
   - Why it matters: the operator dashboard still says `no-go`, so the path remains closed today.

5. `Exact path and identity safety`
   - Still required.
   - Why it matters: keeper/removal paths and the SHA-256 pairing must remain exact.

6. `Protected-surface lock`
   - Still required.
   - Why it matters: protected, partial, unresolved, and latest surfaces must stay untouched.

7. `Rollback and audit visibility`
   - Still missing.
   - Why it matters: the first removal needs an explicit recovery and audit trail before it starts.

8. `Post-mutation verification`
   - Still missing.
   - Why it matters: the first execution needs a defined way to prove it completed without drift or overreach.

## Bottom Line

The path is still blocked today. The preview is ready for review, but authorization, snapshot parity, dashboard clearance, and execution-time safety are not yet in place.
