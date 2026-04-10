# Overnight Queue Repair Status

- Status: `report_only`
- Recovery state: `repaired_and_idle`
- Repair report present: `True`
- Repaired stale dispatches: `7`
- Recovered and redispatched: `0`
- Recovered and idle: `7`
- Current stale dispatch candidates: `0`

## Repaired Stale Dispatches

- `P1-T010`
- `P1-T012`
- `P1-T013`
- `P1-T014`
- `P15-T001`
- `P15-T002`
- `P15-T003`

## Current Stale Candidates

- none

## Truth Boundary

- This status artifact only surfaces stale-dispatch recovery. It does not change queue semantics, dispatch ordering, or manifest state.
